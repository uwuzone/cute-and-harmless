import asyncio

from loguru import logger

from sqlalchemy.orm import Session

from models import get_db_engine
from models.job import Job, JobSource
from models.job import create_child_job, insert_jobs_on_conflict_ignore
from runner.base import take_job, wrap_scraper_exceptions_and_logging
from scrapers.unauthenticated import UnauthenticatedScraper


@wrap_scraper_exceptions_and_logging
def scrape(session: Session, scraper: UnauthenticatedScraper, job: Job):
    logger.debug('getting account info')
    session.merge(scraper.get_user_info())

    logger.info(f'getting tweets and replies')
    n_tweets = 0
    for tweet in scraper.get_tweets(max_tweets=job.max_tweets):
        logger.debug(f'tweet id {tweet.rest_id} ({tweet.content[:20]}...)')
        session.merge(tweet)
        if tweet.is_reply and job.own_depth < job.max_depth:
            session.execute(
                insert_jobs_on_conflict_ignore(
                    create_child_job(job, tweet.reply_to_account_username,
                                     source=JobSource.TWEET_REPLY, authenticated=False),
                    create_child_job(job, tweet.reply_to_account_username,
                                     source=JobSource.TWEET_REPLY, authenticated=True)
                )
            )
        session.commit()

        session.commit()
        n_tweets += 1
    session.commit()
    logger.info(f'saved {n_tweets} tweets')


async def run(concurrency: int = 8):
    engine = get_db_engine()

    # TODO: this doesn't handle cancelled... lol
    # likely this is due to unauthenticated get_tweets pretending to be a
    # generator but dependency is actually eager, so the loop running to
    # completion will hang on io
    async def worker(i: int):
        logger.debug(f'Starting unauthenticated worker {i}/{concurrency}')
        while True:
            with Session(engine) as session:
                job = await take_job(session, authenticated=False)
                scraper = UnauthenticatedScraper(job.username)
                await asyncio.to_thread(scrape, session, scraper, job)

    await asyncio.gather(*[
        worker(i + 1) for i in range(concurrency)
    ])

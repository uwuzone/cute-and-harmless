import asyncio

from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from models import get_db_engine
from models.job import Job, JobSource
from models.job import create_child_job, insert_jobs_on_conflict_ignore
from runner.base import Progress
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



async def run(concurrency: int = 8, max_jobs: Optional[int] = None):
    engine = get_db_engine()

    progress = Progress()

    # TODO: this doesn't handle asyncio cancel.
    # unauthenticated get_tweets pretends to be a generator (nice coroutine) but
    # it uses a dependency which is actually greedy. This means asyncio cancels
    # aren't handled immediately---the scrape job will run fully to completion
    async def worker(i: int):
        logger.debug(f'Starting unauthenticated worker {i}/{concurrency}')
        while True:
            with Session(engine) as session:
                job = await take_job(session, authenticated=False)
                scraper = UnauthenticatedScraper(job.username)
                await asyncio.to_thread(scrape, session, scraper, job)
                await progress.push(job.username)

            if max_jobs is not None and await progress.progress() >= max_jobs:
                return

    await asyncio.gather(*[
        worker(i + 1) for i in range(concurrency)
    ])

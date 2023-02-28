import asyncio

from loguru import logger
from sqlalchemy import Engine, select

from sqlalchemy.orm import Session

from models import get_db_engine
from models.base import JobStatus
from models.job import TweetJob
from runner.base import wrap_scraper_exceptions_and_logging
from scrapers.unauthenticated import UnauthenticatedScraper


async def take_job(engine: Engine, polling_interval: int = 15):
    with Session(engine) as session:
        while True:
            job = session.scalars(
                select(TweetJob).where(
                    TweetJob.status == JobStatus.NEW,
                ).order_by(
                    TweetJob.created_at.desc()
                ).limit(1)
            ).first()

            if job is not None:
                return job

            await asyncio.sleep(polling_interval)


@wrap_scraper_exceptions_and_logging
def scrape(session: Session, scraper: UnauthenticatedScraper, job: TweetJob):
    '''
    Scrape the target.

    High level:
    - Fetch account profile
    - Fetch followers and add them as targets
    - Fetch tweets
      - if any tweet is reply, add the people it replies to as targets
    '''
    logger.debug(f'getting tweets and replies')
    n_tweets = 0
    for tweet in scraper.get_tweets(max_tweets=job.max_tweets):
        logger.debug(
            f'tweet id {tweet.rest_id} ({tweet.content[:20]}...)'
        )
        session.merge(tweet)
        session.commit()
        n_tweets += 1
    session.commit()
    logger.debug(f'saved {n_tweets} tweets')


async def run_unauthenticated(concurrency: int = 8):
    engine = get_db_engine()
    sem = asyncio.Semaphore(concurrency)

    while True:
        logger.info('Waiting for tweet scraping jobs')
        job = await take_job(engine)
        scraper = UnauthenticatedScraper(job.username)
        async with sem:
            logger.debug(
                f'Starting new job, concurrency pool {sem._value}/{concurrency}')
            with Session(engine) as session:
                await asyncio.to_thread(scrape, session, scraper, job)

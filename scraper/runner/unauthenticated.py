import asyncio

from loguru import logger
from sqlalchemy import select, update

from sqlalchemy.orm import Session

from models import get_db_engine
from models.base import JobStatus
from models.job import TweetJob
from runner.base import wrap_scraper_exceptions_and_logging
from scrapers.unauthenticated import UnauthenticatedScraper


async def take_job(session: Session, polling_interval: int = 15):
    while True:
        subq = (
            select(TweetJob.job_id)
            .filter(TweetJob.status == JobStatus.NEW)
            .order_by(TweetJob.created_at.desc())
            .limit(1)
            .subquery()
        )
        jobs = session.scalars(
            update(TweetJob)
            .values(status=JobStatus.RUNNING)
            .where(TweetJob.job_id.in_(select(subq)))
            .returning(TweetJob)
        ).all()

        if len(jobs) > 1:
            raise Exception('my friend your sql are fucked 🙏😑')
        if len(jobs) == 1:
            session.commit()
            return jobs[0]

        await asyncio.sleep(polling_interval)


@wrap_scraper_exceptions_and_logging
def scrape(session: Session, scraper: UnauthenticatedScraper, job: TweetJob):
    logger.info(f'getting tweets and replies')
    n_tweets = 0
    for tweet in scraper.get_tweets(max_tweets=job.max_tweets):
        logger.debug(f'tweet id {tweet.rest_id} ({tweet.content[:20]}...)')
        session.merge(tweet)
        session.commit()
        n_tweets += 1
    session.commit()
    logger.info(f'saved {n_tweets} tweets')


async def run(concurrency: int = 8):
    engine = get_db_engine()

    async def worker(i: int):
        while True:
            with Session(engine) as session:
                logger.debug(f'Waiting for job {i}/{concurrency}')
                job: TweetJob = await take_job(session)
                scraper = UnauthenticatedScraper(job.username)
                await asyncio.to_thread(scrape, session, scraper, job)

    await asyncio.gather(*[
        worker(i + 1) for i in range(concurrency)
    ])

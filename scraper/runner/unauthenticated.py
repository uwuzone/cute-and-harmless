import asyncio

from loguru import logger

from sqlalchemy.orm import Session

from models import get_db_engine
from models.target import Target
from runner.base import take_target
from runner.base import wrap_scraper_exceptions_and_logging
from scrapers.unauthenticated import UnauthenticatedScraper


@wrap_scraper_exceptions_and_logging
def scrape(session: Session, scraper: UnauthenticatedScraper, target: Target):
    '''
    Scrape the target.

    High level:
    - Fetch account profile
    - Fetch followers and add them as targets
    - Fetch tweets
      - if any tweet is reply, add the people it replies to as targets
    '''
    # save tweets
    logger.debug(f'getting tweets and replies')
    n_tweets = 0
    for tweet in scraper.get_tweets(max_tweets=target.max_tweets):
        logger.debug(
            f'tweet id {tweet.rest_id} ({tweet.content[:20]}...)'
        )
        session.merge(tweet)
        session.commit()
        n_tweets += 1
    target.tweets_scraped = True
    session.merge(target)
    session.commit()
    logger.debug(f'saved {n_tweets} tweets')


async def run_unauthenticated(concurrency: int = 8):
    engine = get_db_engine()
    sem = asyncio.Semaphore(concurrency)

    while True:
        logger.info('Waiting for tweet scraping jobs')
        target = await take_target(engine, authenticated=False)
        scraper = UnauthenticatedScraper(target.username)
        async with sem:
            logger.debug(
                f'Starting new job, concurrency pool {sem._value}/{concurrency}')
            with Session(engine) as session:
                await asyncio.to_thread(scrape, session, scraper, target)

# TODO: stop when we see duplicate data?
# TODO: should new user in the replies get added as target?
from typing import Optional, Generator

from selenium import webdriver
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import get_db_engine
from models.target import FollowingJob, JobStatus, new_job_id

from common.logging import logger
from scraper.models.job import insert_targets_on_conflict_ignore
from scrapers import exceptions
from scrapers.abstract import Scraper
from scrapers.authenticated import AuthenticatedScraper
from vendor.scweet.credentials import Credentials


def scrape(scraper: Scraper, session: Session, target: FollowingJob):
    '''
    Scrape the target.

    High level:
    - Fetch account profile
    - Fetch followers and add them as targets
    - Fetch tweets
      - if any tweet is reply, add the people it replies to as targets
    '''

    def start():
        target.status = JobStatus.RUNNING
        session.merge(target)

    def finish():
        target.status = JobStatus.FINISHED
        session.merge(target)
        session.commit()

    def error():
        target.status = JobStatus.ERROR
        session.merge(target)
        session.commit()

    try:
        start()

        # save account info
        logger.debug(f'{target.username}: getting account info')
        session.merge(scraper.get_user_info())

        # save accounts followed by target as new targets
        logger.debug(f'{target.username}: getting following')
        n_following = 0
        for follow in scraper.get_following():
            # TODO: it's actually possible to get user ID here which is more
            # stable than username (can use the unauthenticated scraper for it)
            session.merge(follow)
            logger.debug(
                f'{target.username}: is following {follow.follows_username}'
            )
            if target.own_depth < target.max_depth:
                session.execute(
                    insert_targets_on_conflict_ignore(
                        [target.create_child(follow.followed_by_username)]
                    )
                )
            session.commit()
            n_following += 1
        logger.debug(f'{target.username}: saved {n_following} following')

        # save tweets
        logger.debug(f'{target.username}: getting tweets + replies')
        n_tweets = 0
        for tweet in scraper.get_tweets(max_tweets=target.max_tweets):
            logger.debug(
                f'{target.username}: tweet id {tweet.rest_id} ({tweet.content[:20]}...)'
            )
            session.merge(tweet)
            session.commit()
            n_tweets += 1
        logger.debug(f'{target.username}: saved {n_tweets} tweets')

    except exceptions.UserNotFound as e:
        logger.warning(f'(user not found) skipping {e.username}')
        finish()
    except exceptions.UserProtected as e:
        logger.warning(f'(user is protected) skipping {e.username}')
        finish()
    except exceptions.UnknownException as e:
        logger.error(f'(tweety error) {e.username}, {e.info}')
        error()
    except KeyboardInterrupt as e:
        logger.error(f'(keyboard interrupt) {target.username}')
        error()
        raise e
    except Exception as e:
        logger.error(f'(unknown error) {target.username}, {e}')
        error()
        raise e
    else:
        finish()


def list_targets(session: Session, job_id: str) -> Generator[FollowingJob, None, None]:
    while True:
        target = session.scalars(
            select(FollowingJob).where(
                FollowingJob.job_id == job_id,
                FollowingJob.status == JobStatus.NEW,
            ).order_by(
                FollowingJob.own_depth
            ).limit(1)
        ).first()

        if target is None:
            return

        yield target


async def main():
    pass


if __name__ == '__main__':
    from os import environ

    CUTE_SCRAPER_RESUME_JOB_ID = environ.get('CUTE_SCRAPER_RESUME_JOB_ID')
    CUTE_SCRAPER_ROOT_TARGET = environ.get('CUTE_SCRAPER_ROOT_TARGET')
    CUTE_SCRAPER_USERNAME = environ.get('CUTE_SCRAPER_USERNAME')
    CUTE_SCRAPER_PASSWORD = environ.get('CUTE_SCRAPER_PASSWORD')
    CUTE_SCRAPER_USER_DATA_DIR = environ.get('CUTE_SCRAPER_USER_DATA_DIR')
    CUTE_SCRAPER_PROFILE_DIR = environ.get('CUTE_SCRAPER_PROFILE_DIR')

    if CUTE_SCRAPER_USERNAME is None or CUTE_SCRAPER_PASSWORD is None:
        raise Exception(
            'Missing CUTE_SCRAPER_USERNAME or CUTE_SCRAPER_PASSWORD')
    if CUTE_SCRAPER_ROOT_TARGET is None and CUTE_SCRAPER_RESUME_JOB_ID is None:
        raise Exception(
            'Missing target. Set CUTE_SCRAPER_ROOT_TARGET or CUTE_SCRAPER_RESUME_JOB_ID')

    engine = get_db_engine()

    with Session(engine) as session:
        if CUTE_SCRAPER_RESUME_JOB_ID:
            root_job_id = CUTE_SCRAPER_RESUME_JOB_ID
        else:
            root = FollowingJob(
                id=new_job_id(CUTE_SCRAPER_ROOT_TARGET),
                username=CUTE_SCRAPER_ROOT_TARGET,
                # implies he is the root; this is default
                own_depth=0,
                # max number of additional targets to add on when scraping
                max_depth=4,
                # this is more of a suggestion. we fetch up to the closest number of
                # pages that we expect to return this limit, so you may get slightly
                # more or less than this
                max_tweets=600,
            )
            session.add(root)
            session.commit()
            root_job_id = root.job_id

        logger.info(f'JOB: {root_job_id} starting...')

        driver: Optional[webdriver.Remote] = None

        for target in list_targets(session, root_job_id):
            logger.info(
                f'JOB: {target.job_id} | TARGET: {target.username} | DEPTH {target.own_depth}'
            )
            scraper = AuthenticatedScraper(
                headless=True,
                username=target.username,
                credentials=Credentials(
                    CUTE_SCRAPER_USERNAME,
                    CUTE_SCRAPER_PASSWORD
                ),
                profile_dir=CUTE_SCRAPER_PROFILE_DIR,
                user_data_dir=CUTE_SCRAPER_USER_DATA_DIR,
                driver=driver,
                wait_time=10
            )
            # cache the driver if we have one, saves a lot of time
            driver = scraper._driver
            scrape(scraper, session, target)
            session.commit()

        if driver is not None:
            driver.close()

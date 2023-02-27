# TODO: stop when we see duplicate data?
# TODO: fetch likes (may need authentication for this)
# TODO: should new user in the replies get added as target?
# TODO(optional): better way to handle job state
from typing import List, Optional, Generator

from selenium import webdriver
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as sqlite_insert

from models import init_db
from models.target import Target, JobStatus, new_job_id

from common.logging import logger
from scrapers import exceptions
from scrapers.abstract import Scraper
from scrapers.authenticated import AuthenticatedScraper
from vendor.scweet.credentials import Credentials


def get_db_engine() -> Engine:
    from os import environ as env
    url = URL.create(
        drivername='postgresql',
        username=env.get('CUTE_PG_USER'),
        password=env.get('CUTE_PG_PASSWORD'),
        host=env.get('CUTE_PG_HOST'),
        database=env.get('CUTE_PG_DATABASE'),
        port=env.get('CUTE_PG_PORT')
    )
    return create_engine(url)


class Statement:
    @staticmethod
    def add_targets_statement(targets: List[Target]):
        '''
        Insert targets, ignore duplicates
        '''
        return sqlite_insert(Target).values([
            dict(
                id=target.id,
                username=target.username,
                own_depth=target.own_depth,
                max_depth=target.max_depth,
                max_tweets=target.max_tweets
            )
            for target in targets
        ]).on_conflict_do_nothing(index_elements=[Target.id, Target.username])


def scrape(scraper: Scraper, session: Session, target: Target):
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
        for follow in scraper.get_following():
            # TODO: it's actually possible to get user ID here which is more
            # stable than username (can use the unauthenticated scraper for it)
            session.merge(follow)
            logger.debug(
                f'{target.username}: found following {follow.followed_by_username}'
            )
            if target.own_depth < target.max_depth:
                session.execute(
                    Statement.add_targets_statement(
                        [target.create_child(follow.followed_by_username)]
                    )
                )

        # save tweets
        logger.debug(f'{target.username}: getting tweets + replies')
        for tweet in scraper.get_tweets(max_tweets=target.max_tweets):
            logger.debug(
                f'{target.username}: tweet id {tweet.rest_id} ({tweet.content[:20]}...)'
            )
            session.merge(tweet)

    except exceptions.UserNotFound as e:
        logger.warning(f'(user not found) skipping {e.username}')
        finish()
    except exceptions.UserProtected as e:
        logger.warning(f'(user is protected) skipping {e.username}')
        finish()
    except exceptions.UnknownException as e:
        logger.error(f'(tweety error) {e.username}, {e.info}')
        error()
    except KeyboardInterrupt:
        logger.error(f'(keyboard interrupt) {target.username}')
        error()
        raise
    except Exception as e:
        logger.error(f'(unknown error) {target.username}, {e}')
        error()
    else:
        finish()


def list_targets(job_id: str) -> Generator[Target, None, None]:
    while True:
        target = session.scalars(
            select(Target).where(
                Target.id == job_id,
                Target.status == JobStatus.NEW,
            ).order_by(
                Target.own_depth
            ).limit(1)
        ).first()

        if target is None:
            return

        yield target


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
    init_db(engine)

    with Session(engine) as session:
        if CUTE_SCRAPER_RESUME_JOB_ID:
            root_job_id = CUTE_SCRAPER_RESUME_JOB_ID
        else:
            root = Target(
                id=new_job_id(CUTE_SCRAPER_ROOT_TARGET),
                username=CUTE_SCRAPER_ROOT_TARGET,
                # implies he is the root; this is default
                own_depth=0,
                # max number of additional targets to add on when scraping
                max_branch=None,
                max_depth=4,
                # this is more of a suggestion. we fetch up to the closest number of
                # pages that we expect to return this limit, so you may get slightly
                # more or less than this
                max_tweets=600,
            )
            session.add(root)
            session.commit()
            root_job_id = root.id

        logger.info(f'JOB: {root_job_id} starting...')

        driver: Optional[webdriver.Remote] = None

        for target in list_targets(root_job_id):
            logger.info(
                f'JOB: {target.id} | TARGET: {target.username} | DEPTH {target.own_depth}'
            )
            scraper = AuthenticatedScraper(
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

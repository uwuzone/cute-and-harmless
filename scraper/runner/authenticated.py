'''
Worker initialization:
 - Select all workers and last active time 
'''
import asyncio
import datetime
import os

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from common.logging import logger
from models import get_db_engine
from models.job import Job, JobSource, Worker
from models.job import create_child_job, insert_jobs_on_conflict_ignore
from runner.base import wrap_scraper_exceptions_and_logging, take_job
from scrapers.authenticated import AuthenticatedScraper
from vendor.scweet.credentials import Credentials


def init_chrome_dirs(basedir: str):
    try:
        os.makedirs(os.path.join(basedir, 'user-data'))
        os.makedirs(os.path.join(basedir, 'profile'))
    except FileExistsError:
        pass


def get_user_data_dir(basedir: str, name: str):
    return os.path.join(basedir, 'user-data', name)


def get_profile_dir(basedir: str, name: str):
    return os.path.join(basedir, 'profile', name)


@wrap_scraper_exceptions_and_logging
def scrape(session: Session, scraper: AuthenticatedScraper, job: Job):
    # save accounts followed by target as new targets
    logger.debug('getting following')
    n_following = 0
    for follow in scraper.get_following():
        # TODO: it's actually possible to get user ID here which is more
        # stable than username (can use the unauthenticated scraper for it)
        session.merge(follow)
        logger.debug(f'is following {follow.follows_username}')
        if job.own_depth < job.max_depth:
            session.execute(
                insert_jobs_on_conflict_ignore(
                    create_child_job(
                        job, follow.follows_username, source=JobSource.FOLLOWING, authenticated=True),
                    create_child_job(
                        job, follow.follows_username, source=JobSource.FOLLOWING, authenticated=False),
                )
            )
        session.commit()
        n_following += 1
    logger.debug(f'saved {n_following} following')


async def take_worker(session: Session, cooldown_period: int, polling_interval: int = 3,):
    '''
    Get next available worker. Cooldown is based on db value.

    :cooldown_period cooldown in seconds (default: 8 hours)
    :max_jobs max jobs to run before going on cooldown (+/- a random jitter) (default: 5)
    '''
    while True:
        current_time = datetime.datetime.utcnow()
        cooldown_threshold = current_time - \
            datetime.timedelta(seconds=cooldown_period)

        subq = (
            select(Worker.id)
            .filter(or_(Worker.last_active == None, Worker.last_active >= cooldown_threshold))
            .order_by(Worker.last_active)
            .limit(1)
            .subquery()
        )
        workers = session.scalars(
            update(Worker)
            .values(last_active=current_time)
            .where(Worker.id.in_(select(subq)))
            .returning(Worker)
        ).all()

        if len(workers) > 1:
            raise Exception('my friend your sql are fucked 🙏😑')

        if len(workers) == 1:
            logger.debug(f'workers: {workers}')
            # session.commit()
            return workers[0]

        await asyncio.sleep(polling_interval)


async def run(concurrency: int, worker_cooldown: int, chrome_data_basedir: str):
    '''
    NB: concurrency should be kept pretty low. Also, it's bounded by how many
    scraper accounts you have available.
    '''
    engine = get_db_engine()
    init_chrome_dirs(chrome_data_basedir)

    async def worker(i: int):
        logger.debug(f'Starting authenticated worker {i}/{concurrency}')
        while True:
            with Session(engine) as session:
                worker_config = await take_worker(session, cooldown_period=worker_cooldown)
                job = await take_job(session, authenticated=True)
                scraper = AuthenticatedScraper(
                    headless=True,
                    username=job.username,
                    credentials=Credentials(
                        worker_config.twitter_username,
                        worker_config.twitter_password,
                    ),
                    profile_dir=get_profile_dir(
                        chrome_data_basedir,
                        worker_config.twitter_username,
                    ),
                    user_data_dir=get_user_data_dir(
                        chrome_data_basedir,
                        worker_config.twitter_username,
                    ),
                    wait_time=10
                )
                await asyncio.to_thread(scrape, session, scraper, job)

    await asyncio.gather(*[
        worker(i + 1) for i in range(concurrency)
    ])

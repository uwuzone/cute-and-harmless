from __future__ import annotations

import asyncio

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from common.logging import logger
from models.job import Job, JobStatus
from scrapers.abstract import Scraper
from scrapers import exceptions


async def take_job(session: Session, authenticated: bool, polling_interval: int = 3) -> Job:
    while True:
        subq = (
            select(Job.internal_id)
            .filter(Job.status == JobStatus.NEW, Job.is_authenticated == authenticated)
            .order_by(Job.own_depth, Job.created_at.desc())
            .limit(1)
            .subquery()
        )
        jobs = session.scalars(
            update(Job)
            .values(status=JobStatus.RUNNING)
            .where(Job.internal_id.in_(select(subq)))
            .returning(Job)
        ).all()

        if len(jobs) > 1:
            raise Exception('my friend your sql are fucked 🙏😑')

        if len(jobs) == 1:
            session.commit()
            return jobs[0]

        await asyncio.sleep(polling_interval)


def wrap_scraper_exceptions_and_logging(func):
    def wrapped(session: Session, scraper: Scraper, target: Job, *args, **kwargs):
        def start():
            target.status = JobStatus.RUNNING
            session.merge(target)
            session.commit()

        def finish():
            target.status = JobStatus.FINISHED
            session.merge(target)
            session.commit()

        def error():
            target.status = JobStatus.ERROR
            session.merge(target)
            session.commit()

        with logger.contextualize(scraper=scraper.id(), target=target.username, job=target.job_id):
            try:
                start()
                func(session, scraper, target, *args, **kwargs)
            except exceptions.UserNotFound as e:
                logger.warning(f'(user not found) skipping {e.username}')
                finish()
            except exceptions.UserProtected as e:
                logger.warning(f'(user is protected) skipping {e.username}')
                finish()
            except exceptions.UnknownException as e:
                logger.error(f'(unknown scraper error) {e.username}, {e.info}')
                error()
            except KeyboardInterrupt as e:
                logger.error(f'(keyboard interrupt) {target.username}')
                error()
                raise e
            except Exception as e:
                logger.error(
                    f'(completely unanticipated error) {target.username}, {e}')
                error()
            else:
                finish()

    return wrapped

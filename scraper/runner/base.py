from __future__ import annotations

import asyncio

from typing import Optional

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from common.logging import logger
from models.target import JobStatus
from models.target import Target
from scrapers.abstract import Scraper
from scrapers import exceptions


def get_target(session: Session, authenticated: bool) -> Optional[Target]:
    if authenticated:
        return session.scalars(
            select(Target).where(
                Target.following_scraped == False,
                # TODO/XXX: this is a bad idea, better to have multiple job types
                Target.status != JobStatus.ERROR,
                Target.status != JobStatus.FINISHED,
            ).order_by(
                Target.own_depth
            ).limit(1)
        ).first()
    else:
        return session.scalars(
            select(Target).where(
                Target.tweets_scraped == False,
                Target.status != JobStatus.ERROR,
                Target.status != JobStatus.FINISHED,
            ).order_by(
                Target.own_depth
            ).limit(1)
        ).first()


async def take_target(engine: Engine, authenticated: bool, polling_interval: int = 15):
    with Session(engine) as session:
        while True:
            target = get_target(session, authenticated=authenticated)

            if target is not None:
                return target

            await asyncio.sleep(polling_interval)


def wrap_scraper_exceptions_and_logging(func):
    def wrapped(session: Session, scraper: Scraper, target: Target, *args, **kwargs):
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

        with logger.contextualize(scraper=scraper.id(), target=target.username, job=target.id):
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
                logger.error(f'(completely unanticipated error) {target.username}, {e}')
                error()
                raise e
            else:
                finish()

    return wrapped

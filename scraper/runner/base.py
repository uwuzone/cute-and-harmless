from __future__ import annotations

from sqlalchemy.orm import Session

from common.logging import logger
from models.base import JobBase, JobStatus
from scrapers.abstract import Scraper
from scrapers import exceptions


def wrap_scraper_exceptions_and_logging(func):
    def wrapped(session: Session, scraper: Scraper, target: JobBase, *args, **kwargs):
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

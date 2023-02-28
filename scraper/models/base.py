import datetime
from enum import Enum

from sqlalchemy.sql import func
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped


class Base(DeclarativeBase):
    pass


class ScrapeBase(DeclarativeBase):
    scraped_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now()
    )


class JobStatus(Enum):
    NEW = 'new'
    RUNNING = 'running'
    FINISHED = 'finished'
    ERROR = 'error'


class JobType(Enum):
    # get new targets (using following/followers)
    FOLLOWING = 'following'
    TWEETS = 'tweets'


class JobBase(DeclarativeBase):
    job_id: Mapped[str] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(primary_key=True)
    status: Mapped[JobStatus] = mapped_column(default=JobStatus.NEW)
    created_at: Mapped[datetime.datetime] = mapped_column(default=func.now())

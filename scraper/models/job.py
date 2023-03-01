from __future__ import annotations

import datetime

from enum import Enum
from typing import Optional
from sqlalchemy import UniqueConstraint

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from sqlalchemy.sql import func

from models.base import Base


class JobStatus(Enum):
    NEW = 'new'
    RUNNING = 'running'
    FINISHED = 'finished'
    ERROR = 'error'


class JobSource(Enum):
    MANUAL = 'manual'
    TWEET_REPLY = 'reply'
    FOLLOWING = 'following'


class JobType(Enum):
    # get new targets (using following/followers)
    FOLLOWING = 'following'
    TWEETS = 'tweets'


def new_job_id(root_username: str):
    return f'{root_username}-{int(datetime.datetime.now().timestamp())}'


class Worker(Base):
    __tablename__ = 'worker'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    twitter_username: Mapped[str]
    twitter_password: Mapped[str]
    proxy: Mapped[Optional[str]]

    last_active: Mapped[Optional[datetime.datetime]]

    __table_args__ = (UniqueConstraint(
        'twitter_username', name='worker_uniqueness'),)


class Job(Base):
    __tablename__ = 'job'

    __table_args__ = (UniqueConstraint('job_id', 'username',
                      'is_authenticated', name='job_uniqueness'),)

    # makes things easier to have a single unique ID to refer to
    internal_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True)

    source: Mapped[JobSource]

    job_id: Mapped[str]
    username: Mapped[str]
    is_authenticated: Mapped[bool]

    status: Mapped[JobStatus] = mapped_column(default=JobStatus.NEW)
    created_at: Mapped[datetime.datetime] = mapped_column(default=func.now())

    # 0 if this is the root
    own_depth: Mapped[int]
    max_depth: Mapped[int]
    max_tweets: Mapped[int]
    max_followers: Mapped[int]


def create_child_job(job: Job, username: str, source: JobSource, authenticated: Optional[bool] = None):
    '''Make a child target with settings copied and depth incremented.
    Caller must save.'''
    return Job(
        job_id=job.job_id,
        username=username,
        source=source,
        is_authenticated=authenticated if authenticated is not None else job.is_authenticated,
        own_depth=job.own_depth+1,
        max_tweets=job.max_tweets,
        max_depth=job.max_depth,
        max_followers=job.max_followers,
    )


def insert_jobs_on_conflict_ignore(*following_jobs: Job):
    '''
    Insert targets, ignore duplicates
    '''
    return pg_insert(Job).values([
        dict(
            job_id=job.job_id,
            username=job.username,
            own_depth=job.own_depth,
            max_depth=job.max_depth,
            max_tweets=job.max_tweets,
            max_followers=job.max_followers,
            is_authenticated=job.is_authenticated
        )
        for job in following_jobs
    ]).on_conflict_do_nothing(index_elements=[Job.job_id, Job.username, Job.is_authenticated])

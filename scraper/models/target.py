from __future__ import annotations
import datetime

from enum import Enum
from typing import List, Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql import func
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped

from models.base import Base


def new_job_id(root_username: str):
    return f'{root_username}-{int(datetime.datetime.now().timestamp())}'


class JobStatus(Enum):
    NEW = 'new'
    RUNNING = 'running'
    FINISHED = 'finished'
    ERROR = 'error'


class JobType(Enum):
    # get new targets (using following/followers)
    FOLLOWING = 'following'
    TWEETS = 'tweets'


class Worker(Base):
    __tablename__ = 'worker'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    twitter_username: Mapped[str]
    twitter_password: Mapped[str]

    last_active: Mapped[Optional[datetime.datetime]]


class Target(Base):
    '''
    Each new account is a target with a depth. 0 = it's the root

    if own_depth = max_crawl_depth then worker should not enqueue new accounts that it sees
    '''
    __tablename__ = 'target'

    id: Mapped[str] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(primary_key=True)
    status: Mapped[JobStatus] = mapped_column(default=JobStatus.NEW)

    following_scraped: Mapped[bool] = mapped_column(default=False)
    tweets_scraped: Mapped[bool] = mapped_column(default=False)

    # 0 if this is the root
    own_depth: Mapped[int]
    max_depth: Mapped[int]
    max_tweets: Mapped[int]
    max_followers: Mapped[int]

    created_at: Mapped[datetime.datetime] = mapped_column(default=func.now())

    def create_child(self, username: str) -> Target:
        '''Make a child target with settings copied and depth incremented.
        Caller must save.'''
        return Target(
            id=self.id,
            username=username,
            own_depth=self.own_depth+1,
            max_depth=self.max_depth,
            max_tweets=self.max_tweets,
            max_followers=self.max_followers,
        )


def insert_targets_on_conflict_ignore(targets: List[Target]):
    '''
    Insert targets, ignore duplicates
    '''
    return pg_insert(Target).values([
        dict(
            id=target.id,
            username=target.username,
            own_depth=target.own_depth,
            max_depth=target.max_depth,
            max_tweets=target.max_tweets,
            max_followers=target.max_followers
        )
        for target in targets
    ]).on_conflict_do_nothing(index_elements=[Target.id, Target.username])

from __future__ import annotations
import datetime

from enum import Enum
from typing import Optional

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


class Target(Base):
    '''
    Each new account is a target with a depth. 0 = it's the root

    if own_depth = max_crawl_depth then worker should not enqueue new accounts that it sees
    '''
    __tablename__ = 'target'

    id: Mapped[str] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(primary_key=True)
    status: Mapped[JobStatus] = mapped_column(default=JobStatus.NEW)

    # 0 if this is the root
    own_depth: Mapped[int] = mapped_column(default=0)
    max_depth: Mapped[int] = mapped_column(default=4)

    # max number of additional targets to add on when scraping an account
    # None implies no limit
    max_branch: Mapped[Optional[int]]
    max_tweets: Mapped[Optional[int]]

    created_at: Mapped[datetime.datetime] = mapped_column(default=func.now())
    started_at: Mapped[Optional[datetime.datetime]]
    updated_at: Mapped[Optional[datetime.datetime]]

    def create_child(self, username: str) -> Target:
        '''Make a child target with settings copied and depth incremented.
        Caller must save.'''
        return Target(
            id=self.id,
            username=username,
            own_depth=self.own_depth+1,
            max_branch=self.max_branch,
            max_depth=self.max_depth,
            max_tweets=self.max_tweets,
        )

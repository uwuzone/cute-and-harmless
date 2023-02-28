from __future__ import annotations
import datetime

from typing import List, Optional, Tuple

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped

from models.base import Base, JobBase


def new_job_id(root_username: str):
    return f'{root_username}-{int(datetime.datetime.now().timestamp())}'


class Worker(Base):
    __tablename__ = 'worker'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    twitter_username: Mapped[str]
    twitter_password: Mapped[str]

    last_active: Mapped[Optional[datetime.datetime]]


class TweetJob(JobBase):
    __tablename__ = 'tweet_job'

    max_tweets: Mapped[int]


class FollowingJob(JobBase):
    '''
    Job for scraping an account's "following" list. This kind of job requires
    authentication.

    if own_depth = max_crawl_depth then worker should not enqueue new accounts that it sees
    '''
    __tablename__ = 'following_job'

    # 0 if this is the root
    own_depth: Mapped[int]
    max_depth: Mapped[int]
    max_tweets: Mapped[int]
    max_followers: Mapped[int]

    def create_child(self, username: str) -> Tuple[FollowingJob, TweetJob]:
        '''Make a child target with settings copied and depth incremented.
        Caller must save.'''
        following = FollowingJob(
            job_id=self.job_id,
            username=username,
            own_depth=self.own_depth+1,
            max_tweets=self.max_tweets,
            max_depth=self.max_depth,
            max_followers=self.max_followers,
        )
        tweets = TweetJob(
            job_id=self.job_id,
            username=username,
            max_tweets=self.max_tweets,
        )

        return [following, tweets]


def insert_following_jobs_on_conflict_ignore(following_jobs: List[FollowingJob]):
    '''
    Insert targets, ignore duplicates
    '''
    return pg_insert(FollowingJob).values([
        dict(
            job_id=job.job_id,
            username=job.username,
            own_depth=job.own_depth,
            max_depth=job.max_depth,
            max_tweets=job.max_tweets,
            max_followers=job.max_followers
        )
        for job in following_jobs
    ]).on_conflict_do_nothing(index_elements=[FollowingJob.job_id, FollowingJob.username])


def insert_tweet_jobs_on_conflict_ignore(tweet_jobs: List[TweetJob]):
    '''
    Insert targets, ignore duplicates
    '''
    return pg_insert(TweetJob).values([
        dict(
            job_id=job.job_id,
            username=job.username,
            max_tweets=job.max_tweets,
        )
        for job in tweet_jobs
    ]).on_conflict_do_nothing(index_elements=[TweetJob.job_id, TweetJob.username])

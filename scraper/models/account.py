import datetime

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from models.base import ScrapeBase


class Account(ScrapeBase):
    __tablename__ = 'account'

    # the numerical-looking ID used by API 1.1
    rest_id: Mapped[str] = mapped_column(primary_key=True)
    # tweets: Mapped[List['Tweet']] = relationship(
    #     foreign_keys='Tweet.author_rest_id')

    profile_url: Mapped[str]
    display_name: Mapped[str]
    username: Mapped[str] = mapped_column(index=True)
    joined_at: Mapped[datetime.datetime]
    description: Mapped[str]
    location: Mapped[str]
    protected: Mapped[bool]
    verified: Mapped[bool]

    followers_count: Mapped[int]
    following_count: Mapped[int]
    statuses_count: Mapped[int]
    favourites_count: Mapped[int]

    # tw_possibly_sensitive: Mapped[Optional[bool]]
    # tw_verified_type: Mapped[Optional[str]]

    # tw_normal_followers_count: Mapped[int]
    # tw_statuses_count: Mapped[int]
    # tw_media_count: Mapped[int]
    # tw_listed_count: Mapped[int]
    # tw_fast_followers_count: Mapped[int]
    # tw_favourites_count: Mapped[int]
    # tw_followers_count: Mapped[int]
    # what the API calls follows (not the same as mutuals! lol!)
    # tw_friends_count: Mapped[int]

import datetime

from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped

from models.base import ScrapeBase


class Tweet(ScrapeBase):
    __tablename__ = 'tweet'

    rest_id: Mapped[str] = mapped_column(primary_key=True)
    created_on: Mapped[datetime.datetime]
    content: Mapped[str]

    author_rest_id: Mapped[str] = mapped_column(ForeignKey('account.rest_id'),)

    reply_count: Mapped[int]
    like_count: Mapped[int]
    retweet_count: Mapped[int]
    quote_count: Mapped[int]

    is_retweet: Mapped[bool]

    is_reply: Mapped[bool]
    reply_to_account_rest_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey('account.rest_id'))

    reply_to_tweet_rest_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey('tweet.rest_id'))

    tw_is_possibly_sensitive: Mapped[bool]
    # tw_vibe: Mapped[str]
    # tw_is_quoted: Mapped[str]
    # tw_quoted_tweet: Mapped[str]
    # tw_quote_counts: Mapped[str]
    # tw_tweet_body: Mapped[str]
    # tw_language: Mapped[str]
    # tw_card: Mapped[str]
    # tw_place: Mapped[str]
    # tw_source: Mapped[str]
    # tw_media: Mapped[str]
    # tw_user_mentions: Mapped[str]
    # tw_urls: Mapped[str]
    # tw_hashtags: Mapped[str]
    # tw_symbols: Mapped[str]
    # TODO/XXX: library needs patch to make this the tweet being replied to, or
    # at least the rest ID because this is not necessarily a stable value
    # though not really a big deal
    # reply_to: Mapped[Optional[str]]
    # threads: Mapped[str]
    # comments: Mapped[str]

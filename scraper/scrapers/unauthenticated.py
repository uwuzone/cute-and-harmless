from __future__ import annotations

from math import ceil
from typing import Generator, Optional

from tweety import exceptions_ as tw_exceptions
from tweety.bot import Twitter as Bot

from models.account import Account
from models.interaction import Tweet
from models.interaction import Follow
from scrapers import exceptions
from scrapers.abstract import Scraper


def wrap_exceptions(func):
    def wrapped(self: UnauthenticatedScraper, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except tw_exceptions.UserNotFound:
            raise exceptions.UserNotFound(self._username)
        except tw_exceptions.UserProtected:
            print('WTF')
            raise exceptions.UserProtected(self._username)
        except tw_exceptions.UnknownError as e:
            raise exceptions.UnknownException(self._username, e.message)

    return wrapped


class UnauthenticatedScraper(Scraper):
    '''
    An unauthenticated scraper which can get public tweets + replies but not
    likes/follows/following. This should be used for the bulk of tweet scraping
    tasks, as it doesn't risk your account getting banned.
    '''

    _bot: Optional[Bot]

    def __init__(self, username: str, wait_time: int = 2):
        self._bot = None
        super().__init__(username, wait_time)

    def id(self) -> str:
        return f'anonymous-scraper:{self._username}'

    # wtf why is this necessary LOL
    @wrap_exceptions
    def _get_bot(self, username: str) -> Bot:
        if self._bot is None or self._bot.user.name != username:
            self._bot = Bot(username)

        return self._bot

    @wrap_exceptions
    def get_user_info(self) -> Account:
        user_info = self._get_bot(self._username).get_user_info()
        return Account(
            profile_url=user_info.profile_url,
            rest_id=user_info.rest_id,
            display_name=user_info.name,
            username=user_info.screen_name,
            joined_at=user_info.created_at,
            description=user_info.description,
            location=user_info.location,
            protected=user_info.protected,
            verified=user_info.verified,
            followers_count=user_info.followers_count,
            following_count=user_info.friends_count,
            statuses_count=user_info.statuses_count,
            favourites_count=user_info.fast_followers_count,
        )

    # TODO: a generator fork of tweety is preferable because we won't lose
    # progress if fetching fails partway through. however, since this is
    # unauthenticated, it's low risk
    @wrap_exceptions
    def get_tweets(self, include_replies: bool = True, max_tweets: int = 200) -> Generator[Tweet, None, None]:
        pages = max(ceil(max_tweets / 20), 1)
        # XXX: this is untyped in the library :skull:
        all_tweets = self._get_bot(self._username).get_tweets(
            replies=include_replies,
            pages=pages,
            wait_time=self._wait_time
        )
        for _tweet in all_tweets:
            raw: dict = _tweet._get_original_tweet()
            yield Tweet(
                # TODO(fork): these fields all come from fuken around in the
                # repl as this is untyped in the library
                rest_id=_tweet.id,
                created_on=_tweet.created_on,
                content=_tweet.text,
                author_rest_id=_tweet.author.rest_id,
                reply_count=_tweet.reply_counts,  # yes, it is plural from API
                like_count=_tweet.likes,
                retweet_count=_tweet.retweet_counts,
                quote_count=_tweet.quote_counts,
                is_retweet=_tweet.is_retweet,
                is_reply=_tweet.is_reply,
                reply_to_account_rest_id=raw.get(
                    'in_reply_to_user_id_str', None),
                reply_to_tweet_rest_id=raw.get(
                    'in_reply_to_status_id_str', None),
                # tw_is_possibly_sensitive=_tweet.is_possibly_sensitive,
            )

    @wrap_exceptions
    def get_following(self) -> Generator[Follow, None, None]:
        return super().get_following()

    @wrap_exceptions
    def get_followers(self) -> Generator[Follow, None, None]:
        return super().get_followers()

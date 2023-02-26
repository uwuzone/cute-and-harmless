from abc import ABC, abstractmethod
from typing import Generator

from models.account import Account
from models.interaction import Tweet
from models.interaction import Follow


class Scraper(ABC):
    _wait_time: int
    _username: str

    def __init__(self, username: str, wait_time: int = 2):
        self._wait_time = wait_time
        self._username = username

    @abstractmethod
    def get_user_info(self) -> Account:
        pass

    # TODO: make a generator version..
    @abstractmethod
    def get_tweets(self, include_replies: bool = True, max_tweets: int = 200) -> Generator[Tweet, None, None]:
        yield from []

    @abstractmethod
    def get_following(self) -> Generator[Follow, None, None]:
        yield from []

    @abstractmethod
    def get_followers(self) -> Generator[Follow, None, None]:
        yield from []

    # @abstractmethod
    # def get_thread(self, tweet_id: str):
    #     pass

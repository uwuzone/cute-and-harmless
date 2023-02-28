from __future__ import annotations

from typing import Optional, Generator

from selenium import webdriver

from models.account import Account
from models.interaction import Tweet
from models.interaction import Follow

from common.logging import logger
from scrapers import exceptions
from scrapers.abstract import Scraper
from scrapers.unauthenticated import UnauthenticatedScraper

from vendor.scweet import utils
from vendor.scweet.credentials import Credentials
from vendor.scweet.utils import init_driver


def wrap_exceptions(func):
    def wrapped(self: AuthenticatedScraper, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            raise exceptions.UnknownException(self._username, e)

    return wrapped


class AuthenticatedScraper(Scraper):
    _credentials: Credentials
    _driver: Optional[webdriver.Remote]
    _unauthenticated: Optional[UnauthenticatedScraper]
    _user_data_dir: Optional[str]
    _profile_dir: Optional[str]
    _headless: bool

    def __init__(
        self,
        username: str,
        credentials: Credentials,
        driver: Optional[webdriver.Remote] = None,
        headless: Optional[bool] = False,
        user_data_dir: Optional[str] = None,
        profile_dir: Optional[str] = None,
        wait_time: int = 2
    ):
        self._credentials = credentials
        self._unauthenticated = None
        self._driver = driver
        self._user_data_dir = user_data_dir
        self._profile_dir = profile_dir
        self._headless = headless or False
        super().__init__(username, wait_time)

    def id(self) -> str:
        return f'authenticated-scraper({self._credentials.username}):{self._username}'

    def _get_driver(self):
        if self._driver is None:
            logger.debug(
                f'getting driver {self._user_data_dir} {self._profile_dir}'
            )
            self._driver = init_driver(
                headless=self._headless,
                profile_dir=self._profile_dir,
                user_data_dir=self._user_data_dir
            )
        return self._driver

    def _get_unauthenticated_scraper(self, username: str) -> UnauthenticatedScraper:
        if self._unauthenticated is None or self._unauthenticated._username != username:
            self._unauthenticated = UnauthenticatedScraper(username)

        return self._unauthenticated

    def get_user_info(self) -> Account:
        return self._get_unauthenticated_scraper(self._username).get_user_info()

    def get_tweets(self, *args, **kwargs) -> Generator[Tweet, None, None]:
        return self._get_unauthenticated_scraper(self._username).get_tweets(*args, **kwargs)

    @wrap_exceptions
    def get_following(self, limit: int = 200) -> Generator[Follow, None, None]:
        following = utils.get_follow(
            self._get_driver(),
            self._username,
            headless=False,
            credentials=self._credentials,
            follow='following',
            verbose=True,
            wait=self._wait_time,
            limit=limit
        )
        for username in following:
            yield Follow(
                follows_username=username,
                followed_by_username=self._username
            )

    @wrap_exceptions
    def get_followers(self, limit: int = 200) -> Generator[Follow, None, None]:
        followers = utils.get_follow(
            self._get_driver(),
            self._username,
            headless=False,
            credentials=self._credentials,
            follow='followers',
            verbose=True,
            wait=self._wait_time,
            limit=limit
        )
        for username in followers:
            yield Follow(
                follows_username=self._username,
                followed_by_username=username
            )

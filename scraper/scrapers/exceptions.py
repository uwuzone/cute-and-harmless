from typing import Any, Optional


class ScraperException(Exception):
    username: str  # TODO: this is kinda pointless

    def __init__(self, username: str, *args: object) -> None:
        self.username = username
        super().__init__(*args)


class UserNotFound(ScraperException):
    pass


class UserProtected(ScraperException):
    pass


class UnknownException(ScraperException):
    info: Optional[Any]

    def __init__(self, username: str, info: Optional[Any], *args: object) -> None:
        self.info = info
        super().__init__(username, *args)


# TODO: fill this out

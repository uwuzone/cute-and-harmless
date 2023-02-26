import datetime

from sqlalchemy.sql import func
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped


class Base(DeclarativeBase):
    pass


class ScrapeBase(DeclarativeBase):
    scraped_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now()
    )

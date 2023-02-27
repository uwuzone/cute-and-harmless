from sqlalchemy import Engine
from .base import Base, ScrapeBase


def init_db(engine: Engine):
    Base.metadata.create_all(engine)
    ScrapeBase.metadata.create_all(engine)

from sqlalchemy import URL, Engine, create_engine

from .base import Base, ScrapeBase


def init_db(engine: Engine):
    Base.metadata.create_all(engine)
    ScrapeBase.metadata.create_all(engine)


def get_db_engine(echo: bool = False) -> Engine:
    from os import environ as env

    url = URL.create(
        drivername='postgresql',
        username=env.get('SCRAPER_PG_USER'),
        password=env.get('SCRAPER_PG_PASSWORD'),
        host=env.get('SCRAPER_PG_HOST'),
        database=env.get('SCRAPER_PG_DATABASE'),
        port=env.get('SCRAPER_PG_PORT')
    )

    engine = create_engine(url, echo=echo)

    init_db(engine)

    return engine

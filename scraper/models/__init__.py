from sqlalchemy import URL, Engine, create_engine

from .base import Base, JobBase, ScrapeBase


def init_db(engine: Engine):
    Base.metadata.create_all(engine)
    ScrapeBase.metadata.create_all(engine)
    JobBase.metadata.create_all(engine)


def get_db_engine(echo: bool = False) -> Engine:
    from os import environ as env

    url = URL.create(
        drivername='postgresql',
        username=env.get('CUTE_PG_USER'),
        password=env.get('CUTE_PG_PASSWORD'),
        host=env.get('CUTE_PG_HOST'),
        database=env.get('CUTE_PG_DATABASE'),
        port=env.get('CUTE_PG_PORT')
    )

    engine = create_engine(url, echo=echo)

    init_db(engine)

    return engine

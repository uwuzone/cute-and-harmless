'''
:-3
'''
import asyncio
import os

from common.logging import logger
from runner import run_unauthenticated


SCRAPER_CONCURRENCY = int(os.environ.get('SCRAPER_CONCURRENCY', '2'))
SCRAPER_MAX_JOBS = int(os.environ.get('SCRAPER_CONCURRENCY', '8'))


async def run():
    logger.info(
        f'LAMBDA: starting with concurrency {SCRAPER_CONCURRENCY}, max jobs {SCRAPER_MAX_JOBS}')

    return await run_unauthenticated(
        concurrency=SCRAPER_CONCURRENCY,
        max_jobs=SCRAPER_MAX_JOBS
    )


def handler(_event, _context):
    return asyncio.run(run())

'''
:-3
'''
import asyncio
import os

from runner import run_unauthenticated


SCRAPER_CONCURRENCY = int(os.environ.get('SCRAPER_CONCURRENCY', '4'))
SCRAPER_MAX_JOBS = int(os.environ.get('SCRAPER_CONCURRENCY', '4'))


async def run():
    return await run_unauthenticated(
        concurrency=SCRAPER_CONCURRENCY,
        max_jobs=SCRAPER_MAX_JOBS
    )


def handler(_event, _context):
    return asyncio.run(run())

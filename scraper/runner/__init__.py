
from typing import List, Optional


async def run_authenticated(concurrency: int, worker_cooldown: int, chrome_data_basedir: str):
    from runner import authenticated

    await authenticated.run(
        concurrency=concurrency,
        worker_cooldown=worker_cooldown,
        chrome_data_basedir=chrome_data_basedir
    )


async def run_unauthenticated(concurrency: int, max_jobs: Optional[int] = None) -> List[str]:
    '''
    Run authenticated jobs. Return a list of usernames scraped.

    :concurrency - number of concurrent jobs to run
    :max_jobs - max number of jobs (total) to run before stopping (nb: actual
    number of jobs run will always be at least :concurrency)
    '''
    from runner import unauthenticated

    await unauthenticated.run(concurrency=concurrency, max_jobs=max_jobs)

from __future__ import annotations
import asyncio


from runner.unauthenticated import run_unauthenticated


# async def take_worker(engine: Engine, cooldown_seconds: int = 60*60*12) -> Optional[Worker]:
#     '''Get next available worker that's off cooldown. Immediately marks it as
#     unavailable.'''
#     pass


# async def run_authenticated(concurrency: int = 4):
#     engine = get_db_engine()
#     asyncio.Semaphore(concurrency)

#     while True:
#         worker = await take_worker(engine)


async def main():
    await asyncio.gather(
        run_unauthenticated(concurrency=2)
    )


if __name__ == '__main__':
    asyncio.run(main())

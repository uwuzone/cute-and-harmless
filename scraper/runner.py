from __future__ import annotations

import asyncio

from runner import authenticated, unauthenticated


async def main():
    await asyncio.gather(
        authenticated.run(concurrency=1),
        unauthenticated.run(concurrency=2),
    )


if __name__ == '__main__':
    asyncio.run(main())

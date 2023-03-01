from __future__ import annotations

import asyncio

from runner import unauthenticated


async def main():
    await asyncio.gather(
        unauthenticated.run(concurrency=2)
    )


if __name__ == '__main__':
    asyncio.run(main())

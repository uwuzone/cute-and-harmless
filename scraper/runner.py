from __future__ import annotations

import asyncio
from signal import SIGINT, SIGTERM

from runner import unauthenticated


async def main():
    loop = asyncio.get_running_loop()
    for signal_enum in [SIGINT, SIGTERM]:
        loop.add_signal_handler(signal_enum, loop.stop)

    await asyncio.gather(
        unauthenticated.run(concurrency=2)
    )


if __name__ == '__main__':
    asyncio.run(main())

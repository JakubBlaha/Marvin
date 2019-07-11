import asyncio

from cache import Cacher


class Preloader(Cacher):
    _loop: asyncio.AbstractEventLoop

    def __init__(self, loop: asyncio.AbstractEventLoop, *args, **kw):
        super().__init__(*args, **kw)

        self._loop = loop
        loop.create_task(self._task())

    async def _task(self):
        while self._loop.is_running():
            self._loop.run_in_executor(None, lambda: self.output)
            await asyncio.sleep(self._expire_time)

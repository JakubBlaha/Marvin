import asyncio

from discord import NotFound
from discord.ext.commands import Context


class TimeoutMessage:
    _ctx: Context
    _timeout: int

    def __init__(self, ctx: Context, timeout: int = 5):
        self._ctx = ctx
        self._timeout = timeout

    async def send(self, *args, **kw):
        _msg = await self._ctx.send(*args, **kw)
        await _msg.add_reaction('⏳')
        await asyncio.sleep(self._timeout)
        try:
            await _msg.delete()
        except NotFound:
            pass

    def __str__(self) -> str:
        return self.__class__.__name__

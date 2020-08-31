import asyncio

from discord import Message, NotFound
from discord.ext.commands import Context


class TemporaryMessage:
    _ctx: Context
    _timeout: int
    _msg: Message

    def __init__(self, ctx: Context, timeout: int = 5):
        self._ctx = ctx
        self._timeout = timeout

    async def send(self, *args, **kw):
        """ Send the message. *args and **kw are the message arguments. """
        # Send
        self._msg = await self._ctx.send(*args, **kw)
        await self._msg.add_reaction('⏳')

        # Schedule deletion
        asyncio.get_running_loop().create_task(self.delete(self._timeout))

    async def delete(self, delay: int = None):
        """ Schedule message deletion. """
        await asyncio.sleep(delay)

        try:
            await self._msg.delete()
        except NotFound:
            pass

    def __str__(self) -> str:
        return self.__class__.__name__

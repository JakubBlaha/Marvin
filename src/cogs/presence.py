from typing import List, Tuple

from discord import Game, Status
from discord.ext.commands import Cog
from discord.ext.tasks import loop

from client import Marvin
from remote_config import RemoteConfig


class PresenceCycler(Cog):
    bot: Marvin
    presences: List[Tuple[str, str]]  # [name, status[online, offline, idle, dnd]]

    def __init__(self, bot: Marvin):
        self.bot = bot
        self.presences = []

        self.bot.add_listener(self.restart, 'on_ready')

    async def restart(self):
        # We are gonna retrieve the presence list here
        self.presences = RemoteConfig.presences

        # Restart the loop
        self.loop.start()

    # noinspection PyCallingNonCallable
    @loop(seconds=10)
    async def loop(self):
        if not self.presences:
            return

        self.presences.append(self.presences.pop(0))  # Cycle
        name, status = self.presences[0]
        status = getattr(Status, status)
        await self.bot.change_presence(activity=Game(name=name), status=status)


def setup(bot: Marvin):
    bot.add_cog(PresenceCycler(bot))

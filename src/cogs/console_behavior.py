import logging
from typing import Dict

from discord import Message, User
from discord.ext.commands import Cog, Context, command

import common
from client import Marvin
from command_output import CommandOutputManager
from timeout_message import TimeoutMessage

logger = logging.getLogger('ConsoleCog')


class ConsoleBehavior(Cog, name='Console-like behavior'):
    """
    This cog makes it possible to re-execute commands on message edit, so people don't need to spam commands
    when the command is typed wrong. Plus we can easily edit messages using the up arrow which mimics the
    behavior of most consoles. Adds the `!re` command, so commands can be re-executed faster.
    """

    bot: Marvin

    # A dict storing pairs of [user: last command invocation context]
    _cache: Dict[User, Context] = None

    def __init__(self, bot: Marvin):
        self.bot = bot
        self._cache = {}

        bot.add_listener(self.on_message_edit)
        bot.add_listener(self.on_command_completion)

    async def on_command_completion(self, ctx: Context):
        # We will add the commands in the command cache
        # Skip !re
        if ctx.command == self.re:
            return

        self._cache[ctx.author] = ctx

    async def on_message_edit(self, _, new: Message):
        # We are gonna try to execute a command once again.
        await self.bot.process_commands(new)

    @command()
    async def re(self, ctx: Context):
        """
        Re-execute your last command.

        The last output will be overwritten.
        """

        try:
            # Get the last message from the user that invoked a command
            cached_ctx = self._cache[ctx.author]
        except KeyError:
            # No command found in cache
            await TimeoutMessage(ctx).send(embed=common.Embed.NO_COMMAND_EXECUTED_YET)
        else:
            # Invoke command
            fake_msg: Message = ctx.message
            fake_msg.content = cached_ctx.message.content
            await self.bot.process_commands(fake_msg)
            # Delete last output
            try:
                await CommandOutputManager.store[cached_ctx].msg.delete()
            except KeyError:
                logger.info(f'Command output of a command {cached_ctx.command} could not be retrieved!')


def setup(bot: Marvin):
    bot.add_cog(ConsoleBehavior(bot))

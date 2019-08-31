from __future__ import annotations

from typing import Union, Dict

from discord import Embed, User, Message
from discord.ext.commands import Context

from client import FreefClient
from utils import WideEmbed


class CommandOutputManager:
    bot: FreefClient = None

    store: Dict[Context, CommandOutput] = {}

    @classmethod
    def add(cls, command_output: CommandOutput):
        """ Store the command output. Can be accessed later with the invocation message. """
        cls.store[command_output.ctx] = command_output

    @classmethod
    def get(cls, ctx: Context) -> Union[None, CommandOutput]:
        """ Get the stored command output associated with the invocation message. """
        return cls.store.get(ctx)


class CommandOutput:
    ctx: Context = None
    embed: Embed = None
    msg: Message = None

    def __init__(self, ctx: Context, invoc: Union[bool, str] = True, author: Union[bool, User] = True, wide=False,
                 **kw):
        """
        Create a command output, which will be stored in the CommandOutputManager for later use.

        :param ctx: The context of the command.
        :param invoc: Whether to automatically include the invocation string or the string to use.
        :param author: Whether to automatically include the author or the author to use.
        :param wide: Whether a wide embed should be used.
        :param kw: Additional embed keyword arguments which will be used to build the embed.
        """

        # Save context
        self.ctx = ctx

        # Build embed
        if wide:
            self.embed = WideEmbed.from_dict(kw)
        else:
            self.embed = Embed.from_dict(kw)
        # Add the invocation message to the end of the description
        invoc = invoc if isinstance(invoc, str) else invoc and ctx.message.clean_content
        if invoc:
            self.embed.description = _desc = self.embed.description or ''
            self.embed.description += '\n' if _desc.endswith('```') else '\n\n'
            self.embed.description += f'`{invoc}`'
        # Add the author
        if author:
            author = author if isinstance(author, User) else ctx.author
            self.embed.set_author(name=author.display_name, icon_url=author.avatar_url)

    def store(self):
        """ Store the command output in the CommandOutputManager. """

    async def send(self, register=True, **kw):
        """
        Send to the context and add in the CommandOutputManager.

        :param register: Whether to add the output to the CommandOutputManager. Can be used to hide
            the command output from other components of the bot and therefore prevent it from being
            deleted when set to False.
        :param kw: Additional keyword arguments used in the send coroutine.
        """

        self.msg = await self.ctx.send(embed=self.embed, **kw)
        if register:
            CommandOutputManager.add(self)

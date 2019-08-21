from __future__ import annotations

import datetime
import logging
from typing import Union, Optional, AsyncIterable

import discord.utils
from discord import Embed, Message, TextChannel
from discord.ext import tasks
from discord.ext.commands import Cog, command, Context

import utils
from client import FreefClient
from decorators import del_invoc, start_when_needed

logger = logging.getLogger('EmbedManager')


class DatedEmbed(Embed):
    """ A subclass of discord.Embed allowing for easy date comparison. """

    date: datetime.date
    msg: Message

    def __init__(self, date: datetime.date, msg: Optional[Message] = None, embed: Optional[Embed] = None, **kw):
        """
        :param date: The date to be stored.
        :param msg_id: The msg that will be stored for later use.
        :param embed: The embed which's data will be used.
        :param kw: Keyword arguments for the embed. Priority will be given to these over the embed argument.
        """

        self.msg = msg
        self.date = date

        super().__init__(**{**embed.to_dict(), **kw})

    def __lt__(self, other: Union[DatedEmbed, datetime.date]):
        if isinstance(other, DatedEmbed):
            return self.date < other.date
        if isinstance(other, datetime.date):
            return self.date < other
        else:
            raise ValueError(f'Cannot compare to {type(other)}!')

    def __gt__(self, other: Union[DatedEmbed, datetime.date]):
        if isinstance(other, DatedEmbed):
            return self.date > other.date
        if isinstance(other, datetime.date):
            return self.date > other
        else:
            raise ValueError(f'Cannot compare to {type(other)}!')


class EmbedManager(Cog):
    CACHE_KEY = 'EmbedManager'
    REACTION_OUTDATED = '❌'
    CHANNEL_EMOJI = '🔔'

    bot: FreefClient

    def __init__(self, bot: FreefClient):
        self.bot = bot

    @property
    async def embeds(self, from_all_channels: bool = False) -> AsyncIterable[DatedEmbed]:
        """ Return a list of all the guild embeds in bell marked channels. """
        await self.bot.wait_until_ready()

        # Get channels
        if from_all_channels:
            channels = self.bot.guild.text_channels
        else:
            channels = list(filter(lambda x: self.CHANNEL_EMOJI in (x.topic or ''), self.bot.guild.text_channels))

        # Yield embeds
        for channel in channels:
            async for msg in channel.history():
                if msg.embeds:
                    embed = msg.embeds[0]
                    yield DatedEmbed(utils.Datetime.from_string(embed.description or ''), msg, embed)

    # noinspection PyCallingNonCallable
    @start_when_needed()
    @tasks.loop(minutes=10)
    async def mark_loop(self):
        await self.bot.wait_until_ready()

        # Do the marking
        async for embed in self.embeds:
            if utils.EmbedUtils.is_outdated(embed):
                await embed.msg.add_reaction(self.REACTION_OUTDATED)
            else:
                # Remove X reactions from all users, cause people like adding
                # meaningless reactions
                for reaction in embed.msg.reactions:
                    if reaction.emoji == self.REACTION_OUTDATED:
                        async for user in reaction.users():
                            await embed.msg.remove_reaction(self.REACTION_OUTDATED, user)
                            logger.info(f'Removed {reaction.emoji} from user {user} on embed {embed.title}')

        logger.info('Marked outdated embeds.')

    # noinspection PyUnusedLocal
    @command(hidden=True)
    @del_invoc
    async def mark_embeds(self, ctx: Context):
        """ Put the ❌ emoji over outdated events immediately. """
        await self.mark_loop.coro()

    # noinspection PyCallingNonCallable
    @start_when_needed()
    @tasks.loop(minutes=10)
    async def update_upcoming_loop(self):
        """ List the upcoming embeds in the `general` channel topic. """
        # Create the topic string outta the embeds
        topic = '**Upcoming:** '
        async for embed in self.embeds:
            if not utils.EmbedUtils.is_outdated(embed):
                topic += embed.title + ', '
        topic = topic[:-2]

        # Get the channel
        channel: TextChannel = discord.utils.get(self.bot.guild.text_channels, name='general')

        # Update the topic
        await channel.edit(reason=logger.name, topic=topic)

        logger.info('Edited topic based on the upcoming events.')

    # noinspection PyUnusedLocal
    @command(hidden=True)
    @del_invoc
    async def general_topic(self, ctx: Context):
        """ Put the upcoming events to the #general topic immediately. """
        await self.update_upcoming_loop.coro()

    # noinspection PyCallingNonCallable
    @start_when_needed()  # *args and **kwargs can be put here.
    @tasks.loop(minutes=10)
    async def sync_calendar_loop(self):
        # TODO Put the sync code here. See below.

        # Possible implementation
        # async for embed in cls.embeds:
        #       ... do your stuff ...

        logger.info('Synced embeds with google calendar. #TODO')  # TODO Remove TODO.

    # noinspection PyUnusedLocal
    @command(hidden=True)
    @del_invoc
    async def sync_calendar(self, ctx: Context):
        """ Sync the calendar immediately. """
        await self.sync_calendar_loop.coro()
        # No more things have to be done here.
        # This comment can be deleted.


def setup(bot: FreefClient):
    cog = EmbedManager(bot)
    bot.add_cog(cog)

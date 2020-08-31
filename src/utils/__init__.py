from __future__ import annotations

import asyncio
import datetime
import re
import time

import PIL.Image
import PIL.ImageOps
import dateparser
from discord import Color, Embed, Message, NotFound, Reaction, TextChannel, User
from discord.ext.commands import Context

import common
from .list_to_image import FontMap, ListToImageBuilder
from timeout_message import TimeoutMessage


async def silent_delete(msg: Message) -> bool:
    """
    Delete a message and ignore the NotFound exception.

    :param msg: The message to be deleted
    :return: True if the message was deleted by this function successfully. False if the message could not be deleted.
    """

    try:
        await msg.delete()
    except NotFound:
        return False
    return True


class UserInput:
    context: Context
    question_msg: Message

    def __init__(self, ctx):
        self.context = ctx

    async def ask(self, title: str, description: str = '', regex: str = '') -> [str, None]:
        """
        Ask the user for an input. This function will send an embed informing the user about
        the questioned value criteria and a button to cancel this input.

        :param title: The title of the questioning embed.
        :param description: The description of the questioning embed.
        :param regex: The regex that will be used during the validating of the input. This regex will
            also be shown in the embed description.
        :return: The content of the user sent message or None if cancelled.
        """
        # Create the embed
        embed = Embed(title=f'Enter the **{title}** ...',
                      description=description + f'\n\n*Regex:* `{regex}`' * bool(regex))

        # send the message
        self.question_msg = await self.context.send(embed=embed)

        # Add the cancel reaction
        await self.question_msg.add_reaction('❌')

        def msg_check(msg_):
            # Terminate the waiting if the question was cancelled
            res = True

            # Ignore non-context channels and users
            if msg_.channel != self.context.channel or msg_.author != self.context.author:
                return False

            # Check regex
            if not re.match(regex, msg_.clean_content):
                res = False

            # Accept/dismiss reply
            self.context.bot.loop.create_task(msg_.add_reaction('✅' if res else '❌'))

            if not res:
                self.context.bot.loop.create_task(self._delayed_del(msg_))

            return res

        def react_check(reaction: Reaction, user: User):
            return reaction.emoji == '❌' and user == self.context.author and reaction.message.id == self.question_msg.id

        done, pending = await asyncio.wait([
            self.context.bot.wait_for('message', check=msg_check),
            self.context.bot.wait_for('reaction_add', check=react_check)], return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()

        # Delete the question message
        await silent_delete(self.question_msg)

        stuff: [Reaction, Message] = done.pop().result()

        if isinstance(stuff, Message):
            await self._delayed_del(stuff)
            return stuff.content

        return None

    @staticmethod
    async def _delayed_del(msg: Message):
        """ Delete a message after one second. """
        time.sleep(1)
        await silent_delete(msg)


class Datetime:
    @staticmethod
    def shifted_weekday(timedelta: datetime.timedelta = datetime.timedelta(hours=12)) -> int:
        """
        Get the current datetime + the timedelta weekday.

        :param timedelta: The time that will be added to the current datetime.
        :return: Weekday index.
        """

        return (datetime.datetime.now() + timedelta).weekday()


class EmbedUtils:
    @staticmethod
    async def channel_summary(channel: TextChannel, **kw) -> Embed:
        """
        Make a single embed with less information out of all the embeds in a channel.

        :param channel: The channel to take the embeds from.
        :param kw: The data the embed will be built from.
            The title, description may and the color will be overridden.
        :return: Embed summary of a channel.
        """

        # Get the embeds
        _embeds = [msg.embeds[0] async for msg in channel.history() if msg.embeds]

        # Sort by date
        _embeds.sort(key=lambda x: (dateparser.parse(x.description or '') or common.MAX_DATETIME).date(),
                     reverse=True)

        # Build the embed
        _embed = Embed.from_dict(kw)
        for embed in _embeds:
            _embed.add_field(name=f'**{embed.title}**, {embed.description}',
                             value=', '.join(f.name for f in embed.fields) or '...',
                             inline=False)
        if _embed.fields:
            _embed.color = Color.red()
            _embed.description = _embed.description or ''
            _embed.description = f'More information can be found in {channel.mention}.'

        else:
            _embed.title = 'Nothing to see here!'
            _embed.description = r'\(￣︶￣*\))'
            _embed.color = Color.green()

        return _embed


class MessageUtils:
    @staticmethod
    def age(msg: Message):
        """ Return a timedelta saying how old the message is. """
        return datetime.datetime.now() - msg.created_at


class ImageUtils:
    @staticmethod
    def invert_colors(img: PIL.Image.Image) -> PIL.Image.Image:
        """ Return a new image with the color replaced. Supports RGBA images. """
        if img.mode == 'RGB':
            return PIL.ImageOps.invert(img)

        r, g, b, a = img.split()
        rgb_image = PIL.Image.merge('RGB', (r, g, b))

        inverted_image = PIL.ImageOps.invert(rgb_image)

        r2, g2, b2 = inverted_image.split()

        return PIL.Image.merge('RGBA', (r2, g2, b2, a))

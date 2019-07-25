import calendar
import datetime
from typing import List

from discord import Embed, TextChannel, Color, Message

from .list_to_image import FontMap, ListToImageBuilder


class String:
    @staticmethod
    def contains_scattered(string: str, substring: str) -> bool:
        """
        Check if  string contains a substring even if scattered.

        :param string: The string to search in.
        :param substring: The scattered substring.
        :return: Whether the full scattered substring is contained
            in the string.
        """

        return len([ch for ch in substring if ch in string]) == len(substring)


class Datetime:
    # noinspection PyTypeChecker
    @staticmethod
    def from_string(string: str, fallback: datetime.date = None, month_abbrs: List[str] = None) -> datetime.date:
        """
        Get a date object from a localized string. The format of the string
        should be `%d. %b`.

        :param string: The considered string.
        :param fallback: The date that will be returned in case the conversion
            fails. Default is a date with datetime.MAXYEAR
        :param month_abbrs: A list of the month names. If None, the
            calendar.month_abbr will be used.
        :return: An instance of the inbuilt datetime.date object.
        """

        fallback = fallback or datetime.date(datetime.MAXYEAR, 1, 1)
        month_abbrs = month_abbrs or calendar.month_abbr

        string = string.lower()
        month_abbrs = filter(bool, month_abbrs)

        # Replace month name with their abbr
        month_substring = string.split()[-1]
        for abbr in reversed(list(month_abbrs)):
            if String.contains_scattered(month_substring, abbr):
                string = string.replace(month_substring, abbr)
                break

        try:
            return datetime.datetime.strptime(string, '%d. %b').date()
        except ValueError:
            return fallback

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
    def is_outdated(embed: Embed) -> bool:
        """
        Whether an embed is outdated. Only the embed description is considered
        :param embed: The embed with a date in it's description.
        :return: Whether the embed is outdated.
        """

        now = datetime.datetime.now()

        date = Datetime.from_string(embed.description)  # Convert
        date = date.replace(year=now.year)  # Set the current year

        return date < now.date()

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
        _embeds.sort(key=lambda x: Datetime.from_string(x.description),
                     reverse=True)

        # Build the embed
        _embed = Embed.from_dict(kw)
        for embed in _embeds:
            _embed.add_field(name=f'**{embed.title}**, {embed.description}',
                             value=', '.join(f.name for f in embed.fields) or '...',
                             inline=False)
        if not _embed.fields:
            _embed.title = 'Nothing to see here!'
            _embed.description = r'\(￣︶￣*\))'
            _embed.color = Color.green()
        else:
            _embed.color = Color.red()

        return _embed


class MessageUtils:
    @staticmethod
    def age(msg: Message):
        """ Return a timedelta saying how old the message is. """
        return datetime.datetime.now() - msg.created_at

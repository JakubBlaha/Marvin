import asyncio
import re

from discord.ext.commands import Bot
from discord import Message, TextChannel

from config import Config
from utils.embed_to_text import embed_to_text
from command_modules.embed import is_embed_up_to_date

DEFAULT_INTERVAL = 3600


class EventsNotifier(Bot):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.loop.create_task(self._task_loop())

    async def _task_loop(self):
        await self.wait_until_ready()

        _interval = Config.get('upcoming_events_notif_interval',
                               DEFAULT_INTERVAL)

        while True:
            await self._task()
            await asyncio.sleep(_interval)

    async def _task(self):
        # Get the notification channel
        _notif_channel_id = int(
            Config.get('upcoming_events_notif_channel_id', None))

        # Return if there wa an error getting the channel
        if not _notif_channel_id:
            return

        # Generate the string
        _str = '**Upcoming:** ' + ', '.join(
            [f'*{t}*' async for t in self._get_event_message_titles()])

        await self.get_channel(_notif_channel_id).edit(topic=_str)

    async def _get_event_message_titles(self) -> Message:
        # Get the channels to check
        _channels = [
            self.get_channel(int(id_))
            for id_ in Config.get('upcoming_events_notif_checked_channels', [])
        ]

        # Go throught the channel history
        for _ch in _channels:
            async for _msg in _ch.history():
                # Skip if embed is not found
                if not _msg.embeds:
                    continue

                # Yield the title, if the embed is valid
                if is_embed_up_to_date(_msg.embeds[0]):
                    yield _msg.embeds[0].title

import asyncio

import discord.utils
from discord.ext.commands import Bot

import utils
from logger import Logger
from remote_config import RemoteConfig


class EventsNotifier(RemoteConfig, Bot):
    async def on_ready(self):
        await super().on_ready()

        self.loop.create_task(self._task_loop())

    async def _task_loop(self):
        await self.wait_until_ready()

        while True:
            await self._task()
            await asyncio.sleep(3600)

    async def _task(self):
        # Generate the string
        _str = '**Upcoming:** ' + ', '.join(
            [f'*{t}*' async for t in self._get_event_message_titles()])

        # Get the channel
        _channel = discord.utils.get(self.guild.channels, name='general')
        if not _channel:
            Logger.warning(
                'EventNotifier: Could not find a channel to update!')

        await _channel.edit(topic=_str)

    async def _get_event_message_titles(self):
        # Go through the channel history
        for _ch in filter(lambda x: '🔔' in (getattr(x, 'topic', None) or ''),
                          self.guild.channels):
            async for _msg in _ch.history():
                # Skip if embed is not found
                if not _msg.embeds:
                    continue

                # Yield the title, if the embed is valid
                if utils.EmbedUtils.is_outdated(_msg.embeds[0]):
                    yield _msg.embeds[0].title

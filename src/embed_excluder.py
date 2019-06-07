from discord import Client, TextChannel
import asyncio

from logger import Logger
from remote_config import RemoteConfig
from command_modules.embed import is_embed_up_to_date


class EmbedExcluder(RemoteConfig, Client):
    async def on_ready(self):
        await super().on_ready()
        await self.exclude_embeds()

    async def loop(self):
        while True:
            await self.exclude_embeds()
            await asyncio.sleep(3600)

    async def exclude_embeds(self):
        Logger.info(f'{self}: Running embed exclusion..')
        for channel in filter(
                lambda x: '🔔' in (getattr(x, 'topic', None) or ''),
                self.guild.channels):
            async for msg in channel.history():
                # Skip if no embeds
                if not msg.embeds:
                    continue

                # Add the reaction
                if not is_embed_up_to_date(msg.embeds[0]):
                    await msg.add_reaction('❌')
                else:
                    await msg.remove_reaction('❌', self.user)

    def __str__(self):
        return 'EmbedExcluder'

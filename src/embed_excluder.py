from discord import Client, TextChannel
import asyncio

from logger import Logger
from config import Config
from command_modules.embed import is_embed_up_to_date


class EmbedExcluder(Client):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.loop.create_task(self.exclude_embeds())

    async def exclude_embeds(self):
        await self.wait_until_ready()
        channels = Config.get('embed_exclusion_channel_ids', [])
        if not channels:  # nothing to check
            return

        interval = Config.get('embed_exclusion_check_interval', 600)
        tag_channel = self.get_channel(
            Config.get('embed_exclusion_alert_channel_id', None))
        tag_role = self.get_guild(Config.guild_id).get_role(
            Config.get('embed_exclusion_alert_role_id', None))

        while True:
            Logger.info(f'{self}: Running embed exclusion..')

            for channel in self.get_all_channels():
                if channel.id not in channels:
                    continue

                Logger.info(f'{self}: Checking channel `{channel.name}`')

                async for msg in channel.history():
                    if not msg.embeds:
                        continue

                    e = msg.embeds[0]
                    reactions = [r.emoji for r in msg.reactions]

                    if not ('❌' in reactions or is_embed_up_to_date(e)):
                        await msg.add_reaction('❌')
                        if tag_channel:
                            await tag_channel.send(
                                f'Outdated embed in channel {channel.mention} *{e.title}... {e.description}*\n{tag_role.mention if tag_role else ""}'
                            )
                        Logger.info(
                            f'{self}: Excluded `{e.title}... {e.description}...`'
                        )

            await asyncio.sleep(interval)

    def __str__(self):
        return 'EmbedExcluder'

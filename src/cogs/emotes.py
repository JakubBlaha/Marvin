from typing import Dict

import logging

import requests_async as requests
from bs4 import BeautifulSoup
from discord import Embed, Message
from discord.ext import tasks
from discord.ext.commands import Cog, Context, group

from client import Marvin
from command_output import CommandOutput
from decorators import del_invoc
from timeout_message import TimeoutMessage
from utils import ListToImageBuilder

logger = logging.getLogger('EmoteCog')


async def _get_emotes_twitchemotes() -> Dict[str, str]:
    url = 'https://twitchemotes.com/'
    emotes = {}

    response = await requests.get(url)

    soup = BeautifulSoup(response.text, 'html.parser')

    for a in soup.find_all('img', {'class': 'emote expandable-emote'}):
        name, url = a.attrs['data-regex'], a.attrs['src'].replace('1.0', '3.0')
        emotes[name] = url

    return emotes


class EmoteCog(Cog, name='Emotes'):
    """ Watch emote names in messages of guild members and send emotes according to them. """

    bot: Marvin

    def __init__(self, bot: Marvin):
        self.bot = bot
        self.emotes: Dict[str, str] = {}

        self.bot.add_listener(self.on_message)

        self.reload_emotes_loop.start()

    # noinspection PyCallingNonCallable
    @tasks.loop(minutes=60)
    async def reload_emotes_loop(self, force=False):
        logger.info('Loading emotes ...')

        # Emotes from remote servers
        functions = [
            _get_emotes_twitchemotes
        ]

        for function in functions:
            try:
                emotes = await function()
            except Exception:
                logger.error(f'Failed to load emotes using function {function}.')
            else:
                self.emotes.update(emotes)

        # Custom guild emotes
        await self.bot.wait_until_ready()

        for emoji in self.bot.guild.emojis:
            self.emotes[emoji.name] = emoji.url

        logger.info(f'Loaded {len(self.emotes)} emotes.')

    async def on_message(self, msg: Message):
        if any([not msg.content, msg.author == self.bot.user]):
            return

        # Recognized emotes
        recognized = []
        content = msg.content.lower()

        # Ignore punctuation
        content = content.translate(str.maketrans('', '', '.,!?'))

        words = content.split()

        # Send emotes
        for emote, url in self.emotes.items():
            emote = emote.lower()
            if emote in recognized:
                continue
            if emote in words:
                recognized.append(emote)
                _e = Embed()
                _e.set_author(name=msg.author.display_name, icon_url=msg.author.avatar_url)
                _e.set_image(url=url)
                await msg.channel.send(embed=_e)

        # Delete message if all it was were emotes
        for emote in recognized:
            content = content.replace(emote, '')
        if not content.strip():
            await msg.delete()

    @group()
    @del_invoc
    async def emote(self, ctx: Context):
        """ List all the custom emotes along with their images. """
        # Return if subcommand was invoked
        if ctx.invoked_subcommand:
            return

        string = ''.join(map(str, ctx.guild.emojis))
        string += '\n\n... these custom, global twitch emotes and BTTV emotes.'
        string += '\n\n**Try it:** type `OhMyDog` into the chat or `!emote list` to list all available emotes.'

        await CommandOutput(ctx, description=string).send()

    @emote.command(hidden=True)
    @del_invoc
    async def reload(self, ctx: Context):
        await self.reload_emotes_loop.coro(self, True)
        await TimeoutMessage(ctx).send('✅ Emotes have been successfully reloaded.')

    @emote.command()
    async def list(self, ctx: Context):
        """ List all the available emote names. Without images this time. We cannot spam the network too much. """
        emotes = sorted(list(self.emotes.keys()))
        tabular_data = [emotes[i: i + 3] for i in range(0, len(emotes), 3)]

        builder = ListToImageBuilder(tabular_data)

        await CommandOutput(ctx, invoc=False, title='List of all available emotes:').send(register=False)

        for img in builder.generate(convert_to_file=True):
            await ctx.send(file=img)

        # We only send the invocation message here
        await CommandOutput(ctx, description=f'Listed **{len(emotes)}** emotes.', author=False).send(
            register=False)


def setup(bot: Marvin):
    bot.add_cog(EmoteCog(bot))

import json
import logging
from urllib.request import urlopen

from bs4 import BeautifulSoup
from discord import Embed, Message
from discord.ext import tasks
from discord.ext.commands import Cog, Context, group

from cache import Cache
from client import FreefClient
from command_output import CommandOutput
from decorators import del_invoc
from timeout_message import TimeoutMessage
from utils import ListToImageBuilder

logger = logging.getLogger('EmoteCog')


class EmoteCog(Cog, name='Emotes'):
    """ Watch emote names in messages of guild members and send emotes according to them. """

    bot: FreefClient
    emotes: dict

    CACHE_KEY = 'emotes'
    CACHE_SECONDS = 600

    def __init__(self, bot: FreefClient):
        self.bot = bot
        self.emotes = {}

        self.bot.add_listener(self.on_message)

        self.reload_emotes_loop.start()

    # noinspection PyCallingNonCallable
    @tasks.loop(seconds=CACHE_SECONDS)
    async def reload_emotes_loop(self, force=False):
        # TODO use walrus operator in 3.8
        cached = Cache.load(self.CACHE_KEY, self.CACHE_SECONDS)
        if not force and cached:
            self.emotes = cached
            logger.info('Retrieved cached emotes.')
            return

        logger.info('Reloading emotes ...')

        self.emotes.clear()

        # twitchemotes
        response = urlopen('https://twitchemotes.com/')
        soup = BeautifulSoup(response.read(), 'html.parser')
        for a in soup.find_all('img', {'class': 'emote expandable-emote'}):
            name, url = a.attrs['data-regex'], a.attrs['src']
            url = url.replace('1.0', '3.0')  # get the largest possible size
            self.emotes[name] = url

        # BTTV
        response = urlopen('https://api.betterttv.net/1/emotes')
        for emote in json.loads(response.read())['emotes']:
            name, url = emote['regex'], 'https:' + emote['url']
            url = url.replace('1x', '3x')  # get the largest possible size
            self.emotes[name] = url

        # guild custom emotes
        await self.bot.wait_until_ready()

        for emoji in self.bot.guild.emojis:
            # noinspection PyProtectedMember
            self.emotes[emoji.name] = emoji.url._url

        logger.info('Done')

        # We can still use the cached value if new data could not be retrieved
        cached = Cache.load(self.CACHE_KEY, 0)
        if self.emotes:
            # Cache
            Cache.cache(self.CACHE_KEY, self.emotes)
        elif cached:  # TODO change to walrus in 3.8
            self.emotes = cached

    async def on_message(self, msg: Message):
        if any([not msg.content, msg.author == self.bot.user]):
            return

        # Recognized emotes
        recognized = []
        content = msg.content.lower()

        # Ignore punctuation
        content = content.translate(str.maketrans('', '', '.,!?'))

        # Send emotes
        for emote, url in self.emotes.items():
            emote = emote.lower()
            if emote in recognized:
                continue
            if emote in content.split():
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
        """ List all the custom emotes with images. """
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
        await CommandOutput(ctx, description=f'Listed **{len(emotes)}** emotes.', author=False).send(register=False)


def setup(bot: FreefClient):
    bot.add_cog(EmoteCog(bot))

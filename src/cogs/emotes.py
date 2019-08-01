import json
import logging
from urllib.request import urlopen

from bs4 import BeautifulSoup
from discord import Embed, Message
from discord.ext import tasks
from discord.ext.commands import Cog, Context, command

from cache import Cache
from client import FreefClient
from decorators import del_invoc
from timeout_message import TimeoutMessage

logger = logging.getLogger('EmoteCog')


class EmoteCog(Cog):
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
    async def reload_emotes_loop(self):
        # TODO use walrus operator in 3.8
        cached = Cache.load(self.CACHE_KEY, self.CACHE_SECONDS)
        if cached:
            self.emotes = cached
            logger.info('Retrieved cached emotes ...')
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

        # Cache
        Cache.cache(self.CACHE_KEY, self.emotes)

    @command(hidden=True)
    @del_invoc
    async def reload_emotes(self, ctx: Context):
        await self.reload_emotes_loop.coro()
        await TimeoutMessage(ctx).send('✅ Emotes have been successfully reloaded.')

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


def setup(bot: FreefClient):
    bot.add_cog(EmoteCog(bot))

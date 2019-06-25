import json
import os
from urllib.request import urlopen

from bs4 import BeautifulSoup
from discord import Client, Embed, Guild, Message

from logger import Logger

TWITCH_API_URL = 'https://twitchemotes.com/'
BTTV_API_URL = 'https://api.betterttv.net/1/emotes'


class GlobalEmojiScraper:
    emotes = {}

    def reload_twitch_emotes(self):
        ''' Reload global Twitch emotes. '''
        # Open url
        Logger.info(self, f'Loading {TWITCH_API_URL} ...')
        _r = urlopen(TWITCH_API_URL)

        # Check if ok
        if _r.getcode() != 200:
            Logger.error(self, f'Response code: {_r.getcode()}')
            return False

        Logger.info(self, 'Response OK')

        # Read document
        Logger.info(self, 'Reading content ...')
        _soup = BeautifulSoup(_r.read(), 'html.parser')

        # Update emotes
        Logger.info(self, 'Finding emotes ...')
        for a in _soup.find_all('img', {'class': 'emote expandable-emote'}):
            self.emotes[
                a.attrs['data-regex'].lower()] = a.attrs['src'].replace(
                    '1.0', '3.0')

        Logger.info(self, 'Ok')

    def reload_bttv_emotes(self):
        ''' Reload BTTV emotes. '''
        # Open url
        Logger.info(self, f'Loading {BTTV_API_URL} ...')
        _r = urlopen(BTTV_API_URL)

        # Check ok
        if _r.getcode() != 200:
            Logger.error(self, f'Response code: {_r.getcode()}')
            return False

        Logger.info(self, 'Response OK')

        # Update emotes
        for emote in json.loads(_r.read())['emotes']:
            self.emotes[emote['regex'].lower(
            )] = 'https:' + emote['url'].replace('1x', '3x')

        Logger.info(self, 'Ok')

    def reload_guild_emotes(self, guild: Guild):
        ''' Reload guild emojis. '''
        Logger.info(self, 'Reloading guild emojis ...')
        for emoji in guild.emojis:
            self.emotes[emoji.name.lower()] = emoji.url

        Logger.info(self, 'Ok')

    def __str__(self) -> str:
        return self.__class__.__name__


class TwitchClient(Client):
    '''
    A subclass of discord.Client watching for messages with emote names to be
    sent and replacing them with the actual emote images using embeds.
    '''

    _scraper: GlobalEmojiScraper

    async def on_ready(self):
        await super().on_ready()

        self._scraper = GlobalEmojiScraper()
        self._scraper.reload_bttv_emotes()
        self._scraper.reload_twitch_emotes()
        self._scraper.reload_guild_emotes(self.guild)

    async def on_message(self, msg: Message):
        await super().on_message(msg)

        # Skip own messages
        if msg.author == self.user:
            return

        # Recognized emotes
        _recognized = []
        _content = msg.content.lower()

        # Send emotes
        for emote in self._scraper.emotes:
            if emote in _content.translate(str.maketrans('', '',
                                                         '.,!?')).split():
                _recognized.append(emote)
                _e = Embed()
                _e.set_author(name=msg.author.display_name,
                              icon_url=msg.author.avatar_url)
                _e.set_image(url=self._scraper.emotes[emote])
                await msg.channel.send(embed=_e)

        # Delete message if all it was were emojis
        for emote in _recognized:
            _content = _content.replace(emote, '')

        if not _content.strip():
            await msg.delete()


if __name__ == "__main__":
    _ = GlobalEmojiScraper()
    _.reload_twitch_emotes()
    _.reload_bttv_emotes()
    print(_.emotes)

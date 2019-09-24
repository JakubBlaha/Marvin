import datetime
import logging
import re
from typing import Dict

from discord import Message, User
from discord.ext.commands import Cog, Context, group
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import PhantomJS, Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from client import Marvin
from config import Config
from decorators import list_subcommands
from remote_config import RemoteConfig

logger = logging.getLogger('Cleverbot')


class Memory:
    """ Stores the user context and decides whether the bot should respond based on the last message. """
    _user_ids: Dict[int, Context] = {}

    def should_respond(self, user: User, ctx: Context):
        """ Whether the bot should respond to the message without mentioning. Return False if the bot has not been
        tagged yet, else consider the max configured time in the remote config. Also takes into an account the
        present channel. """

        try:
            msg: Message = self._user_ids[user.id].message
        except KeyError:
            return False

        if msg.channel != ctx.channel:
            return False

        created_at = msg.created_at
        now = datetime.datetime.utcnow()
        max_diff = datetime.timedelta(seconds=RemoteConfig.chatbot_memory_seconds)

        return now - created_at < max_diff

    def update(self, user: User, context: Context):
        """ Update the user's context. Use to reset the timer. """
        self._user_ids[user.id] = context

    def remove(self, user: User):
        """ Forget the user last context. """
        self._user_ids.pop(user.id)

    def is_stored(self, user: User):
        """ Whether the context of the user is stored or not. """
        return user.id in self._user_ids


class Cleverbot(Cog, name='Chatting'):
    bot: Marvin
    memory: Memory
    driver: PhantomJS = None
    context: Context = None
    _input_box: WebElement

    def __init__(self, bot: Marvin):
        self.bot = bot
        self.memory = Memory()

    def _setup_driver(self):
        # Initialize the browser
        logger.debug('Initializing browser ...')
        opts = ChromeOptions()
        if Config.headless_chrome:
            opts.add_argument('headless')
            opts.add_argument('disable-gpu')

        self.driver = Chrome(options=opts)

        # Get the url
        logger.debug('Loading cleverbot ...')
        self.driver.get('https://www.cleverbot.com')

        # Locate the input box
        logger.debug('Locating elements..')
        self._input_box = self.driver.find_element_by_xpath(
            '//*[@id="avatarform"]/input[1]')

    async def communicate(self, string: str):
        # Warn if not initialized
        if not self.driver:
            logger.error('Driver not initialized!')
            return 'I cannot get up. Help me! Tell the developers please. :frowning:'

        # Type the input in
        self._input_box.send_keys(string + '\n')

        # Wait for reply by looking for the yellow snip icon
        try:
            WebDriverWait(self.driver, 10).until(
                expected_conditions.visibility_of_element_located((By.ID, 'snipTextIcon')))
        except TimeoutException:
            return ('I am sorry, I am not feeling very well today. I have'
                    ' eaten a *TimeoutException*.. :frowning:*')

        # Return the reply
        return self.driver.find_element_by_xpath('//*[@id="line1"]/span[1]').text

    @Cog.listener()
    async def on_message(self, msg: Message):
        # Set the context for usage in initialization
        self.context = await self.bot.get_context(msg)

        # Skip if it's a command
        if msg.content.startswith(self.bot.command_prefix):
            return

        # Skip if not mentioned or the bot does not remember chatting with the user
        if self.bot.user not in msg.mentions and not self.memory.should_respond(msg.author, self.context):
            return

        self.memory.update(msg.author, self.context)

        # Clean content up, remove html since that causes errors
        content = msg.clean_content
        content = content.replace(f'@{self.context.me.display_name}', '')
        content = content.encode('ascii', 'ignore').decode('ascii')
        content = re.sub('<.*?>', '', content)

        # Log
        logger.debug(f'Received message input: *{content}*')

        # Init driver
        if not self.driver:
            _msg = await self.context.send('I am waking up. Please wait a little ... 🥱')
            await msg.channel.trigger_typing()
            self._setup_driver()
            await _msg.delete()

        await msg.channel.trigger_typing()

        # Get the reply
        reply = await self.communicate(content)

        # Log
        logger.debug(f'Received reply: *{reply}*')

        # Send the reply
        await msg.channel.send(reply)

    @group(hidden=True)
    @list_subcommands
    async def shut(self, ctx: Context):
        pass

    @shut.command()
    async def up(self, ctx: Context):
        """ Make the bot not respond to your messages until you tag him again. """
        if not self.driver:
            await ctx.send("We weren't even talking. Were we?")
            return

        if not self.memory.is_stored(ctx.author):
            await ctx.send("We weren't even talking!")
            return

        await ctx.trigger_typing()
        await ctx.send(await self.communicate('shut up') + ' I am quiet now. 😢')
        self.memory.remove(ctx.author)


def setup(bot: Marvin):
    bot.add_cog(Cleverbot(bot))

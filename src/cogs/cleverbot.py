import logging
import re
import time
from typing import Dict, Optional

from discord import Message
from discord.ext.commands import Cog, Context, group
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from client import Marvin
from decorators import list_subcommands
from remote_config import RemoteConfig

logger = logging.getLogger('Cleverbot')


class Memory:
    """ Will remember the people who ere chatting with cleverbot. """
    _timestamps: Dict[int, float] = {}  # id: timestamp

    def remembers(self, user_id: int) -> bool:
        """ Whether the bot should respond to a message he is not tagged in. The new timestamp will be registered. """
        return user_id in self._timestamps and time.time() - self._timestamps[
            user_id] < RemoteConfig.chatbot_memory_seconds

    def reset(self, user_id: int):
        """ Put or reset the user data in the memory. """
        self._timestamps[user_id] = time.time()

    def remove(self, user_id: int) -> Optional[float]:
        """ Remove the user from the memory. Return his last timestamp. """
        return self._timestamps.pop(user_id, None)


class Cleverbot(Cog, name='Chatting'):
    bot: Marvin
    memory: Memory
    driver: Chrome = None
    context: Context = None
    _input_box: WebElement

    def __init__(self, bot: Marvin):
        self.bot = bot
        self.memory = Memory()

    def _setup_driver(self):
        # Initialize options
        logger.debug('Initializing driver options ...')
        options = ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--log-level=3')  # fatal

        # Initialize the browser
        logger.debug('Initializing browser ...')
        self.driver = Chrome(options=options)

        # Get the url
        logger.debug('Loading cleverbot ...')
        self.driver.get('https://www.cleverbot.com')

        # Locate the input box
        logger.debug('Locating elements..')
        self._input_box = self.driver.find_element_by_xpath(
            '//*[@id="avatarform"]/input[1]')

    async def communicate(self, string: str):
        # Initialize if needed
        if not self.driver:
            _msg = await self.context.send('I am waking up. Please wait a little ... 🥱')
            await self.context.trigger_typing()
            self._setup_driver()
            await _msg.delete()

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
        if self.bot.user not in msg.mentions and not self.memory.remembers(msg.author.id):
            return

        self.memory.reset(msg.author.id)

        # Clean content up, remove html since that causes errors
        # content = msg.clean_content
        content = msg.clean_content
        content = content.replace(f'@{self.context.me.display_name}', '')
        content = content.encode('ascii', 'ignore').decode('ascii')
        content = re.sub('<.*?>', '', content)

        # Log
        logger.debug(f'Received message input: *{content}*')

        # Trigger typing
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
        if not self.memory.remove(ctx.author.id):
            await ctx.send("We weren't even talking!")
            return

        await ctx.trigger_typing()
        await ctx.send(await self.communicate('shut up') + ' I am quiet now. 😢')


def setup(bot: Marvin):
    bot.add_cog(Cleverbot(bot))

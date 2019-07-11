import re

from discord import Client, Message

from cleverbot import Cleverbot
from logger import Logger


class CleverbotClient(Client):
    TAG = 'CleverbotClient'

    cb: Cleverbot = None

    async def _init_cb(self):
        Logger.info(self.TAG, 'Initializing ...')
        self.cb = await self.loop.run_in_executor(None, Cleverbot)

    async def on_message(self, msg: Message):
        await super().on_message(msg)

        # Skip if not mentioned
        if self.user not in msg.mentions:
            return

        # Check if initialized, initialize
        if not self.cb:
            _msg = await msg.channel.send('I am waking up. Please wait a little ... 🥱')
            await msg.channel.trigger_typing()
            await self._init_cb()
            await _msg.delete()

        # Clean content up, remove html since that causes errors
        # content = msg.clean_content
        content = msg.content
        content = content.replace('@freefbot', '')
        content = content.encode('ascii', 'ignore').decode('ascii')
        content = re.sub('<.*?>', '', content)

        # Log
        Logger.info(self.TAG, f'Received message input: *{content}*')

        # Trigger typing
        await msg.channel.trigger_typing()

        # Get the reply
        reply = await self.cb.communicate(content)

        # Log
        Logger.info(self.TAG, f'Received reply: *{reply}*')

        # Send the reply
        await msg.channel.send(reply)

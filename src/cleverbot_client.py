from discord import Client, Message

from cleverbot import Cleverbot
from logger import Logger
from utils.clean_message_content import clean_message_content


class CleverbotClient(Client):
    TAG = 'CleverbotClient'
    cb: Cleverbot

    async def _init_cb(self):
        Logger.info(self.TAG, 'Cleverbot initialization requested. Running ...')
        self.cb = await self.loop.run_in_executor(None, Cleverbot)

    async def on_message(self, msg: Message):
        await super().on_message(msg)

        # Skip if not mentioned
        if not self.user in msg.mentions:
            return
        
        # Check if initialized, initialize
        if not hasattr(self, 'cb'):
            _msg = await msg.channel.send('I am waking up. Please wait a little ...')
            await msg.channel.trigger_typing()
            await self._init_cb()
            await _msg.delete()

        # Prepare the content
        _content = msg.clean_content
        _content = _content.replace('@freefbot', '')
        _content = _content.strip()
        _content = clean_message_content(_content)

        # Log
        Logger.info(self.TAG, f'Received message input: *{_content}*')

        # Trigger typing
        await msg.channel.trigger_typing()

        # Get the reply
        _reply = await self.cb.communicate(_content)

        # Log
        Logger.info(self.TAG, f'Received reply: *{_reply}*')

        # Send the reply
        await msg.channel.send(_reply)            

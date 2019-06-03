from discord import Client, Message

from cleverbot import Cleverbot
from logger import Logger
from utils.clean_message_content import clean_message_content


class CleverbotClient(Client):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.loop.create_task(self._init_cb())

    async def _init_cb(self):
        self.cb = await self.loop.run_in_executor(None, Cleverbot)

    async def on_message(self, msg: Message):
        await super().on_message(msg)

        if not self.user in msg.mentions:
            return

        if not hasattr(self, 'cb'):
            await msg.channel.send('I am not ready yet. Try in *10* seconds!')
            return

        # Prepare the content
        _content = msg.clean_content
        _content = _content.replace('@freefbot', '')
        _content = _content.strip()
        _content = clean_message_content(_content)

        # Log
        Logger.info(f'CleverbotClient: Received message input: *{_content}*')

        # Trigger typing
        await msg.channel.trigger_typing()

        # Get the reply
        _reply = await self.cb.communicate(_content)

        # Log
        Logger.info(f'CleverbotClient: Received reply: *{_reply}*')

        # Send the reply
        await msg.channel.send(_reply)
            

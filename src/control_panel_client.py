from asyncio import sleep

from discord import TextChannel, Message, Reaction, User, Embed
from discord.ext.commands import Bot
from discord.errors import NotFound

from config import Config, CONTROL_PANEL_CHANNEL_ID

EMOJI_COMMAND_MAP = {
    '📃': 'substits',
    '📑': 'table',
    '📚': 'subj',
    '🎒': 'bag',
    '✅': 'test',
    '🏠': 'ukol'
}


class ControlPanelClient(Bot):
    _channel: TextChannel
    _msg: Message = None

    async def on_ready(self):
        # Get the channel
        self._channel = self.get_channel(Config.get(CONTROL_PANEL_CHANNEL_ID))

        # Clear the channel
        await self._clear_channel()

        # Send message
        self._msg = await self._channel.send(
            embed=self._generate_embed(EMOJI_COMMAND_MAP))

        # Pin the message
        await self._msg.pin()

        # Delete the pin information message
        async for _msg in self._msg.channel.history():
            await _msg.delete()
            break

        # Add reactions
        await self._reset_reactions(self._msg)

    async def _reset_reactions(self, _msg: Message):
        await self._msg.clear_reactions()

        for emoji, func in EMOJI_COMMAND_MAP.items():
            await _msg.add_reaction(emoji)

    async def _clear_channel(self):
        ''' Clears the configured channel. '''
        await self._channel.delete_messages([msg async for msg in self._channel.history()])

    def _generate_embed(self, command_map: dict) -> Embed:
        ''' Return an embed based on the `command_map` argument. '''
        _embed = Embed(title='**Command panel**')
        for emoji, command_name in command_map.items():
            _embed.add_field(
                name=f'{emoji} {command_name}',
                value=self._get_command_short_description(command_name),
                inline=False)

        return _embed

    def _get_command_short_description(self, command_name: str) -> str:
        '''
        Return a short command description based on the `command_name`
        argument.
        '''
        return self.get_command(command_name).help.split('\n')[0]

    async def on_reaction_add(self, reaction: Reaction, user: User):
        # Execute corresponding commands on a reaction add

        # Skip own reactions
        if user == self.user:
            return

        # Do not check other messages
        if reaction.message.id != self._msg.id:
            return

        # Simulate the invocation message
        _msg = self._msg
        _msg.author = user

        # Simulate the context
        _context = await self.get_context(self._msg)

        # Get the command, invoke
        await self.get_command(EMOJI_COMMAND_MAP[reaction.emoji]
                               ).invoke(_context)

        # Reset reactions
        await self._reset_reactions(self._msg)

    async def on_message(self, msg: Message):
        # Remove any messages posted to the configured channel after a time
        # period

        await super().on_message(msg)

        # Skip if control panel message was not set yet, is not assigned yet
        if not self._msg:
            return

        # Skip messages in non-configured channels
        if msg.channel != self._channel:
            return

        # Add the alert emoji
        try:
            await msg.add_reaction('⚠')
        except NotFound:
            pass

        # Sleep
        await sleep(60)

        # Delete the message
        try:
            await msg.delete()
        except NotFound:
            pass

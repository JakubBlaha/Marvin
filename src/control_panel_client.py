import logging
from asyncio import sleep

from discord import TextChannel, Message, Embed, RawReactionActionEvent
from discord.errors import NotFound
from discord.ext.commands import Bot

from remote_config import RemoteConfig

EMOJI_COMMAND_MAP = {
    '📃': 'substits',
    '📑': 'table',
    '📚': 'subj',
    '🎒': 'bag',
    '✅': 'exam',
    '🏠': 'homework'
}

TAG = 'CommandPanel'

logger = logging.getLogger('CommandPanel')


class ControlPanelClient(RemoteConfig, Bot):
    _channel: TextChannel
    _msg: Message = None

    async def on_ready(self):
        await super().on_ready()

        # Get the channel
        self._channel = self.get_channel(self['control_panel_channel_id'])

        # Build the embed
        embed = self._generate_embed(EMOJI_COMMAND_MAP)

        # Adopt the embed, delete other messages
        async for msg in self._channel.history():
            if msg.embeds and msg.embeds[0].to_dict() == embed.to_dict():
                self._msg = await self._channel.fetch_message(msg.id)
                logger.info(f'Adopted message {msg.id}')
                break
            else:
                await msg.delete()
        else:
            # Send the message if no matching one was found
            logger.info('Could not find a message that could be adopted. Will send a new one ...')
            self._msg = await self._channel.send(embed=embed)

        # Add reactions
        logger.info('Adding reactions ...')
        await self.reset_reactions()

        logger.info('Initialization completed.')

    async def reset_reactions(self):
        # msg: Message = await self._channel.fetch_message(self._msg.id)

        # Clear not desired reactions
        for reaction in self._msg.reactions:
            async for user in reaction.users():
                if user != self.user or reaction.emoji not in EMOJI_COMMAND_MAP:
                    await self._msg.remove_reaction(reaction.emoji, user)

        # Add missing reactions
        for emoji in EMOJI_COMMAND_MAP:
            await self._msg.add_reaction(emoji)

    def _generate_embed(self, command_map: dict) -> Embed:
        """ Return an embed based on the `command_map` argument. """
        _embed = Embed(title='**Command panel**')
        for emoji, command_name in command_map.items():
            _embed.add_field(
                name=f'{emoji} {command_name}',
                value=self._get_command_short_description(command_name),
                inline=False)

        return _embed

    def _get_command_short_description(self, command_name: str) -> str:
        """
        Return a short command description based on the `command_name`
        argument.
        """
        return self.get_command(command_name).help.split('\n')[0].strip()

    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        emoji, user = payload.emoji.name, self.get_user(payload.user_id)

        # Skip own reactions
        if user.id == self.user.id:
            return

        # Skip other than the command panel message
        if payload.message_id != self._msg.id:
            return

        # Simulate the context
        _context = await self.get_context(self._msg)
        _context.author = user
        _context.is_private = True

        # Invoke the command
        try:
            await self.get_command(EMOJI_COMMAND_MAP[emoji]).invoke(_context)
        except KeyError:
            pass

        # Reset reactions
        await self._msg.remove_reaction(emoji, user)

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

import logging
from asyncio import sleep

from discord import Embed, Message, RawReactionActionEvent, TextChannel
from discord.errors import NotFound
from discord.ext.commands import Cog

from client import Marvin
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


class CommandPanel(Cog):
    bot: Marvin
    _channel: TextChannel
    _msg: Message = None

    def __init__(self, bot: Marvin):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        # Get the channel
        channel_id = self.bot.store.command_panel_channel_id
        self._channel = self.bot.get_channel(channel_id)

        # Build the embed
        embed = self._generate_embed(EMOJI_COMMAND_MAP)

        # Adopt the embed
        async for msg in self._channel.history():
            if msg.embeds and msg.embeds[0].to_dict() == embed.to_dict():
                self._msg = await self._channel.fetch_message(msg.id)
                logger.debug(f'Adopted message {msg.id}')
                break
        else:
            # Send the message if no matching one was found
            logger.debug('Could not find a message that could be adopted. Will send a new one ...')
            self._msg = await self._channel.send(embed=embed)

        # Add reactions
        await self.reset_reactions()

        logger.debug('Initialization completed.')

    async def reset_reactions(self):
        logger.debug('Resetting reactions ...')

        # Clear not desired reactions
        added_emojis = []
        for reaction in self._msg.reactions:
            if reaction.emoji not in EMOJI_COMMAND_MAP:
                async for user in reaction.users():
                    await self._msg.remove_reaction(reaction.emoji, user)
            else:
                added_emojis.append(reaction.emoji)

        # Add missing reactions
        for emoji in EMOJI_COMMAND_MAP:
            if emoji not in added_emojis:
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
        return self.bot.get_command(command_name).help.split('\n')[0].strip()

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        emoji, user = payload.emoji.name, self.bot.get_user(payload.user_id)

        # Skip own reactions
        if user.id == self.bot.user.id:
            return

        # Skip other than the command panel message
        if payload.message_id != self._msg.id:
            return

        # Simulate the context
        _context = await self.bot.get_context(self._msg)
        _context.author = user
        _context.is_private = True

        # Invoke the command
        try:
            await self.bot.get_command(EMOJI_COMMAND_MAP[emoji]).invoke(_context)
        except KeyError:
            pass

        # Reset reactions
        await self._msg.remove_reaction(emoji, user)

    @Cog.listener()
    async def on_message(self, msg: Message):
        # Remove any messages posted to the configured channel after a time
        # period

        # Skip if command panel message was not set yet, is not assigned yet
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
        await sleep(RemoteConfig.command_panel_timeout)

        # Delete the message
        try:
            await msg.delete()
        except NotFound:
            pass


def setup(bot: Marvin):
    bot.add_cog(CommandPanel(bot))

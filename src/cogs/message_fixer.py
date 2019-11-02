import asyncio

from discord import Message, Embed, NotFound
from discord.ext.commands import Cog

from client import Marvin

CHARS: dict = {
    '2': 'ě',
    '3': 'š',
    '4': 'č',
    '5': 'ř',
    '6': 'ž',
    '7': 'ý',
    '8': 'á',
    '9': 'í',
    '0': 'é',
    ';': 'ů',
    'y': 'z',
    'z': 'y'
}
NO_TRIGGER = {'y', 'z'}
REJECT_REACTION = '❌'
ACCEPT_REACTION = '✔'


def clean_iter(string: str) -> tuple:
    _ = False  # ignoring
    for i, ch in enumerate(string):
        if ch in '<>':
            _ = not _
            continue
        if _:
            continue
        yield (i, ch)


def fix_content(s: str) -> str:
    # Check if should be triggered
    for _, ch in clean_iter(s):
        if ch in set(CHARS) - NO_TRIGGER:
            break
    else:
        return s

    # Fix it
    for index, ch in clean_iter(s):
        s = s[:index] + CHARS.get(s[index], s[index]) + s[index + 1:]

    return s


class MessageFixer(Cog):
    bot: Marvin

    def __init__(self, bot: Marvin):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, msg: Message):
        # don't fix own messages
        if msg.author == self.bot.user:
            return

        # don't fix commands
        if msg.content.startswith(self.bot.command_prefix):
            return

        # don't fix messages directed to the bot
        if (await self.bot.get_context(msg)).me.display_name in msg.clean_content:
            return

        fixed_content = fix_content(msg.content)

        # nothing to fix
        if msg.content == fixed_content:
            return

        # Create an embed as a preview and add reactions to it
        embed = Embed(title=fixed_content)
        embed.set_author(name=msg.author.display_name)
        preview: Message = await msg.channel.send(embed=embed)
        await preview.add_reaction(REJECT_REACTION)
        await preview.add_reaction(ACCEPT_REACTION)

        def check(reaction_, user_):
            return reaction_.message.id == preview.id and reaction_.emoji in (
                REJECT_REACTION, ACCEPT_REACTION) and user_ == msg.author

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=5, check=check)
        except asyncio.TimeoutError:
            pass
        # Using pass-else statement because we want the message to get deleted on timeout
        else:
            # Remove the reactions from the preview and delete the original message
            if reaction.emoji == ACCEPT_REACTION:
                # Delete original message
                await msg.delete()

                # Remove reactions
                try:
                    await preview.clear_reactions()
                except NotFound:
                    pass
                return

        # Delete the message if not accepted
        try:
            await preview.delete()
        except NotFound:
            pass


def setup(bot: Marvin):
    bot.add_cog(MessageFixer(bot))


if __name__ == "__main__":
    print(fix_content('<Not this 1234> this yeah :)'))
    print(fix_content('<Not this 1234> this yeah :) 234'))

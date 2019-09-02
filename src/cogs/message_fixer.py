import asyncio

from discord import Message, Embed, NotFound
from discord.ext.commands import Cog

from client import FreefClient

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
    REACTION = '\u274c'
    bot: FreefClient

    def __init__(self, bot: FreefClient):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, msg: Message):
        # don't fix own messages
        if msg.author == self.bot.user:
            return

        # don't fix commands
        if msg.content.startswith(self.bot.command_prefix):
            return

        # don't fix messages directed to freefbot/cleverbot
        if '@freefbot' in msg.clean_content:
            return

        fixed_content = fix_content(msg.content)

        # nothing to fix
        if msg.content == fixed_content:
            return

        await msg.add_reaction(self.REACTION)

        def check(reaction, user):
            return reaction.message == msg and reaction.emoji == self.REACTION and user == msg.author

        try:
            await self.bot.wait_for('reaction_add', timeout=5, check=check)
        except asyncio.TimeoutError:
            try:
                await msg.remove_reaction(self.REACTION, self.bot.user)
            except NotFound:
                pass
        else:
            embed = Embed(description=fixed_content)
            embed.set_author(name=msg.author.display_name, icon_url=msg.author.avatar_url)
            await msg.channel.send(embed=embed)
            await msg.delete()


def setup(bot: FreefClient):
    bot.add_cog(MessageFixer(bot))


if __name__ == "__main__":
    print(fix_content('<Not this 1234> this yeah :)'))
    print(fix_content('<Not this 1234> this yeah :) 234'))

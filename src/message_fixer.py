from discord import Client, Message, Embed
from concurrent.futures._base import TimeoutError as TimeoutError_

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
    # Check if should be trigered
    for _, ch in clean_iter(s):
        if ch in set(CHARS) - NO_TRIGGER:
            break
    else:
        return s

    # Fix it
    for index, ch in clean_iter(s):
        s = s[:index] + CHARS.get(s[index], s[index]) + s[index + 1:]

    return s


class MessageFixer(Client):
    async def on_message(self, msg: Message):
        await super().on_message(msg)

        # don't fix own messages
        if msg.author == self.user:
            return

        # don't fix commands
        if msg.content.startswith(self.command_prefix):
            return

        # don't fix messages directed to freefbot/cleverbot
        if '@freefbot' in msg.clean_content:
            return

        fixed_content = fix_content(msg.content)
        # nothing to fix
        if msg.content == fixed_content:
            return

        REACTION = '\u274c'

        await msg.add_reaction(REACTION)

        def check(reaction, user):
            return (reaction.message == msg and reaction.emoji == REACTION
                    and user != self.user)

        try:
            reaction, user = await self.wait_for('reaction_add',
                                                 timeout=5,
                                                 check=check)
        except TimeoutError_:
            await msg.remove_reaction(REACTION, self.user)
        else:
            await msg.channel.send(
                embed=self._generate_embed(msg, fixed_content))
            await msg.delete()

    def _generate_embed(self, msg: Message, fixed_content: str):
        e = Embed(description=fixed_content)
        e.set_author(name=msg.author.display_name,
                     icon_url=msg.author.avatar_url)

        return e


if __name__ == "__main__":
    print(fix_content('<Not this 1234> this yeah :)'))
    print(fix_content('<Not this 1234> this yeah :) 234'))
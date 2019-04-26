from discord import Client, Message, Embed
from concurrent.futures._base import TimeoutError as TimeoutError_

from command_modules.cz import fix_content

class MessageFixer(Client):
    async def on_message(self, msg: Message):
        await super().on_message(msg)

        # don't fix own messages
        if msg.author == self.user:
            return

        # don't fix commands
        if msg.content.startswith(self.command_prefix):
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
            reaction, user = await self.wait_for(
                'reaction_add', timeout=5, check=check)
        except TimeoutError_:
            await msg.remove_reaction(REACTION, self.user)
        else:
            await msg.channel.send(embed=self._generate_embed(msg, fixed_content))
            await msg.delete()

    def _generate_embed(self, msg: Message, fixed_content: str):
        e = Embed(description=fixed_content)
        e.set_author(name=msg.author.display_name, icon_url=msg.author.avatar_url)

        return e
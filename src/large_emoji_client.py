from discord import Client, Message, Embed


class LargeEmojiCLient(Client):
    async def on_message(self, msg: Message):
        await super().on_message(msg)

        if msg.author == self:  # Do not reply to own messages
            return

        _content = msg.content.strip()

        if ' ' in _content:  # Skip multi-word messages
            return

        for emoji in msg.guild.emojis:
            if emoji.name.lower() == _content.lower():
                e = Embed()
                e.set_image(url=emoji.url)
                await msg.channel.send(embed=e)

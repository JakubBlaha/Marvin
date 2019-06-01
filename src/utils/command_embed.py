from discord.ext.commands import Context
from discord import Embed

async def send_command_embed(ctx: Context, content: str, send=True):
    ''' Send an embed with an author and the content. Return embed.'''
    e = Embed(title=content, description=f'`{ctx.message.content}`')
    e.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

    if send:
        await ctx.send(embed=e)
    await ctx.message.delete()

    return e
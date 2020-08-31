from discord.ext.commands import Context


async def send_error(ctx: Context, message: str):
    await ctx.send(f'❌ {message} ❌')
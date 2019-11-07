import inspect

from discord import Embed, NotFound, Forbidden
from discord.ext.commands import Context

from timeout_message import TimeoutMessage


def del_invoc(fn: callable):
    """
    Delete the commands invocation message after the command has been
    successfully executed.
    """

    async def wrapper(self, ctx: Context, *args, **kw):
        ret = await fn(self, ctx, *args, **kw)
        if not hasattr(ctx, 'is_private'):  # For command panel
            try:
                await ctx.message.delete()
            except NotFound:
                pass

        return ret

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    wrapper.__signature__ = inspect.signature(fn)

    return wrapper


def list_subcommands(fn: callable):
    """ List all the subcommands to the user if no subcommand was invoked. """

    async def wrapper(self, ctx: Context, *args, **kw):
        if not ctx.invoked_subcommand:
            _e = Embed(title='Available subcommands',
                       description=', '.join(
                           map(lambda x: f'`{x.name}`', ctx.command.commands)))
            await TimeoutMessage(ctx).send(embed=_e)
            try:
                await ctx.message.delete()
            except (NotFound, Forbidden):
                pass

        return await fn(self, ctx, *args, **kw)

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    wrapper.__signature__ = inspect.signature(fn)

    return wrapper

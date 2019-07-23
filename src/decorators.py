import inspect

from discord import Embed, NotFound, Role
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
            await TimeoutMessage(ctx, 5).send(embed=_e)

        return await fn(self, ctx, *args, **kw)

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    wrapper.__signature__ = inspect.signature(fn)

    return wrapper


def required_role(role_id: int):
    """ Execute only when the user meets the role requirements. Otherwise, inform him. """

    def decorator(fn: callable):
        async def wrapper(self, ctx: Context, *args, **kw):
            req_role: Role = ctx.guild.get_role(role_id)
            if req_role not in ctx.author.roles:
                embed = Embed(title='⚠ Invalid role!',
                              description=('You do not meet the role requirements. '
                                           f'This command is for **{req_role.name}** users only. '
                                           'Your command will not be executed.'))
                await TimeoutMessage(ctx, 5).send(embed=embed)
                return

            return await fn(self, ctx, *args, **kw)

        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        wrapper.__signature__ = inspect.signature(fn)

        return wrapper

    return decorator

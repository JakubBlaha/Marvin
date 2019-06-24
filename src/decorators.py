from typing import Callable


def del_invoc(fn: Callable):
    async def wrapper(self, ctx, *args, **kw):
        ret = await fn(self, ctx, *args, **kw)
        if not hasattr(ctx, 'is_private'):
            await ctx.message.delete()

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__

    return wrapper

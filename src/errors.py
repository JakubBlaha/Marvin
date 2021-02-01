import io
import traceback
from typing import Iterable

from discord import DiscordException, Embed
from discord.ext.commands import BadArgument, Bot, CommandNotFound, CommandOnCooldown, Context, MissingRequiredArgument, \
    MissingRole

from timeout_message import TimeoutMessage


# Handlers
class DiscordExceptionHandler:
    """
    A baseclass for the exception handlers.
    """

    # noinspection PyUnusedLocal
    @staticmethod
    async def handle(ctx: Context, exception: DiscordException):
        """
        Override to handle the exception. Return True if handler execution should be continued.
        Denote the exception type in the type hint.
        """

        # Prepare embed title, part of the description
        embed = Embed(title='⚠ Command error',
                      description=f'Sorry, there was an error executing the command `{ctx.message.clean_content}`.')

        # Finally send the embed
        await ctx.send(embed=embed)

        # Print to the stderr
        await Bot.on_command_error(ctx.bot, ctx, exception)


class MissingRoleHandler(DiscordExceptionHandler):
    @staticmethod
    async def handle(ctx: Context, exception: MissingRole):
        embed = Embed(
            title='Oops! Missing role.',
            description=f'Only members with the role **{exception.missing_role}** can run the command `{ctx.command}`'
        )

        await TimeoutMessage(ctx, 10).send(embed=embed)


class MissingRequiredArgumentHandler(DiscordExceptionHandler):
    @staticmethod
    async def handle(ctx: Context, exception: MissingRequiredArgument):
        await ctx.send('> Missing required arguments. See below. ⬇ ⬇')
        ctx.bot.help_command.context = ctx
        await ctx.bot.help_command.send_command_help(ctx.command)


class CommandNotFoundHandler(DiscordExceptionHandler):
    @staticmethod
    async def handle(ctx: Context, exception: CommandNotFound):
        await ctx.send(f"> Command `!{ctx.invoked_with}` not found. Type `!help` if you're lost.")


class BadArgumentHandler(DiscordExceptionHandler):
    @staticmethod
    async def handle(ctx: Context, exception: BadArgument):
        await ctx.send(f'> Bad argument given. See below. ⬇ ⬇')
        ctx.bot.help_command.context = ctx
        await ctx.bot.help_command.send_command_help(ctx.command)


class CommandOnCooldownHandler(DiscordExceptionHandler):
    @staticmethod
    async def handle(ctx: Context, exception: CommandOnCooldown):
        await ctx.message.delete()
        await TimeoutMessage(ctx, min(5, exception.retry_after)).send(
            f'> Command `{ctx.command}` is on cooldown! Try again in **{int(exception.retry_after)}** seconds.')


class ErrorHandler:
    # Put the error handlers in a order, the top ones will be processed first and have a chance
    # of stopping other handlers to being processed. Putting subclasses before baseclass
    # is recommended
    handlers: Iterable[DiscordExceptionHandler] = (
        CommandNotFoundHandler,
        MissingRoleHandler,
        CommandOnCooldownHandler,
        MissingRequiredArgumentHandler,
        BadArgumentHandler,
        DiscordExceptionHandler
    )

    async def handle(self, ctx: Context, exception: DiscordException):
        """
        Trigger all corresponding handlers for the given exception
        :return: Whether an error handler was triggered.
        """

        # We are iterating because some errors may be subclasses of other errors.
        triggered = False
        for handler in self.handlers:
            if isinstance(exception, handler.handle.__annotations__.get('exception')):
                triggered = True
                if not await handler.handle(ctx, exception):
                    break

        return triggered

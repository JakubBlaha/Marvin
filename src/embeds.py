from __future__ import annotations

import asyncio
import inspect
import re
from copy import deepcopy
from typing import Callable, Optional

from discord import Embed, Message
from discord.ext.commands import Bot, Cog
from discord.ext.commands import ColourConverter as ColorConverter
from discord.ext.commands import Context, group

import common
from decorators import del_invoc, list_subcommands
from reaction_callback_manager import ReactionCallbackManager, CancelCallback
from timeout_message import TimeoutMessage


class EmbedHistory:
    """
    Manages an embed history.
    """

    history: list
    _pos: int

    def __init__(self):
        self.history = []
        self._pos = 0

    def stack(self, embed: Embed):
        """
        Add the current state of the embed to the stack. Return the index of
        the added entry.
        """

        # Add to history
        self.history.append(deepcopy(embed.to_dict()))

        # Reset the position in te history
        self._pos = len(self.history) - 1

        return self._pos

    def grab_at(self, index: int) -> Embed:
        """
        Return the saved embed at the given index without changing the history.
        """

        return Embed.from_dict(deepcopy(self.history[index]))

    def undo(self) -> Embed:
        """ Move back in the history and return the embed. """
        self._pos -= 1
        return self.grab_at(self._pos)

    def redo(self) -> Embed:
        """ Move forward in the history and return the embed. """
        self._pos += 1
        return self.grab_at(self._pos)

    @property
    def can_undo(self) -> bool:
        return self._pos > 0

    @property
    def can_redo(self) -> bool:
        return self._pos < len(self.history) - 1

    def _get_fields_history(self):
        # DEBUG
        return [i.get('fields', []) for i in self.history]


class EmbedBuilder:
    """
    Used to build an embed using the user input.

    The class handles all the user input and embed building including the info
    presented to the user and the final embed, also referred as a preview. Lot
    of the methods return `cls` to allow method chaining.

    Attributes:
        ctx (discord.ext.commands.Context): The context of the invocation command.
    """
    ctx: Context

    # Instructions for the user
    _info_msg: Optional[Message] = None
    _info_embed: Embed = None

    # A preview of the actual embed
    _preview_msg: Optional[Message] = None
    _preview_embed: Embed = None

    # Field query
    _rcm: ReactionCallbackManager = None

    # History
    _history: EmbedHistory = None

    # Builder state
    _alive: bool

    # Constants
    UNDO_REACTION = '↩'
    REDO_REACTION = '↪'
    ADD_REACTION = '➕'
    EDIT_REACTION = '✏'
    REMOVE_REACTION = '➖'
    SAVE_REACTION = '✅'

    def __init__(self,
                 ctx: Context,
                 msg: Message = None):
        """
        Args:
            ctx (discord.ext.commands.Context): The context of the invocation
                command.
            msg (discord.Message): The message of the edited embed, if exists
                already. Can be None in case the embed is being created.
        """
        self.ctx = ctx
        self._preview_msg = msg
        if msg:
            self._preview_embed = msg.embeds[0]

        self._history = EmbedHistory()

        # Builder state
        self._alive = True

    @property
    async def info_msg(self) -> Message:
        if not self._info_msg:
            self._info_msg = await self.ctx.send(embed=self.info_embed)

        return self._info_msg

    @property
    def info_embed(self) -> Embed:
        if not self._info_embed:
            self._info_embed = Embed()

        return self._info_embed

    @property
    async def preview_msg(self) -> Message:
        if not self._preview_msg:
            self._preview_msg = await self.ctx.send(embed=Embed())

        return self._preview_msg

    @property
    def preview_embed(self) -> Embed:
        if not self._preview_embed:
            self._preview_embed = Embed()

        return self._preview_embed

    # Decorators
    # noinspection PyMethodParameters
    def async_update_preview(fn: Callable):
        # Asynchronously update the embed preview
        # Use with async functions only
        async def wrapper(self, *args, **kw):
            res = await fn(self, *args, **kw)

            await self._update_preview_msg()

            return res

        return wrapper

    # noinspection PyMethodParameters
    def restore_info(fn: Callable):
        # Save and then restore the info message embed after completed
        # Use with async functions only
        async def wrapper(self, *args, **kw):
            _embed_data = self.info_embed.to_dict()

            res = await fn(self, *args, **kw)

            self._info_embed = Embed.from_dict(_embed_data)
            await self._update_info_msg()

            return res

        return wrapper

    # noinspection PyMethodParameters
    def stack_to_history(fn: Callable):
        # Add the current embed to the history before applying any changes
        async def wrapper(self: EmbedBuilder, *args, **kw):
            ret = await fn(self, *args, **kw)

            await self._rcm.listen_for(self.UNDO_REACTION, self.undo)
            self._history.stack(self.preview_embed)

            return ret

        return wrapper

    # noinspection PyMethodParameters
    def update_rcm(fn: Callable):
        # Update the ReactionCallbackManager after the coroutine is executed

        async def wrapper(self, *args, **kw):
            ret = await fn(self, *args, **kw)

            await self._update_rcm()

            return ret

        return wrapper

    # Message management
    async def _update_info_msg(self) -> EmbedBuilder:
        # Update the input message remotely
        await (await self.info_msg).edit(embed=self.info_embed)

        return self

    async def _delete_info_msg(self) -> EmbedBuilder:
        # Delete the input message remotely
        await (await self.info_msg).delete()
        self._info_msg = None

        return self

    async def _update_preview_msg(self) -> EmbedBuilder:
        # Update the preview message remotely
        await (await self.preview_msg).edit(embed=self.preview_embed)

        return self

    async def _delete_preview_msg(self) -> EmbedBuilder:
        # Delete the preview message remotely
        await (await self.preview_msg).delete()
        self._preview_msg = None

        return self

    # noinspection PyArgumentList
    @update_rcm
    @async_update_preview
    async def undo(self) -> EmbedBuilder:
        """ Undo the last change to the preview embed. """
        self._preview_embed = self._history.undo()
        return self

    # noinspection PyArgumentList
    @update_rcm
    @async_update_preview
    async def redo(self) -> EmbedBuilder:
        """ Redo the undid chane to the preview embed. """
        self._preview_embed = self._history.redo()
        return self

    # User input
    async def _dismiss_reply(self, msg: Message) -> EmbedBuilder:
        # Add a reaction and delete the message
        await msg.add_reaction('❌')
        await asyncio.sleep(1)
        await msg.delete()

        return self

    async def _accept_reply(self, msg: Message) -> EmbedBuilder:
        # Add a reaction and delete the message
        await msg.add_reaction('✅')
        await asyncio.sleep(1)
        await msg.delete()

        return self

    def _check_input_message(self, msg: Message, regex: str):
        # Cancel input if builder should not be alive anymore
        if not self._alive:
            raise CancelCallback

        # Check author and channel
        if msg.author != self.ctx.author or msg.channel != self.ctx.channel:
            return False

        # Check regex
        if not re.match(regex, msg.clean_content):
            self.ctx.bot.loop.create_task(self._dismiss_reply(msg))
            return False

        self.ctx.bot.loop.create_task(self._accept_reply(msg))
        return True

    async def _request_input(self,
                             title: str,
                             description: str = '',
                             regex: str = ''):
        # Update the info embed
        self.info_embed.title = f'Enter the **{title}** ...'
        self.info_embed.description = description + f'\n\n*Regex:* `{regex}`' * bool(
            regex)
        await self._update_info_msg()

        # Wait for reply from the user
        _msg = await self.ctx.bot.wait_for(
            'message', check=lambda msg: self._check_input_message(msg, regex))

        return _msg.content

    # Embed building
    # noinspection PyArgumentList
    @async_update_preview
    async def set_title(self, title: str = None) -> EmbedBuilder:
        """ Request the user to enter the embed title or use the given one. """
        self.preview_embed.title = title or await self._request_input('title')

        return self

    # noinspection PyArgumentList
    @async_update_preview
    async def set_url(self, url: str = None) -> EmbedBuilder:
        """ Request the user to enter the embed url or use the given one. """
        self.preview_embed.url = url or await self._request_input('url')
        return self

    # noinspection PyArgumentList
    @async_update_preview
    async def set_description(self, description: str = None) -> EmbedBuilder:
        """ Request the user to enter the embed description or use the given one. """
        self.preview_embed.description = description or await self._request_input(
            'description')

        return self

    # noinspection PyArgumentList
    @async_update_preview
    async def set_color(self, color: str = None) -> EmbedBuilder:
        """ Request the user to enter the embed color or use the given one. """
        self.preview_embed.colour = await ColorConverter().convert(
            self.ctx, color or await self._request_input('color'))

        return self

    # noinspection PyArgumentList
    @async_update_preview
    async def set_footer(self, footer: str = None) -> EmbedBuilder:
        """ Request the user to enter the footer text or use the given one. """
        self.preview_embed.set_footer(
            text=footer or await self._request_input('footer'))

        return self

    # noinspection PyArgumentList
    @async_update_preview
    async def set_ctx_author(self) -> EmbedBuilder:
        """ Set the embed author automatically based on the context. """
        self.preview_embed.set_author(name=self.ctx.author.display_name,
                                      icon_url=self.ctx.author.avatar_url)

        return self

    # noinspection PyArgumentList
    @update_rcm
    @async_update_preview
    @restore_info
    @stack_to_history
    async def add_field(self) -> EmbedBuilder:
        """ Request the user to add a field. """
        self.preview_embed.add_field(name=await self._request_input('field name'),
                                     value=await
                                     self._request_input('field value'),
                                     inline=False)

        return self

    # noinspection PyArgumentList
    @update_rcm
    @async_update_preview
    @restore_info
    @stack_to_history
    async def edit_field(self) -> EmbedBuilder:
        """
        Request the user to edit an embed field at the given index. The user
        will be given option to edit either only the name or only the value or
        both.
        """

        # Pick the field index automatically if there's only one field
        if len(self.preview_embed.fields) == 1:
            index = 0
        else:
            # Ask the field index
            index = await self._request_input('field index', regex=common.Re.INDEX)
            index = int(index)

        if index >= len(self.preview_embed.fields):
            await TimeoutMessage(self.ctx).send(embed=common.Embed.INVALID_INDEX)
            return self

        # Ask what to edit
        _option = await self._request_input('digit saying what to edit',
                                            '0 = both, 1 = name, 2 = value',
                                            '^(0|1|2){1}$')
        _option = int(_option)

        # Ask the values
        _name = await self._request_input('field name') if _option in (
            0, 1) else self.preview_embed.fields[index].name
        _value = await self._request_input('field value') if _option in (
            0, 2) else self.preview_embed.fields[index].value

        # Modify the embed
        self.preview_embed.set_field_at(index,
                                        name=_name,
                                        value=_value,
                                        inline=False)

        return self

    # noinspection PyArgumentList
    @update_rcm
    @async_update_preview
    @restore_info
    @stack_to_history
    async def remove_field(self) -> EmbedBuilder:
        """ Remove an embed field at the user-specified index. """
        self.preview_embed.remove_field(
            int(await self._request_input('index of the field to remove',
                                          regex=common.Re.INDEX)))

        return self

    async def start_field_query(self) -> EmbedBuilder:
        """
        Provide reactions for the user in order to add/edit/remove fields.
        """

        # Save the embed to history
        self._history.stack(self.preview_embed)

        # Init the reaction trigger manager
        await self._update_rcm()

        # Inform the user about reactions and their callbacks
        self.info_embed.title = 'Use the reactions for further modifications'
        self.info_embed.description = (
            f'{self.ADD_REACTION} - Add field\n'
            f'{self.EDIT_REACTION} - Edit field\n'
            f'{self.REMOVE_REACTION} - Remove field\n'
            f'{self.UNDO_REACTION} - Undo\n'
            f'{self.REDO_REACTION} - Redo\n'
            f'{self.SAVE_REACTION} - Save\n')
        await self._update_info_msg()

        return self

    async def _update_rcm(self):
        # Update the reactions so it matches the possibilities of
        # editing the embed content

        if not self._rcm:
            self._rcm = ReactionCallbackManager(
                self.ctx, await self.preview_msg, {
                    self.ADD_REACTION: self.add_field,
                    self.SAVE_REACTION: self.cleanup
                })
            await self._rcm.asyncinit()

        # Field remove, edit
        if self.preview_embed.fields:
            await self._rcm.listen_for(self.REMOVE_REACTION, self.remove_field)
            await self._rcm.listen_for(self.EDIT_REACTION, self.edit_field)
        else:
            await self._rcm.remove_listen_for(self.REMOVE_REACTION)
            await self._rcm.remove_listen_for(self.EDIT_REACTION)

        # Undo
        if self._history.can_undo:
            await self._rcm.listen_for(self.UNDO_REACTION, self.undo)
        else:
            await self._rcm.remove_listen_for(self.UNDO_REACTION)

        # Redo
        if self._history.can_redo:
            await self._rcm.listen_for(self.REDO_REACTION, self.redo)
        else:
            await self._rcm.remove_listen_for(self.REDO_REACTION)

    async def cleanup(self) -> EmbedBuilder:
        """ Cleanup. Should be used after the embed is created. """
        # Cancel user input
        self._alive = False

        # Clean up reactions
        if self._rcm:
            await self._rcm.cleanup()

        # Clean up instructions message
        self.ctx.bot.loop.create_task(self._delete_info_msg())

        return self


class EmbedCog(Cog, name='Embed Builder'):
    """ Build and edit embeds. """

    @group()
    @list_subcommands
    @del_invoc
    async def embed(self, ctx: Context):
        """
        An embed builder.

        Available subcommands:
            new, edit
        """

        pass

    @embed.command()
    async def new(self, ctx: Context):
        """
        Build an embed with the help of Marvin.

        You will be asked to enter a title, descriptions, color and embed
        fields. The available colors are listed at the discord API
        documentation.
        """

        builder = EmbedBuilder(ctx)
        await builder.set_ctx_author()
        await builder.set_title()
        await builder.set_description()
        await builder.set_color()
        await builder.start_field_query()
        # From this point on, the builder will keep care of itself and doesn't
        # have to be cleaned up manually

    @embed.group()
    @list_subcommands
    async def edit(self, ctx: Context, index=0):
        """
        Edit an embed.

        An index of the embed needs to be given. The last sent embed has the
        index 0. The following example takes the last sent embed and edits its
        title. A subcommand and the actual argument needs to follow.

        Example:
            !embed edit 0 title MyAwesomeTitle

        Available subcommands:
            title, desc, footer, fields
        """

        # Convert index
        index = int(index)

        # Get the embed
        async for msg in ctx.history():
            if msg.embeds:
                index -= 1

                if index < 0:
                    # Make sure the bot will be able to edit this message
                    if ctx.bot.user != msg.author:
                        await TimeoutMessage(ctx).send('> ⚠ I have not created this embed, therefore I cannot edit it.')
                        return

                    # Add the embed, msg to the context, so subcommands can use it
                    ctx.msg = msg
                    break
        else:
            await TimeoutMessage(ctx).send(embed=common.Embed.INVALID_INDEX)
            return

    # noinspection PyMethodParameters
    # TODO ctx.message?
    def require_msg(fn: Callable):
        # A decorator aborting the command execution if ctx.msg attr is missing
        async def wrapper(self, ctx: Context, *args, **kw):
            if not hasattr(ctx, 'msg'):
                return

            await fn(self, ctx, *args, **kw)

        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        wrapper.__signature__ = inspect.signature(fn)

        return wrapper

    @edit.command(aliases=['t'])
    @require_msg
    async def title(self, ctx, *, title):
        """
        Edit the embed title.

        Example:
            !embed edit 0 title MyAwesomeTitle
        """

        await EmbedBuilder(ctx, ctx.msg).set_title(title)

    @edit.command(aliases=['u'])
    @require_msg
    async def url(self, ctx, *, url):
        """
        Edit the embed url.

        Example:
            !embed edit 0 url https://example.com
        """

        await EmbedBuilder(ctx, ctx.msg).set_url(url)

    @edit.command(aliases=['d'])
    @require_msg
    async def desc(self, ctx, *, description):
        # We cannot use `description` here, because it interferes with the cog.description property.
        """
        Edit the embed description.

        Example:
            !embed edit 0 desc MyAwesomeDescription
        """

        await EmbedBuilder(ctx, ctx.msg).set_description(description)

    @edit.command(aliases=['c'])
    @require_msg
    async def color(self, ctx, *, color):
        """
        Edit the embed color.

        Example:
            !embed edit 0 color green
            !embed edit 0 color 00ff00
            !embed edit 0 color #00ff00
            !embed edit 0 color 0x00ff00
            !embed edit 0 color 0x#00ff00
        """

        await EmbedBuilder(ctx, ctx.msg).set_color(color)

    @edit.command(aliases=['foo'])
    @require_msg
    async def footer(self, ctx, *, footer):
        """
        Edit the embed footer.

        Example:
            !embed edit 0 footer MyAwesomeFooter
        """
        await EmbedBuilder(ctx, ctx.msg).set_footer(footer)

    @edit.command(aliases=['f', 'field'])
    @require_msg
    async def fields(self, ctx):
        """
        Edit the fields using reaction. Further guide will be given.

        Example:
            !embed edit 0 fields
        """
        await EmbedBuilder(ctx, ctx.msg).start_field_query()


def setup(bot: Bot):
    bot.add_cog(EmbedCog())

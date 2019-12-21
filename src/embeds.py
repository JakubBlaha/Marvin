from __future__ import annotations

from copy import deepcopy
from typing import Callable, Optional, Union

from discord import Embed, HTTPException, Message
from discord.ext.commands import BadArgument, Bot, Cog, ColourConverter as ColorConverter, Context, Converter, group

import common
from decorators import del_invoc, list_subcommands
from reaction_callback_manager import ReactionCallbackManager
from timeout_message import TimeoutMessage
from utils import UserInput


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
    HELP_REACTION = '❔'

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

    async def _send_help(self):
        """ Send a help embed with an info about the reactions and their callbacks. """
        embed = Embed(title='Use the reactions for further modifications')

        embed.description = (
            f'{self.ADD_REACTION} - Add a field\n'
            f'{self.EDIT_REACTION} - Edit a field\n'
            f'{self.REMOVE_REACTION} - Remove a field\n'
            f'{self.UNDO_REACTION} - Undo\n'
            f'{self.REDO_REACTION} - Redo\n'
            f'{self.SAVE_REACTION} - Save\n'
            f'{self.HELP_REACTION} - Invoke this help')

        await TimeoutMessage(self.ctx, 10).send(embed=embed)

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

    # noinspection PyMethodParameters
    def async_update_preview(fn: Callable):
        """ Update the embed after the function finishes. """

        async def wrapper(self, *args, **kw):
            res = await fn(self, *args, **kw)

            await self._update_preview_msg()

            return res

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
    async def stack_to_history(self):
        """ Add the current embed state to the history. """
        self._history.stack(self.preview_embed)
        await self._rcm.listen_for(self.UNDO_REACTION, self.undo)

    async def _update_preview_msg(self):
        # Update the preview message remotely
        await (await self.preview_msg).edit(embed=self.preview_embed)

    # noinspection PyArgumentList
    @update_rcm
    @async_update_preview
    async def undo(self):
        """ Undo the last change to the preview embed. """
        self._preview_embed = self._history.undo()

    # noinspection PyArgumentList
    @update_rcm
    @async_update_preview
    async def redo(self):
        """ Redo the undid chane to the preview embed. """
        self._preview_embed = self._history.redo()

    # Embed building
    # noinspection PyArgumentList
    @async_update_preview
    async def set_title(self, title: str):
        """ Set the title of the embed. """
        self.preview_embed.title = title

    async def ask_title(self):
        await self.set_title(await UserInput(self.ctx).ask('title') or self.preview_embed.title)

    # noinspection PyArgumentList
    @async_update_preview
    async def set_url(self, url: str):
        """ Set the url of the embed. """
        self.preview_embed.url = url

    async def ask_url(self):
        await self.set_url(await UserInput(self.ctx).ask('url', regex=common.Re.URL) or self.preview_embed.url)

    # noinspection PyArgumentList
    @async_update_preview
    async def set_description(self, description: str):
        """ Set the description of the embed. """
        self.preview_embed.description = description

    async def ask_description(self):
        await self.set_description(await UserInput(self.ctx).ask('description') or self.preview_embed.description)

    # noinspection PyArgumentList
    @async_update_preview
    async def set_color(self, color: str):
        """ Convert and set the color of the embed. """
        self.preview_embed.colour = await ColorConverter().convert(self.ctx, color)

    async def ask_color(self):
        try:
            color: str = await UserInput(self.ctx).ask('color')
            if color:
                await self.set_color(color)
        except BadArgument:
            await TimeoutMessage(self.ctx).send('> ⚠ Bad color! Default one will be used.')
            self.preview_embed.colour = Embed.Empty

    # noinspection PyArgumentList
    @async_update_preview
    async def set_footer(self, footer: str):
        """ Set the footer of the embed. """
        self.preview_embed.set_footer(text=footer)

    async def ask_footer(self):
        await self.set_footer(await UserInput(self.ctx).ask('footer text') or self.preview_embed.footer.text)

    # noinspection PyArgumentList
    @async_update_preview
    async def set_ctx_author(self):
        """ Set the embed author automatically based on the context. """
        self.preview_embed.set_author(name=self.ctx.author.display_name,
                                      icon_url=self.ctx.author.avatar_url)

    # noinspection PyArgumentList
    @update_rcm
    @async_update_preview
    async def ask_add_field(self):
        """ Add a field. """
        field_name = await UserInput(self.ctx).ask('field name')
        if field_name is None:
            return

        self.preview_embed.add_field(
            name=field_name,
            value='...'
        )

        await self._update_preview_msg()
        await self.stack_to_history()

        field_value = await UserInput(self.ctx).ask('field value') or '(￣o￣) . z Z'
        self.preview_embed.set_field_at(-1, name=field_name, value=field_value)

        await self.stack_to_history()

    # noinspection PyArgumentList
    @update_rcm
    @async_update_preview
    async def edit_field(self):
        """
        Request the user to edit an embed field at the given index. The user will be asked to enter
        both the field name and the field value, but the user can reject to type in the new text by pressing
        on the cross reaction. In that case, the current values will be preserved.
        """

        # Pick the field index automatically if there's only one field
        if len(self.preview_embed.fields) == 1:
            index = 0
        else:
            # Ask the field index
            index = await UserInput(self.ctx).ask('field index', regex=common.Re.INDEX)

            if index is None:
                return

            index = int(index)

        if index >= len(self.preview_embed.fields):
            await TimeoutMessage(self.ctx).send(embed=common.Embed.INVALID_INDEX)
            return

        # Ask the values
        _name = await UserInput(self.ctx).ask('field name') or self.preview_embed.fields[index].name
        _value = await UserInput(self.ctx).ask('field value') or self.preview_embed.fields[index].value

        # Modify the embed
        self.preview_embed.set_field_at(index,
                                        name=_name,
                                        value=_value,
                                        inline=False)

        await self.stack_to_history()

    # noinspection PyArgumentList
    @update_rcm
    @async_update_preview
    async def remove_field(self):
        """ Remove an embed field at the user-specified index. """
        if len(self.preview_embed.fields) == 1:
            index = 0
        else:
            index = await UserInput(self.ctx).ask('index of the field to remove', regex=common.Re.INDEX)

        # User has cancelled the input
        if index is None:
            return

        self.preview_embed.remove_field(int(index))

        await self.stack_to_history()

    async def start_field_query(self):
        """ Provide reactions for the user in order to add/edit/remove fields. """
        # Save the embed to history
        self._history.stack(self.preview_embed)

        # Init the reaction trigger manager
        await self._update_rcm()

    async def _update_rcm(self):
        # Update the reactions so it matches the possibilities of
        # editing the embed content

        if not self._rcm:
            self._rcm = ReactionCallbackManager(
                self.ctx, await self.preview_msg, {
                    self.ADD_REACTION: self.ask_add_field,
                    self.SAVE_REACTION: self.cleanup,
                    self.HELP_REACTION: self._send_help
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

    async def cleanup(self):
        """ Cleanup. Should be used after the embed is created. """
        # Cancel user input
        self._alive = False

        # Clean up reactions
        if self._rcm:
            await self._rcm.cleanup()


class EmbedIndexMessageConverter(Converter):
    async def convert(self, ctx: Context, argument: Union[str, int]):
        index = int(argument)

        # Get the embed
        async for msg in ctx.history():
            if msg.embeds:
                index -= 1

                if index == -1:
                    return msg
        else:
            await TimeoutMessage(ctx).send(embed=common.Embed.INVALID_INDEX)


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

    @embed.command()
    async def new(self, ctx: Context):
        """
        Build an embed with the help of Marvin.

        You will be asked to enter a title, description, color and embed
        fields. The available colors are listed in the discord API
        documentation.
        """

        builder = EmbedBuilder(ctx)
        await builder.set_ctx_author()
        await builder.ask_title()
        await builder.ask_description()
        await builder.ask_color()
        await builder.start_field_query()
        # From this point on, the builder will keep care of itself and doesn't
        # have to be cleaned up manually

    @embed.group()
    @list_subcommands
    async def edit(self, ctx: Context):
        """
        Edit an embed.

        An index of the embed needs to be given to each and every subcommand. The last sent embed is considered
        to be of index `0`. The following example takes the last sent embed and edits its
        title. The actual value needs to follow after the embed index.

        Example:
        ```
        !embed edit title 0 MyAwesomeTitle
        ```
        """

    @edit.command(aliases=['t'])
    async def title(self, ctx, msg_index: EmbedIndexMessageConverter, *, title=None):
        """
        Edit the embed title.

        Example:
        ```
        !embed edit title 0 MyAwesomeTitle
        ```
        """

        # noinspection PyTypeChecker
        b = EmbedBuilder(ctx, msg_index)
        await (b.set_title(title) if title else b.ask_title())

    @edit.command(aliases=['u'])
    async def url(self, ctx: Context, msg_index: EmbedIndexMessageConverter, *, url=None):
        """
        Edit the embed url.

        Example:
        ```
        !embed edit url 0 https://example.com
        ```
        """

        # noinspection PyTypeChecker
        b = EmbedBuilder(ctx, msg_index)
        try:
            await (b.set_url(url) if url else b.ask_url())
        except HTTPException:
            await TimeoutMessage(ctx).send('> Not well formed url!')

    @edit.command(aliases=['d'])
    async def desc(self, ctx: Context, msg_index: EmbedIndexMessageConverter, *, description=None):
        # We cannot use `description` here, because it interferes with the cog.description property.
        """
        Edit the embed description.

        Example:
        ```
        !embed edit desc 0 MyAwesomeDescription
        ```
        """

        # noinspection PyTypeChecker
        b = EmbedBuilder(ctx, msg_index)
        await (b.set_description(description) if description else b.ask_description())

    @edit.command(aliases=['c'])
    async def color(self, ctx: Context, msg_index: EmbedIndexMessageConverter, *, color=None):
        """
        Edit the embed color.

        Example:
        ```
        !embed edit color 0 green
        !embed edit color 0 00ff00
        !embed edit color 0 #00ff00
        !embed edit color 0 0x00ff00
        !embed edit color 0 0x#00ff00
        ```
        """

        # noinspection PyTypeChecker
        b = EmbedBuilder(ctx, msg_index)
        await (b.set_color(color) if color else b.ask_color())

    @edit.command(aliases=['foo'])
    async def footer(self, ctx: Context, msg_index: EmbedIndexMessageConverter, *, footer=None):
        """
        Edit the embed footer.

        Example:
        ```
        !embed edit footer 0 MyAwesomeFooter
        ```
        """

        # noinspection PyTypeChecker
        b = EmbedBuilder(ctx, msg_index)
        await (b.set_footer(footer) if footer else b.ask_footer())

    @edit.command(aliases=['f', 'field'])
    async def fields(self, ctx: Context, msg_index=0):
        """
        Edit the fields using reactions.

        The `msg_index` argument may be omitted. In that case, the most recent embed in the
        channel will be edited.

        Example:
        ```
        !embed edit fields 0
        ```
        """
        embed = await EmbedIndexMessageConverter().convert(ctx, msg_index)
        await EmbedBuilder(ctx, embed).start_field_query()


def setup(bot: Bot):
    bot.add_cog(EmbedCog())

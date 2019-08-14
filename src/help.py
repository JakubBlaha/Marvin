from typing import List, Dict, Iterable, Optional, Union

from discord import Embed, Color
from discord.ext.commands import DefaultHelpCommand, Cog, Command, Group

from timeout_message import TimeoutMessage
from utils import WideEmbed


class DummyCog(Cog):
    qualified_name = '¯\\\\_(ツ)_/\u2060¯'
    description = None
    _commands: list

    def __init__(self, commands: Iterable[Command]):
        self._commands = list(commands)

    def get_commands(self) -> List[Command]:
        return self._commands.copy()


class ColorCycler:
    colors = [
        Color.teal,
        Color.green,
        Color.blue,
        Color.purple,
        Color.magenta,
        Color.gold,
        Color.orange,
        Color.red,
        Color.light_grey,
        Color.blurple,
        Color.greyple
    ]

    @classmethod
    def next(cls):
        cls.colors.append(cls.colors.pop(0))
        return cls.colors[-1]()


class CustomHelpCommand(DefaultHelpCommand):
    command_attrs = {'hidden': False}

    @staticmethod
    def _code_format_seq(seq: Iterable) -> str:
        """ Format the sequence so each element is surrounded by inline code block and the seq sorted. """
        return '`' + '`, `'.join(sorted(seq)) + '`'

    # noinspection PyMethodOverriding
    @staticmethod
    def get_command_signature(command: Union[Group, Command]) -> str:
        """ Get the full command syntax along with the ! and command names formatted in a code block. """
        syntax = '`!'
        for parent in tuple(reversed(command.parents)) + (command,):
            syntax += f'{parent.name} {parent.signature} '

        return syntax.strip() + '`'

    async def send_bot_help(self, mapping: Dict[Optional[Cog], List[Command]]):
        # Prepare the list of cogs
        cogs = list(mapping.keys())

        # Replace the no-category with a pseudo cog
        if None in mapping:
            cogs.append(DummyCog(mapping[None]))
            cogs.remove(None)

        # Send help for each cog
        for cog in sorted(cogs, key=lambda x: x.qualified_name):
            await self.send_cog_help(cog)

    async def send_cog_help(self, cog: Cog):
        # Make the embed
        embed = WideEmbed(title=f'Category: **{cog.qualified_name}**',
                          # We are putting large amount of unbreakable spaces in the embed title
                          # so all the embeds have the same size. Then we are replacing all spaces
                          # in the string (including the cog name) with unbreakable spaces, so all
                          # the content stays on the same line.
                          description=f'*{cog.description.strip()}*' if cog.description else None,
                          color=ColorCycler.next())

        # Iter through commands, add embed fields
        # for command in sorted(cog.get_commands(), key=lambda x: x.name):
        listed_commands = []
        for command in cog.walk_commands():
            # Skip if hidden or added already
            if command.hidden or command in listed_commands:
                continue

            # Add field
            embed.add_field(
                name=f'!`{command.qualified_name}`' + (
                    f'*({self._code_format_seq(command.aliases)})*' if command.aliases else ''),
                # The full command name with the aliases after
                value=command.short_doc or '...',
                inline=False)

            listed_commands.append(command)

        # Send the embed at least one of the commands is not hidden
        if embed.fields:
            await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        embed = Embed(
            title=f'`!{group.qualified_name}`',
            description=group.help,
            color=ColorCycler.next()
        )

        embed.add_field(name='Category', value=group.cog_name)
        embed.add_field(name='Syntax', value=self.get_command_signature(group))
        embed.add_field(name='Subcommands', value=self._code_format_seq(map(lambda x: x.name, group.commands)))
        if group.aliases:
            embed.add_field(name='Aliases', value=self._code_format_seq(group.aliases))
        embed.set_footer(text=f'Type [ !help {group.qualified_name} <subcommand> ] to see more.')

        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        embed = Embed(
            title=f'`!{command.qualified_name}`',
            description=command.help,
            color=ColorCycler.next()
        )

        embed.add_field(name='Category', value=command.cog_name)
        embed.add_field(name='Syntax', value=self.get_command_signature(command))
        if command.aliases:
            embed.add_field(name='Aliases', value=self._code_format_seq(command.aliases))

        await self.get_destination().send(embed=embed)

        print(self.get_command_signature(command))

    async def command_not_found(self, string):
        return f'⚠ Command **`{string}`** not found. Are you sure?'

    async def subcommand_not_found(self, group: Group, string):
        return f'⚠ Subcommand **`{string}`** not found. Available subcommands are ' \
               f'{self._code_format_seq(map(lambda x: x.name, group.commands))}.'

    async def send_error_message(self, error):
        embed = Embed(
            title='Oh no!',
            description=error,
            color=Color.red()
        )
        embed.set_footer(text='Type [ !help ] in case you are lost.')

        await TimeoutMessage(self.context, 10).send(embed=embed)
        await self.context.message.delete()

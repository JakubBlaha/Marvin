import discord


class Re:
    INDEX = '^[0-9]+$'


class Embed:
    INVALID_INDEX = discord.Embed(
        title='⚠ Invalid index!',
        description=
        'All indexes are counted from *0*, the most recent for message and the most top for embed fields!'
    )

    TOO_OLD_MESSAGES = discord.Embed(
        title='⚠ Failed to delete some messages!',
        description='Can only delete messages 14 days old an younger. Sorry. API thing... '
    )

    COMMAND_ERROR = discord.Embed(
        title='⚠ Error occured!',
        description=
        'There was an error executing the command. Please tell the @bot_developer or contribute to the project.'
    )

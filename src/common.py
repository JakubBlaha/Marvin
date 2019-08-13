import discord


class Re:
    INDEX = '^[0-9]+$'


class Embed:
    INVALID_INDEX = discord.Embed(
        title='⚠ Invalid index!',
        description=
        'All indexes are counted from *0*, the most recent for message and the most top for embed fields!'
    )

    DELETE_MESSAGES_ERROR = discord.Embed(
        title='⚠ Failed to delete some messages!',
        description='I could not delete the messages, sorry. :frowning: '
    )

    COMMAND_ERROR = discord.Embed(
        title='⚠ Error occurred!',
        description=
        'There was an error executing the command. Please tell the @bot_developer or contribute to the project.'
    )

    EMPTY_CHANNEL = discord.Embed(
        title='Am I blind?',
        description='⚠ No messages in the channel were found!'
    )

    NO_COMMAND_EXECUTED_YET = discord.Embed(
        title='Oops!',
        description='⚠ I cannot remember that you would execute a command. Please do so.'
    )

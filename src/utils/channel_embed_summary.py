from discord import Embed, TextChannel, Color

from utils.get_datetime_from_string import get_datetime_from_string


async def channel_embed_summary(channel: TextChannel) -> Embed:
    # Get the embeds
    _embeds = [msg.embeds[0] async for msg in channel.history() if msg.embeds]

    # Sort by date
    _embeds.sort(key=lambda x: get_datetime_from_string(x.description),
                 reverse=True)

    # Build the embed
    _embed = Embed()
    for embed in _embeds:
        _embed.add_field(name=f'**{embed.title}**, {embed.description}',
                         value=', '.join(f.name for f in embed.fields),
                         inline=False)
    if not _embed.fields:
        _embed.title = 'Nothing to see here!'
        _embed.description = '\(￣︶￣*\))'
        _embed.color = Color.green()
    else:
        _embed.color = Color.red()

    return _embed

from datetime import datetime, timedelta
from discord import Embed

from .date_processing import str_to_datetime


def is_embed_up_to_date(embed: Embed) -> bool:
    if not embed.description:
        return True

    d = str_to_datetime(embed.description)

    return d > datetime.now() + timedelta(days=-1)


if __name__ == "__main__":
    e = Embed(description='6. dubna')
    print(is_embed_up_to_date(e))
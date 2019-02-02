import yaml

from logger import Logger

TEMPLATE = '<:{name}:{id}>'


class EmojisMeta(type):
    '''
    Access server custom emojis from the specified file. The emojis will be
    set as attributes of this class in a string with format `<:name:id>`.
    Note that these emojis are not instances of the `discord.Emoji` class.
    '''

    FNAME = 'res/emojis.yaml'

    def __init__(cls, *args, **kw):
        super().__init__(*args, **kw)

        try:
            with open(cls.FNAME) as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            Logger.error(f'Emoji: {cls.FNAME} not found')
            return

        for name, id_ in data.items():
            setattr(cls, name, TEMPLATE.format(name=name, id=id_))

        Logger.info(f'Emoji: Loaded emojis from {cls.FNAME}')


class Emojis(metaclass=EmojisMeta):
    pass

from logger import Logger

TEMPLATE = '<:{0}:{1}>'


class EmojisMeta(type):
    '''
    A metaclass for the class Emojis.

    The method `reload` has to be called explicitly before the emojis
    can be accessed.
    '''

    def __init__(cls, *args, **kw):
        super().__init__(*args, **kw)

    def reload(cls, client):
        ''' Reload all custom emoji the client has an access to. '''

        Logger.info('Emojis: Reloading emojis..')

        for e in client.emojis:
            setattr(cls, e.name, TEMPLATE.format(e.name, e.id))


class Emojis(metaclass=EmojisMeta):
    ''' Class provoding client emoji mentions as attributes. '''

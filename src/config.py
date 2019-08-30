import logging
import sys
from typing import List, Tuple

import yaml

logger = logging.getLogger('Config')


class ConfigMeta(type):
    """
    Loads a config file as attributes of the subclass of this class.
    """

    def __init__(cls, *args):
        """
        Will load the config data from `config.yaml`. Can be overridden in order to load from another sources.
        The `from_data` method then needs to be called explicitly.
        """

        super().__init__(*args)

        # Load config
        with open('config.yaml') as f:
            data = yaml.safe_load(f)
        cls.from_data(data)

    def from_data(cls, data: dict):
        """ Set the attributes from the given data. This needs to be called explicitly if __init__ is overridden. """
        # Set values
        for k, v in data.items():
            if k not in cls.__annotations__:
                logger.warning(f'Setting redundant config value `{k}`! Is it a typo?')

            setattr(cls, k, v)

        # Check all the values are filled in and the correct type
        for name, expected_type in cls.__annotations__.items():
            if not hasattr(cls, name):
                logger.critical(f'Required value `{name}` has not been set in the config!')
                sys.exit()

            # Skip check if typing was used for annotating
            if getattr(expected_type, '_name', None) in ('List', 'Tuple', 'Dict', 'EncryptedString'):
                continue

            value_type = type(getattr(cls, name))
            if value_type != expected_type:
                logger.warning(
                    f'Value `{name}` in the config has not the expected type ({expected_type})'
                    f' but a type of {value_type}!')


class Config(metaclass=ConfigMeta):
    # Critical values
    token: str
    guild_id: int

    # Optional values
    presences: List[Tuple[str, str]] = []
    loglevel: int = logging.WARNING
    modulelog: bool = False
    remote_config_channel_name: str = 'config'

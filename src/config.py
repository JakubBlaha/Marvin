import logging
import sys
from typing import List, Tuple

import yaml

logger = logging.getLogger('Config')


class ConfigMeta(type):
    _override_annotations = {}

    def __init__(cls, *args):
        super().__init__(*args)

        # Load config
        with open('config.yaml') as f:
            data = yaml.safe_load(f)

        # Set values
        for k, v in data.items():
            if k not in cls.__annotations__:
                logger.warning(f'Setting redundant config value `{k}`! Is it a typo?')

            setattr(cls, k, v)

        # Check all the values are filled in and the correct type
        for name, expected_type in {**cls.__annotations__, **cls._override_annotations}.items():
            if not hasattr(cls, name):
                logger.critical(f'Required value `{name}` has not been set in the config!')
                sys.exit()

            value_type = type(getattr(cls, name))
            if value_type != expected_type:
                logger.critical(
                    f'Value `{name}` in the config has not the expected type ({expected_type})'
                    f' but a type of {value_type}!')
                sys.exit()


class Config(metaclass=ConfigMeta):
    # Critical values
    token: str
    guild_id: int

    # Optional values
    moodle_username: str = ''
    moodle_password: str = ''
    presences: List[Tuple[str, str]] = []
    loglevel: int = logging.WARNING
    modulelog: bool = False

    _override_annotations = {'presences': list}

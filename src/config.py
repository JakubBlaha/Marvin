import logging
from typing import Any, List, Tuple

import yaml

logger = logging.getLogger('Config')

ANNOTATION_CONVERTING_OVERRIDES = {'List': list, 'Tuple': tuple, 'Dict': dict}


class EmptyValue:
    pass


class ConfigBase:
    """
    This class allows to access the config values in a discord channel, which's
    name is `config` by default. This allows multiple instances in different
    environments to all have the same config setup shared together.

    This file has to be added as an extension. Then values can be accessed lie so.

        from remote_config import RemoteConfig\n
        name = RemoteConfig.name

    Attributes:
        failed_conversions: A list of (name, value, exception) tuples containing the conversions that failed.
    """

    failed_conversions: List[Tuple[str, Any, Exception]]  # name, value, exception

    def __init__(self, data: dict):
        self.failed_conversions = []

        for name, expected_type in self.__annotations__.items():
            # Get the actual value
            default = getattr(self, name)
            value = data.get(name, default)

            if default == value:
                continue

            if value is EmptyValue:
                logger.warning(f'Entry {name} not present in the data!')
                continue

            # See if there is an override for the conversion type
            expected_type = ANNOTATION_CONVERTING_OVERRIDES.get(
                getattr(expected_type, '_name', None),
                expected_type)

            if not isinstance(value, expected_type):
                # Try to convert the value to the type specified by the type annotations
                try:
                    value = expected_type(value)
                except Exception as ex:
                    logger.warning(f'Could not convert entry {name}: {value} to type {expected_type}, {ex}!')
                    self.failed_conversions.append((name, value, ex))

            setattr(self, name, value)


class LocalConfig(ConfigBase):
    # Critical values
    token: str = EmptyValue
    guild_id: int = EmptyValue

    # Optional values
    loglevel: int = logging.WARNING
    modulelog: bool = False
    remote_config_channel_name: str = 'config'
    command_prefix: str = '!'
    load_dev_config: bool = False
    headless_chrome: bool = True


# Config: LocalConfig
with open('config.yaml') as f:
    Config = LocalConfig(yaml.safe_load(f))

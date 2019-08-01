import logging
import os
import sys

import yaml

# Name constants / code completion help
TOKEN = 'token'
GUILD_ID = 'guild_id'

MOODLE_USERNAME = 'username'
MOODLE_PASSWORD = 'password'

LOG_CHANNEL_ID = 'log_channel_id'
DISABLE_LOGS = 'disable_logs'

PRESENCE = 'presence'
STATUS = 'status'

REQUIRED_ENTRIES = [TOKEN, GUILD_ID]

logger = logging.getLogger('Config')


class ConfigMeta(type):
    _FILENAME = 'config.yaml'
    _store = {}

    def __init__(cls, *args, **kw):
        super().__init__(*args, **kw)

        try:
            cls.ensure_file()
            cls.reload()
        except Exception as e:
            logger.critical('Failed to read the config file! Exiting.. \n', e)
            sys.exit()

    def reload(cls):
        with open(cls._FILENAME, encoding='utf-8') as f:
            cls._store = yaml.safe_load(f)

        if cls._store is None:
            cls._store = {}

        cls._data_ok()

    def _data_ok(cls):
        local_keys = cls._store.keys()

        for entry in REQUIRED_ENTRIES:
            if entry not in local_keys:
                raise ValueError(f'{entry} not present in {cls._FILENAME}')

    def ensure_file(cls):
        if not os.path.isfile(cls._FILENAME):
            raise FileNotFoundError(f'{cls._FILENAME} not found! Exiting..')

    def __getattr__(cls, name: str):
        return cls._store.get(name)

    def __setattr__(cls, name: str, value):
        if name.startswith('_'):
            return type.__setattr__(cls, name, value)
        cls._store[name] = value

    def save(cls):
        with open(cls._FILENAME, 'w') as f:
            yaml.dump(cls._store, f)

    def get(cls, name, default=None):
        """ Use instead of `getattr`. """
        return cls._store.get(name, default)


class Config(metaclass=ConfigMeta):
    pass

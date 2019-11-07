import logging
import os
import pickle
from dataclasses import dataclass
from time import time
from typing import Any

CACHE_PATH = 'cache/'

logger = logging.getLogger('Cache')

# Ensure the cache dir is present so we do not have to check for it every time.
os.makedirs(CACHE_PATH, exist_ok=True)


@dataclass
class CacheEntry:
    timestamp: float
    obj: Any


class Cache:
    @staticmethod
    def _get_path(key: str) -> str:
        """ Get the path of the file with the cached object depending on the key. """
        return os.path.join(CACHE_PATH, key)

    @classmethod
    def cache(cls, key: str, value: Any):
        """ Cache a key: value pair which can be retrieved later. """
        _entry = CacheEntry(time(), value)
        _path = cls._get_path(key)

        # Open file and dump
        with open(_path, 'wb') as f:
            pickle.dump(_entry, f)

        logger.debug(f'Cached "{key}" to "{_path}"')

    @classmethod
    def load(cls, key: str, lasts_seconds: int) -> Any:
        """ Return the cached value for the key.

        :param key: The key.
        :param lasts_seconds: The amount of seconds the value should last. None will be returned if the cached value
            has already expired. Set to 0 if the cached value should never expire.
        :return: Cached value for key. None if expired or no value is cached for the specified key.
        """

        _path = cls._get_path(key)

        try:
            with open(_path, 'rb') as f:
                _entry: CacheEntry = pickle.load(f)
        except (OSError, FileNotFoundError):
            logger.debug(f'{_path} not found.')
            return

        # print(_entry.obj)

        if lasts_seconds == 0 or time() - _entry.timestamp < lasts_seconds:
            logger.debug(f'Returned cached value for key {key}.')
            return _entry.obj

        logger.debug(f'The cached value for key {key} has expired.')


if __name__ == '__main__':
    _obj = ['Lol', 'Test', 1, 0.5]
    _key = 'test'

    Cache.cache(_key, _obj)
    assert Cache.load(_key, 10) == _obj

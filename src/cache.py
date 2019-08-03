import logging
import os
from time import time

import yaml

CACHE_PATH = 'cache/cache.yaml'

logger = logging.getLogger('Cache')


class Cache:
    @classmethod
    def cache(cls, key, value):
        """ Cache a key: value pair which can be retrieved later. """
        data = cls._read_cache()
        data[key] = {'stamp': time(), 'value': value}

        cls._write_cache(data)

        logger.debug(f'Cached {key}={value}')

    @classmethod
    def load(cls, key, lasts_seconds: int):
        """ Return the cached value for the key.

        :param key: The key.
        :param lasts_seconds: The amount of seconds the value should last. None will be returned if the cached value
            has already expired. Set to 0 if the cached value should never expire.
        :return: Cached value for key. None if expired.
        """
        data = cls._read_cache()
        entry = data.get(key, {})

        # Log if entry not found
        if not entry:
            logger.debug(f'No cached value for key {key} found.')
            return

        if lasts_seconds == 0 or time() - entry.get('stamp', 0) < lasts_seconds:
            logger.debug(f'Returned cached value for key {key}.')
            return entry.get('value')

        logger.debug(f'The cached value for key {key} has expired.')

    @classmethod
    def clear_entry(cls, key):
        """ Remove the specified entry from the cache. Return the cached value. None if not found. """
        data = cls._read_cache()
        value = data.pop(key, {})
        cls._write_cache(data)

        logger.debug(f'Cleared entry {key}')

        return value.get('value')

    @staticmethod
    def _read_cache() -> dict:
        logger.debug('Reading cache ...')

        try:
            with open(CACHE_PATH) as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}

    @staticmethod
    def _write_cache(cache: dict):
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

        with open(CACHE_PATH, 'w') as f:
            yaml.safe_dump(cache, f, default_flow_style=True)

        logger.debug('Updated cache')

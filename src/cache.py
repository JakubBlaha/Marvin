import os
from time import time

import yaml

from logger import Logger

CACHE_PATH = 'cache/cache.yaml'
TAG = 'Cache'


class Cache:
    @classmethod
    def cache(cls, key, value):
        """ Cache a key: value pair which can be retrieved later. """
        data = cls._read_cache()
        data[key] = {'stamp': time(), 'value': value}

        cls._write_cache(data)

        Logger.info(TAG, f'Cached {key}={value}')

    @classmethod
    def load(cls, key, lasts_seconds: int):
        """ Return the cached value for the key. None if expired. """
        data = cls._read_cache()
        entry = data.get(key, {})

        # Log if entry not found
        if not entry:
            Logger.info(TAG, f'No cached value for key {key} found')
            return

        if time() - entry.get('stamp', 0) < lasts_seconds:
            Logger.info(TAG, f'Returned cached value for key {key}')
            return entry.get('value')
        else:
            Logger.info(TAG, f'The cached value for key {key}')
            return

    @staticmethod
    def _read_cache() -> dict:
        Logger.info(TAG, 'Reading cache ...')

        try:
            with open(CACHE_PATH) as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {}

    @staticmethod
    def _write_cache(cache: dict):
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

        with open(CACHE_PATH, 'w') as f:
            yaml.safe_dump(cache, f, default_flow_style=True)

        Logger.info(TAG, 'Updated cache')

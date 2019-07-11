from typing import Callable
from time import time
import yaml
import os

CACHE_PATH = 'cache/cache.yaml'


class Cacher:
    """ Cache the output of a function. """

    _expire_time: int
    _func: Callable
    _args: tuple
    _kw: dict

    def __init__(self,
                 func: Callable,
                 args: tuple = (),
                 kw: dict = None,
                 expire_time: int = 600):
        self._expire_time = expire_time
        self._func = func
        self._args = args
        self._kw = kw or {}

    @property
    def output(self):
        return LocalCacher.load(self._func.__name__,
                                self._expire_time) or self.call()

    def call(self, *args, **kw):
        """
        Call the function. If no args or kwargs are given, use the ones that
        were specified on instantiation. Cache the output. Return the output.
        """

        if not (args and kw):
            args = self._args
            kw = self._kw

        # Call
        _output = self._func(*args, **kw)

        # Cache to drive
        LocalCacher.cache(self._func.__name__, _output)

        return _output


class LocalCacher:
    @classmethod
    def cache(cls, key, value):
        _data = cls._read_cache()
        _data.update(cls._gen_cache(key, value))
        cls._write_cache(_data)

    @classmethod
    def load(cls, key, lasts: int):
        _data = cls._read_cache()
        _cached = _data.get(key, {})
        return _cached.get(
            'value',
            None) if time() - _cached.get('stamp', 0) < lasts else None

    @staticmethod
    def _read_cache() -> dict:
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

    @staticmethod
    def _gen_cache(key, value) -> dict:
        return {key: {'stamp': time(), 'value': value}}

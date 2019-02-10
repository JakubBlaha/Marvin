import os
import yaml

REQUIRED_ENTRIES = ['token']


class ConfigMeta(type):
    _FILENAME = 'config.yaml'
    _store = {}

    def __init__(cls, *args, **kw):
        super().__init__(*args, **kw)

        cls.ensure_file()
        cls.reload()

    def reload(cls):
        with open(cls._FILENAME) as f:
            cls._store = yaml.safe_load(f)

        if cls._store is None:
            cls._store = {}

        cls._data_ok()

    def _data_ok(cls):
        local_keys = cls._store.keys()
        print(local_keys)

        for entry in REQUIRED_ENTRIES:
            if not entry in local_keys:
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

    def get(cls, name, default):
        ''' Use instead of `getattr`. '''
        return cls._store.get(name, default)


class Config(metaclass=ConfigMeta):
    pass
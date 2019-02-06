import os
import yaml


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

    def ensure_file(cls):
        if not os.path.isfile(cls._FILENAME):
            open(cls._FILENAME, 'w').close()

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
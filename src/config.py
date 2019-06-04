import os
import yaml

# Name constants / intellisense help
TOKEN = 'token'
GUILD_ID = 'guild_id'

MOODLE_USERNAME = 'username'
MOODLE_PASSWORD = 'password'

LOG_CHANNEL_ID = 'log_channel_id'
DISABLE_LOGS = 'disable_logs'

PRESENCE = 'presence'
STATUS = 'status'

EMBED_EXCLUSION_CHANNEL_ID = 'embed_exclusion_alert_channel_id'
EMBED_EXCLUSION_CHANNEL_IDS = 'embed_exclusion_channel_ids'
EMBED_EXCLUSION_ALERT_ROLE_ID = 'embed_exclusion_alert_role_id'
EMBED_EXCLUSION_CHECK_INTERVAL = 'embed_exclusion_check_interval'

TABLE_REPLACEMENTS = 'table_replacements'
TABLE_HEADERS = 'table_headers'
TABLE_COLS = 'table_cols'

UPCOMING_EVENTS_NOTIF_CHANNEL_ID = 'upcoming_events_notif_channel_id'
UPCOMING_EVENTS_NOTIF_CHECKED_CHANNELS = 'upcoming_events_notif_checked_channels'
UPCOMING_EVENTS_NOTIF_INTERVAL = 'upcoming_events_notif_interval'

TIMETABLE_URL = 'timetable_url'

AUTO_REACTOR_CHANNEL_IDS = 'auto_reactor_channel_ids'
AUTO_REACTOR_REACTION_IDS = 'auto_reactor_reaction_ids'


REQUIRED_ENTRIES = [TOKEN, GUILD_ID]


class ConfigMeta(type):
    _FILENAME = 'config.yaml'
    _store = {}

    def __init__(cls, *args, **kw):
        super().__init__(*args, **kw)

        try:
            cls.ensure_file()
            cls.reload()
        except Exception:
            print('Failed to read the config file!')

    def reload(cls):
        with open(cls._FILENAME, encoding='utf-8') as f:
            cls._store = yaml.safe_load(f)

        if cls._store is None:
            cls._store = {}

        cls._data_ok()

    def _data_ok(cls):
        local_keys = cls._store.keys()

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
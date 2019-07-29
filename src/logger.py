import asyncio
import io
import os
import shutil
import sys

import colorama
from discord import Client, TextChannel
from termcolor import colored

from config import Config

colorama.init()

MSG_TEMPLATE = '```python\n{}```'
DEBUG = colored('DEBUG', 'magenta')
INFO = colored('INFO', 'blue')
WARNING = colored('WARNING', 'yellow')
ERROR = colored('ERROR', 'red')


class LogBridge:
    _client: Client = None
    _channel_id: int = None
    _channel: TextChannel = None

    _buffer: io.StringIO = None
    _buffer_size: int = 1980

    def __init__(self,
                 channel_id: int,
                 client: Client,
                 buffer_size: int = 1980):
        self._client = client
        self._channel_id = channel_id
        self._buffer_size = buffer_size

        self._make_buffer()

        client.loop.create_task(self._flush_loop())

    def _make_buffer(self):
        self._buffer = io.StringIO()

    def _io_full(self):
        return len(self._buffer.getvalue()) > self._buffer_size

    @property
    def channel(self):
        if not self._channel:
            self._channel = self._client.get_channel(self._channel_id)
        return self._channel

    def flush(self):
        if not (self.channel and self._buffer.getvalue()):
            return

        self._client.loop.create_task(
            self.channel.send(MSG_TEMPLATE.format(self._buffer.getvalue())))

        # Reset the buffer
        self._make_buffer()

    def write(self, s: str):
        self._buffer.write(s)

        # Dump if necessary
        if self._io_full():
            self.flush()

    async def _flush_loop(self):
        _interval = int(Config.get('channel_log_flush_interval', 10))

        while True:
            self.flush()
            await asyncio.sleep(_interval)


class LoggerMeta(type):
    LOG_DIR = 'logs'
    MAX_LOG_FILE_COUNT = 10

    log = io.StringIO()
    _bridge = io.StringIO()
    _client = None

    def __init__(cls, *args, **kw):
        super().__init__(*args, **kw)

        # file logging
        if Config.get('disable_logs', False):
            return

        cls._ensure_dir()

        # get the log filename
        fnames = os.listdir(cls.LOG_DIR)
        for i in range(cls.MAX_LOG_FILE_COUNT):
            _fname = f'{i}.txt'
            if _fname not in fnames:
                cls.fname = _fname
                break

        # when max logs count, purge
        if not hasattr(cls, 'fname'):
            shutil.rmtree(cls.LOG_DIR)
            cls._ensure_dir()
            cls.fname = '0.txt'
            cls.info(f'Logger: Purged `{cls.LOG_DIR}`')

        cls.log = open(os.path.join(cls.LOG_DIR, cls.fname),
                       'w',
                       encoding='utf-8')

    @property
    def client(cls):
        return cls._client

    @client.setter
    def client(cls, value):
        cls._client = value
        cls._init_bridge()

    def _init_bridge(cls):
        cls._bridge = LogBridge(Config.log_channel_id, cls.client)

    def _ensure_dir(cls):
        os.makedirs(cls.LOG_DIR, exist_ok=True)

    def __del__(cls):
        cls.flush()
        cls.log.close()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    def _log(cls, level, *args):
        if not 0 < len(args) < 3:
            raise ValueError(f'Invalid arguments: {args}')

        if len(args) < 2:
            tag, msg = args[0].split(':', 1)
        else:
            tag, msg = args

        tag = str(tag).strip()
        msg = str(msg).strip()

        sys.stdout.write(f'[{level.ljust(16)}] [{tag.ljust(20)}] {msg}\n')

    def debug(cls, *args):
        cls._log(DEBUG, *args)

    def info(cls, *args):
        cls._log(INFO, *args)

    def warning(cls, *args):
        cls._log(WARNING, *args)

    def error(cls, *args):
        cls._log(ERROR, *args)

    def write(cls, msg):
        sys.__stdout__.write(msg)
        sys.__stdout__.flush()
        cls.log.write(msg)
        cls._bridge.write(msg)

    def flush(cls):
        sys.__stdout__.flush()
        cls.log.flush()
        cls._bridge.flush()

    def get_log(cls):
        return cls.log.getvalue()


class Logger(metaclass=LoggerMeta):
    pass


sys.stdout = Logger
# sys.stderr = Logger

if __name__ == "__main__":
    Logger.debug('Tag: Test Debug')
    Logger.info('Tag: Test Info')
    Logger.warning('Tag: Test Warning')
    Logger.error('Tag: Test Error')

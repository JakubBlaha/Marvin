import os, sys
import shutil


class LoggerMeta(type):
    LOG_DIR = 'logs'
    MAX_LOG_FILE_COUNT = 10

    client = None
    log_channel = None

    def __init__(cls, *args, **kw):
        super().__init__(*args, **kw)

        cls.terminal = sys.stdout

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

        cls.log = open(os.path.join(cls.LOG_DIR, cls.fname), 'w')

        cls.info(f'Logger: Purged `{cls.LOG_DIR}`')

    def _ensure_dir(cls):
        os.makedirs(cls.LOG_DIR, exist_ok=True)

    def __del__(cls):
        cls.flush()
        cls.log.close()
        sys.stdout = cls.terminal

    def _log(cls, level, string):
        if not ':' in string:
            string = ':' + string

        category, message = [i.strip() for i in string.split(':', 1)]
        _string = f'[{level.ljust(8)}] [{category.ljust(8)}] {message}'
        print(_string)

    async def _alog(cls, string):
        # return if string empty
        if not string.strip():
            return

        # search for corresponding channel
        for ch in cls.client.get_all_channels():
            if ch.name == cls.log_channel:
                break
        else:
            return

        # actual log
        await ch.send(f'```python\n{string}```')

    def debug(cls, msg):
        cls._log('DEBUG', msg)

    def info(cls, msg):
        cls._log('INFO', msg)

    def warning(cls, msg):
        cls._log('WARNING', msg)

    def error(cls, msg):
        cls._log('ERROR', msg)

    def write(cls, msg):
        cls.terminal.write(msg)
        cls.log.write(msg)
        cls.log.flush()

        # write to discord logs channel
        if cls.client:
            cls.client.loop.create_task(cls._alog(msg))

    def flush(cls):
        cls.terminal.flush()
        cls.log.flush()

    def get_log(cls):
        with open(os.path.join(cls.LOG_DIR, cls.fname)) as f:
            return f.read()


class Logger(metaclass=LoggerMeta):
    pass

from typing import Callable
from time import time


DEFAULT_EXPIRE_TIME = 600  # 10 minutes


class EmptyOutput:
    pass


class Cacher:
    ''' Cache the output of a function. '''

    _expire_time: int
    _func: Callable
    _args: tuple
    _kw: dict

    _cached_output = EmptyOutput()
    _last_cached_timestamp = 0

    def __init__(self,
                 func: Callable,
                 args: tuple = (),
                 kw: dict = {},
                 expire_time: int = DEFAULT_EXPIRE_TIME):
        self._expire_time = expire_time
        self._func = func
        self._args = args
        self._kw = kw

    @property
    def output(self):
        # Call for the first time
        if isinstance(self._cached_output, EmptyOutput):
            self.call()

        # Time difference unacceptable
        if (time() - self._last_cached_timestamp) > self._expire_time:
            self.call()

        return self._cached_output

    def call(self, *args, **kw):
        '''
        Call the function. If no args or kwargs are given, use the ones that
        were specified on instantiation. Cache the output. Return the output.
        '''

        if not (args and kw):
            args = self._args
            kw = self._kw

        self._cached_output = self._func(*args, **kw)
        self._last_cached_timestamp = time()

        return self._cached_output


if __name__ == "__main__":
    _timecacher = Cacher(time, expire_time=3)
    assert isinstance(_timecacher._cached_output, EmptyOutput)
    
    _output = _timecacher.output
    assert isinstance(_output, float)
    
    from time import sleep
    sleep(1)
    assert _timecacher.output == _output
    sleep(2)
    assert _timecacher.output != _output

    _output = _timecacher.output
    sleep(.1)
    assert _timecacher.call() != _output

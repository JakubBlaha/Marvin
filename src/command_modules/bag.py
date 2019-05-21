from csv import reader
from datetime import datetime


RES_FNAME = 'command_modules/res/rozvrh.csv'


def get_data() -> list:
    with open(RES_FNAME, encoding='utf-8') as f:
        return list(reader(f))


def get_out_in(data: list) -> list:
    # Get the weekday
    _wday = datetime.today().weekday()

    # Get the subjects
    _today = set(data[_wday])
    _tomorrow = set(data[(_wday + 1) % 7])

    # Process the subjects
    _out = _today - _tomorrow
    _in = _tomorrow - _today

    return [_out, _in]


def build_string(out_in: list) -> str:
    _out_str = ', '.join(f'*{i}*' for i in out_in[0])
    _in_str = ', '.join(f'*{i}*' for i in out_in[1])

    return f'**Out:** {_out_str}\n**In:** {_in_str}'


if __name__ == "__main__":
    print(build_string(get_out_in(get_data())))
from csv import reader

from utils.relevant_day import relevant_weekday_index

RES_FNAME = 'command_modules/res/rozvrh.csv'


def get_data() -> list:
    with open(RES_FNAME, encoding='utf-8') as f:
        return list(reader(f))


def round_day(i: int, step: int) -> int:
    while i in (5, 6):
        i = (i + step) % 7

    return i % 7


def get_out_in(data: list) -> list:
    # Get the weekday
    _wday = round_day(relevant_weekday_index() - 1, -1)
    _wday_next = round_day(_wday + 1, 1)

    # Get the subjects
    _last_day = set(data[_wday])
    _next_day = set(data[_wday_next])

    # Get the difference
    _out = _last_day - _next_day
    _in = _next_day - _last_day

    return [_out, _in]


def build_string(out_in: list) -> str:
    _out_str = ', '.join(f'*{i}*' for i in out_in[0])
    _in_str = ', '.join(f'*{i}*' for i in out_in[1])

    return f'**Out:** {_out_str}\n**In:** {_in_str}'


if __name__ == "__main__":
    print(build_string(get_out_in(get_data())))

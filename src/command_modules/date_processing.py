import yaml
import os
from datetime import datetime, MAXYEAR

DATA_PATH = os.path.abspath(
    os.path.join(__file__, os.pardir, 'res/date_locals.yaml'))
FUTURE = datetime(MAXYEAR, 1, 1)

with open(DATA_PATH, encoding='utf-8') as f:
    DATA: dict = yaml.safe_load(f)


def _get_day_month(date: str) -> tuple:
    day, month, *_ = [*date.split('.'), '', '']

    day = day.strip()
    month = month.strip()

    return (day, month)


# def is_date_valid(date: str) -> bool:
#     day, month = _get_day_month(date)

#     if not day.isdigit():
#         return False

#     if month.isdigit() and 0 < int(month) < 13:
#         return True

#     return month.lower() in [
#         i for j in DATA[DESIRED_LOCALE].values() for i in j
#     ]


def str_to_datetime(date: str, invalid=FUTURE) -> datetime:
    '''
    Return a datetime object made from the given string. If the string has an
    invalid format, return the object passed to the invalid parameter. Default
    invalid is FUTURE.
    '''
    day, month = _get_day_month(date)
    year = datetime.now().year

    for loc in DATA.values():
        for key, value in loc.items():
            for i in value:
                month = month.replace(i, str(key))

    if not(month.isdigit() and day.isdigit()):
        return invalid

    return datetime(year, int(month), int(day))

if __name__ == "__main__":
    _test_dates = ['6. dubna', '6. 4.']
    for date in _test_dates:
        # print(date, is_date_valid(date))
        print(date, str_to_datetime(date))
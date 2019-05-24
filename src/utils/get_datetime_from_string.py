import re
from datetime import datetime, MAXYEAR

from command_modules.date_processing import str_to_datetime


def get_datetime_from_string(s: str):
    ''' Returns the first datetime found. '''
    match = re.search('\d{1,2}\. ?\w+', s)

    if match:
        return str_to_datetime(match.group(0))
    return datetime(0, 1, 1)
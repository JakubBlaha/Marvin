from csv import reader
from datetime import datetime
import os

TIMETABLE_RELATIVE_PATH = 'res/rozvrh.csv'
TIMETABLE_PATH = os.path.join(
    os.path.dirname(__file__), TIMETABLE_RELATIVE_PATH)
DAYS = ['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne']

with open(TIMETABLE_PATH, encoding='utf-8') as f:
    TIMETABLE = list(reader(f))


def get_subjects() -> str:
    day_index = datetime.today().weekday()
    day_index = (day_index + (datetime.now().hour > 12)) % 7

    subjs = sorted(list(set(TIMETABLE[day_index]) - set('-')))
    return f'{DAYS[day_index]}: {", ".join(subjs)}'


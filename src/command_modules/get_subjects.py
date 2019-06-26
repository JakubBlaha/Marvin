from csv import reader
from datetime import datetime
import os

from utils.relevant_day import relevant_weekday_index

TIMETABLE_RELATIVE_PATH = 'res/rozvrh.csv'
TIMETABLE_PATH = os.path.join(
    os.path.dirname(__file__), TIMETABLE_RELATIVE_PATH)
DAYS = ['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne']

with open(TIMETABLE_PATH, encoding='utf-8') as f:
    TIMETABLE = list(reader(f))


def get_subjects() -> str:
    day_index = relevant_weekday_index() % 7

    subjs = sorted(list(set(TIMETABLE[day_index]) - set('-')))
    return f'{DAYS[day_index]}: {", ".join(subjs)}'

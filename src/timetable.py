from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple, Optional


@dataclass
class Subject:
    """
    Represents a subject in the day.

    Attributes:
        cls.abbr: The abbreviation for the subject name.
        cls.name: The full name of the subject.
        cls.raw_time: The raw time string that was used for constructing the object in a format HM
            (e. g. 0905 for 9:05).

    Note that __eq__ and __hash__ functions do not account the starting time so converting to sets can work
    as expected.
    """

    abbr: str
    name: str
    raw_time: str  # Starting time in the format %H%M (e. g. 9:05 would be 0905)

    @property
    def fmt_time(self):
        """ Return the starting time as a string formatted as %H:%M (e.g. 09:05)"""
        return f'{self.raw_time[:2]}:{self.raw_time[2:]}'

    @property
    def timedelta_time(self):
        """ Return the starting time as a timedelta object. """
        dt = datetime.strptime(self.raw_time, '%H%M')
        return timedelta(hours=dt.hour, minutes=dt.minute)

    def __eq__(self, other: Subject):
        return hash(self) == hash(other)

    def __hash__(self):
        return hash((self.abbr, self.name))


class Day:
    """
    Represents a day in the Timetable.

    Attributes:
        subjs: A list of the Subject objects representing different subjects.
    """
    subjs: List[Subject]

    def __init__(self, subjects: List[Tuple[str, str, str]]):
        self.subjs = [Subject(*subj) for subj in subjects]

    def get(self, abbr: Optional[str] = None, name: Optional[str] = None, raw_time: Optional[str] = None):
        """
        Return the first subject from the day which accomplishes all the requirements. If any of the parameters is
        omitted, the parameter will be considered as unimportant.

        :param abbr: The abbreviation of the name of the subject.
        :param name: The long name of the subject.
        :param raw_time: The raw time (e. g. 0905 for 9:05).
        :return: The first matching subject.
        """

        for subj in self.subjs:
            if all([
                subj.abbr == abbr or not abbr,
                subj.name == name or not name,
                subj.raw_time == raw_time or not raw_time
            ]):
                return subj

    @property
    def without_dupes(self) -> Day:
        """ Return a new Day object, but without duplicated subjects. """
        return Day(list(map(lambda x: (x.abbr, x.name, x.raw_time), dict.fromkeys(self.subjs))))

    def __getitem__(self, item: int):
        """ Return the corresponding Subject object. """
        return self.subjs[item]

    def __iter__(self) -> Subject:
        yield from self.subjs


class Timetable:
    """
    Represents a timetable.

    Attributes:
        days: A list of Day objects representing different days.
    """

    days: List[Day] = []

    def __init__(self, data: List[List[Tuple[str, str, str]]]):
        """
        Build an instance from the given data. The data should be in the following format.
        days[subjects[abbreviation, full name, starting time e. g. 0905 for 9:05]]
        """

        data = (data + [[]] * 7)[:7]  # Make sure the data is at least 7 empty days long.
        self.days = [Day(day) for day in data]

    def __getitem__(self, item: int) -> Day:
        """ Return the corresponding Day object. """
        return self.days[item]

    def __iter__(self) -> Day:
        yield from self.days

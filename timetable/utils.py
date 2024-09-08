from __future__ import annotations

import collections
import dataclasses
import datetime
import logging
import re
import time
import typing

import icalendar
import orjson

from timetable import api as api_
from timetable import models

logger = logging.getLogger(__name__)

ORDER: typing.Final[str] = "BG123456789"
SEMESTER_CODE = re.compile(r"[\[\(][0-2F,]+[\]\)]")
SMALL_WORDS = re.compile(
    r"\b(a|an|and|at|but|by|de|en|for|if|in|of|on|or|the|to|via|vs?\.?)\b",
    re.IGNORECASE,
)
INTERNAL_CAPS = re.compile(r"\S+[A-Z]+\S*")
SPLIT_ON_WHITESPACE = re.compile(r"\s+")
SPLIT_ON_HYPHENS = re.compile(r"-")


def parse_weeks(weeks: str) -> list[int]:
    """Parse a weeks string into a list of week numbers."""
    groups = [w.strip() for w in weeks.split(",")]

    final: list[int] = []

    for w in groups:
        w = w.split("-")

        if len(w) == 1:
            final.append(int(w[0]))
        elif len(w) == 2:
            final.extend(list(range(int(w[0]), int(w[1]) + 1)))

    return final


def year_start_end_dates() -> tuple[datetime.datetime, datetime.datetime]:
    """Get default start and end dates for the academic year.

    * Default start date: Sept 1
    * Default end date: May 1

    Returns
    -------
    tuple[datetime.datetime, datetime.datetime]
        The start and end dates.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    start_year = now.year if now.month >= 9 else now.year - 1
    end_year = now.year + 1 if now.month >= 9 else now.year
    start = datetime.datetime(start_year, 9, 1)
    end = datetime.datetime(end_year, 5, 1)
    return (start, end)


@dataclasses.dataclass
class Category:
    name: str
    code: str


@dataclasses.dataclass
class Categories:
    courses: list[Category]
    modules: list[Category]


async def get_basic_category_results(api: api_.API) -> Categories:
    if not (
        courses := await api.get_category_results(
            models.CategoryType.PROGRAMMES_OF_STUDY
        )
    ):
        start = time.time()
        courses = await api.fetch_category_results(
            models.CategoryType.PROGRAMMES_OF_STUDY, cache=True
        )
        logger.info(f"Cached Programmes of Study in {time.time()-start:.2f}s")

    if not (modules := await api.get_category_results(models.CategoryType.MODULES)):
        start = time.time()
        modules = await api.fetch_category_results(
            models.CategoryType.MODULES, cache=True
        )
        logger.info(f"Cached Modules in {time.time()-start:.2f}s")

    return Categories(
        courses=[Category(name=c.name, code=c.code) for c in courses.items],
        modules=[Category(name=m.name, code=m.code) for m in modules.items],
    )


# Converted to python and modified from
# https://github.com/HubSpot/humanize/blob/master/src/humanize.js#L439-L475
def title_case(text: str):
    def do_title_case(_text: str, hyphenated: bool = False, first_or_last: bool = True):
        title_cased_array: list[str] = []
        string_array = re.split(
            SPLIT_ON_HYPHENS if hyphenated else SPLIT_ON_WHITESPACE, _text
        )

        for index, word in enumerate(string_array):
            if "-" in word:
                title_cased_array.append(
                    do_title_case(
                        word, True, index == 0 or index == len(string_array) - 1
                    )
                )
                continue

            if first_or_last and (index == 0 or index == len(string_array) - 1):
                title_cased_array.append(
                    word.capitalize() if not INTERNAL_CAPS.search(word) else word
                )
                continue

            if INTERNAL_CAPS.search(word):
                title_cased_array.append(word)
            elif SMALL_WORDS.search(word):
                title_cased_array.append(word.lower())
            else:
                title_cased_array.append(word.capitalize())

        return (
            "-".join(title_cased_array) if hyphenated else " ".join(title_cased_array)
        )

    return do_title_case(text)


@dataclasses.dataclass
class EventDisplayData:
    """Display data for events."""

    summary: str
    """Short summary of this event."""
    summary_long: str
    """Long summary of this event."""
    location: str
    """Long location(s) of this event."""
    location_long: str
    """Location(s) of this event."""
    description: str
    """Description of this event."""
    original_event: models.Event
    """The original event for the display data."""

    def to_full_event_dict(self) -> dict[str, typing.Any]:
        data = dataclasses.asdict(self.original_event)
        data["display"] = dataclasses.asdict(self)
        data["display"].pop("original_event")
        return data

    @classmethod
    def from_events(cls, events: list[models.Event]) -> list[typing.Self]:
        return [cls.from_event(event) for event in events]

    @classmethod
    def from_event(cls, event: models.Event) -> typing.Self:
        # SUMMARY

        name = (
            re.sub(SEMESTER_CODE, "", n, 1) if (n := event.module_name) else event.name
        )

        if event.description and event.description.lower().strip() == "lab":
            activity = "Lab"
        elif event.parsed_name_data:
            activity = event.parsed_name_data[0].activity_type.display()
        else:
            activity = ""

        if activity and event.group_name:
            summary_long = f"({activity}, Group {event.group_name})"
        elif activity:
            summary_long = f"({activity})"
        elif event.group_name:
            summary_long = f"(Group {event.group_name})"
        else:
            summary_long = ""

        summary_long = title_case(
            (name + (f" {summary_long}" if summary_long else "")).strip()
        )
        summary_short = title_case(name)

        # LOCATIONS

        if event.locations:
            # dict[(campus, building)] = [locations]
            locations: dict[tuple[str, str], list[models.Location]] = (
                collections.defaultdict(list)
            )

            for loc in event.locations:
                locations[(loc.campus, loc.building)].append(loc)

            locations_long: list[str] = []
            locations_short: list[str] = []
            for (campus, building), locs_ in locations.items():
                building = models.BUILDINGS[campus][building]
                campus = models.CAMPUSES[campus]
                locs_ = sorted(locs_, key=lambda r: r.room)
                locs_ = sorted(locs_, key=lambda r: ORDER.index(r.floor))
                locations_long.append(
                    f"{', '.join((f"{loc.building}{loc.floor}{loc.room}" for loc in locs_))} ({building}, {campus})"
                )
                locations_short.append(
                    f"{', '.join((f"{loc.building}{loc.floor}{loc.room}" for loc in locs_))}"
                )

            location_long = ", ".join(locations_long)
            location_short = ", ".join(locations_short)
        else:
            location_long = event.event_type
            location_short = event.event_type

        # DESCRIPTION

        if not activity:
            description = event.description
        elif (
            activity
            and event.description
            and event.description.lower() != activity.lower()
        ):
            description = f"{event.description}, {activity}"
        else:
            description = activity

        event_type = (
            data[0].delivery_type.display()
            if (data := event.parsed_name_data)
            else event.event_type
        )
        description = f"{f'{activity}, ' if activity else ''}{event_type}"

        return cls(
            summary=summary_short,
            summary_long=summary_long,
            location=location_short,
            location_long=location_long,
            description=description,
            original_event=event,
        )


def generate_ical_file(events: list[models.Event]) -> bytes:
    display_data = EventDisplayData.from_events(events)

    calendar = icalendar.Calendar()
    calendar.add("METHOD", "PUBLISH")
    calendar.add("PRODID", "-//nova@redbrick.dcu.ie//TimetableSync//EN")
    calendar.add("VERSION", "2.0")

    for item in display_data:
        event = icalendar.Event()
        event.add("UID", item.original_event.identity)
        event.add("LAST-MODIFIED", item.original_event.last_modified)
        event.add("DTSTART", item.original_event.start)
        event.add("DTEND", item.original_event.end)
        event.add("SUMMARY", item.summary_long)
        event.add("DESCRIPTION", item.description)
        event.add("LOCATION", item.location_long)
        event.add("CLASS", "PUBLIC")
        calendar.add_component(event)

    return calendar.to_ical()


def generate_json_file(
    events: list[models.Event], display: bool | None = None
) -> bytes:
    if not display:
        return orjson.dumps(events)

    display_data = EventDisplayData.from_events(events)
    return orjson.dumps([event.to_full_event_dict() for event in display_data])

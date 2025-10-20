from __future__ import annotations

import collections
import dataclasses
import datetime
import logging
import re
import typing

import icalendar
import orjson

from timetable import __version__, models
from timetable.types import is_str_list

if typing.TYPE_CHECKING:
    from timetable import api as api_


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


def default_year_start_end_dates() -> tuple[datetime.datetime, datetime.datetime]:
    """Get default start and end dates for the academic year.

    * Default start date: Aug 1
    * Default end date: May 1

    Returns
    -------
    tuple[datetime.datetime, datetime.datetime]
        The start and end dates.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    start_year = now.year if now.month >= 8 else now.year - 1
    end_year = now.year + 1 if now.month >= 8 else now.year
    start = datetime.datetime(start_year, 8, 1, tzinfo=datetime.timezone.utc)
    end = datetime.datetime(end_year, 5, 1, tzinfo=datetime.timezone.utc)
    return (start, end)


def calc_start_end_range(
    start: datetime.datetime | None = None, end: datetime.datetime | None = None
) -> tuple[datetime.datetime, datetime.datetime]:
    start_default, end_default = default_year_start_end_dates()
    start = (start or start_default).astimezone(datetime.UTC)
    end = (end or end_default).astimezone(datetime.UTC)

    # TODO: is this warning necessary?
    if not (start_default <= start <= end_default) or not (
        start_default <= end <= end_default
    ):
        logger.warning(
            f"{start} and {end} datetimes not within the current academic year range"
        )

    # TODO: set end to start + 1 week if end before start
    if start > end:
        raise ValueError("Start date/time cannot be later than end date/time")

    return start, end


@dataclasses.dataclass
class Category:
    name: str
    identity: str


async def get_basic_category_results(
    api: api_.API,
    category_type: models.CategoryType,
    query: str | None = None,
) -> list[Category]:
    result = await api.get_category(category_type, query=query)
    if not result:
        result = await api.fetch_category(category_type, query=query, cache=True)

    return [Category(name=c.name, identity=c.identity) for c in result.items]


async def resolve_to_category_items(
    original_codes: dict[models.CategoryType, list[str]],
    api: api_.API,
) -> dict[models.CategoryType, list[models.CategoryItem]]:
    codes: dict[models.CategoryType, list[models.CategoryItem]] = (
        collections.defaultdict(list)
    )

    for group, cat_codes in original_codes.items():
        for code in cat_codes:
            # code is a category item identity and timetable must be fetched
            item = await api.get_category_item(group, code)
            if item:
                codes[group].append(item)
                continue

            # code is not a category item, search cached category items for it
            category = await api.get_category(group, query=code, count=1)
            if not category or not category.items:
                # could not find category item in cache, fetch it
                category = await api.fetch_category(group, query=code)
                if not category.items:
                    raise models.InvalidCodeError(code)

            item = category.items[0]
            codes[group].append(item)

    return codes


async def gather_events(
    group_identities: dict[models.CategoryType, list[str]],
    start_date: datetime.datetime | None,
    end_date: datetime.datetime | None,
    api: api_.API,
) -> list[models.Event]:
    events: list[models.Event] = []

    for group, identities in group_identities.items():
        for identity in identities:
            # timetable is cached
            timetable = await api.get_category_item_timetable(
                group.value, identity, start=start_date, end=end_date
            )
            if timetable:
                events.extend(timetable.events)
                continue

            # timetable needs to be fetched
            timetables = await api.fetch_category_items_timetables(
                group,
                [identity],
                start=start_date,
                end=end_date,
            )
            # no timetables may be returned
            if timetables:
                events.extend(timetables[0].events)

    return events


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


# TODO: rework this to be an optional attribute of the `Event` class
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

        name = re.sub(SEMESTER_CODE, "", n) if (n := event.module_name) else event.name

        if event.description and event.description.lower().strip() == "lab":
            activity = "Lab"
        elif event.parsed_name_data:
            activity = event.parsed_name_data[0].activity_type.display
        else:
            activity = None

        if activity and event.group_name:
            summary_long = f"({activity}, Group {event.group_name})"
        elif activity:
            summary_long = f"({activity})"
        elif event.group_name:
            summary_long = f"(Group {event.group_name})"
        else:
            summary_long = None

        summary_long = title_case(
            (name + (f" {summary_long}" if summary_long else "")).strip()
        )
        summary_short = title_case(name)
        if event.group_name:
            summary_short = f"{summary_short} (Group {event.group_name})".strip()

        # LOCATIONS

        if event.locations:
            # dict[(campus, building)] = [locations]
            locations: dict[tuple[str, str] | None, list[models.Location]] = (
                collections.defaultdict(list)
            )

            for loc in event.locations:
                if loc.original is not None:
                    locations[None].append(loc)
                else:
                    locations[(loc.campus, loc.building)].append(loc)

            locations_long: list[str] = []
            locations_short: list[str] = []
            for main, locs in locations.items():
                if main is None:
                    locs_ = [loc.original for loc in locs]
                    assert is_str_list(locs_)
                    loc_string = ", ".join(locs_)
                    locations_long.append(loc_string)
                    locations_short.append(loc_string)
                    continue

                campus, building = main
                building = models.BUILDINGS[campus].get(building, "[unknown]")
                campus = models.CAMPUSES[campus]
                locs = sorted(locs, key=lambda r: r.room)
                locs = sorted(locs, key=lambda r: ORDER.index(r.floor))
                locations_long.append(
                    f"{', '.join((f'{loc.building}{loc.floor}{loc.room}' for loc in locs))} ({building}, {campus})"
                )
                locations_short.append(
                    f"{', '.join((f'{loc.building}{loc.floor}{loc.room}' for loc in locs))}"
                )

            location_long = ", ".join(locations_long)
            location_short = ", ".join(locations_short)
        else:
            location_long = event.event_type
            location_short = event.event_type

        # DESCRIPTION

        event_type = (
            data[0].delivery_type.display
            if (data := event.parsed_name_data) and data[0].delivery_type is not None
            else event.event_type
        )
        if event_type.lower().strip() == "booking":
            description = (
                f"{event.description}, {event_type}"
                if event.description
                else event_type
            )
        else:
            description = f"{activity}, {event_type}" if activity else event_type

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
    calendar.add(
        "PRODID", f"-//timetable.redbrick.dcu.ie//TimetableSync {__version__}//EN"
    )
    calendar.add("VERSION", "2.0")
    calendar.add("DTSTAMP", datetime.datetime.now(datetime.timezone.utc))

    for item in display_data:
        event = icalendar.Event()
        event.add("UID", item.original_event.identity)
        event.add("LAST-MODIFIED", item.original_event.last_modified)
        event.add("DTSTART", item.original_event.start)
        event.add("DTEND", item.original_event.end)
        event.add("DTSTAMP", item.original_event.last_modified)
        event.add("SUMMARY", item.summary_long)
        event.add(
            "DESCRIPTION",
            f"Details: {item.description}\nStaff: {item.original_event.staff_member}",
        )
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

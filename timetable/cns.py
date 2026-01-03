import dataclasses
import datetime
import enum
import os
import typing
import uuid

import aiohttp
import icalendar
import orjson

from rapidfuzz import fuzz
from rapidfuzz import utils as fuzz_utils

from timetable import __version__, utils


class GroupType(enum.Enum):
    """The group type."""

    CLUB = "club"
    """A club."""
    SOCIETY = "society"
    """A society."""


@dataclasses.dataclass
class Event:
    """An event."""

    name: str
    """The event name."""
    image: str | None
    """The event poster."""
    start: datetime.datetime
    """The event's start time."""
    end: datetime.datetime
    """The event's end time."""
    cost: float
    """The event cost."""
    capacity: int | None
    """The event maximum capacity."""
    type: str
    """The event type. Usually `IN-PERSON` or `VIRTUAL`."""
    location: str | None
    """The event location."""
    description: str
    """The event description."""

    @classmethod
    def from_payload(cls, data: dict[str, typing.Any]) -> typing.Self:
        return cls(
            name=data["name"],
            image=data["image"],
            start=datetime.datetime.fromisoformat(data["start"]),
            end=datetime.datetime.fromisoformat(data["end"]),
            cost=data["cost"],
            capacity=data["capacity"],
            type=data["type"],
            location=data["location"],
            description=data["description"],
        )


@dataclasses.dataclass
class Activity:
    """A weekly activity."""

    name: str
    """The activity name."""
    image: str | None
    """The activity poster."""
    day: str
    """The day the activity is on (`monday`, `tuesday`, etc.)."""
    start: datetime.datetime
    """The activity start time."""
    end: datetime.datetime
    """The activity end time."""
    capacity: int | None
    """The activity maximum capacity."""
    type: str
    """The activity type. Usually `IN-PERSON` or `VIRTUAL`."""
    location: str | None
    """The activity location."""
    description: str
    """The activity description."""

    @classmethod
    def from_payload(cls, data: dict[str, typing.Any]) -> typing.Self:
        return cls(
            name=data["name"],
            image=data["image"],
            day=data["day"],
            start=datetime.datetime.fromisoformat(data["start"]),
            end=datetime.datetime.fromisoformat(data["end"]),
            capacity=data["capacity"],
            type=data["type"],
            location=data["location"],
            description=data["description"],
        )


SITE = "dcuclubsandsocs.ie"


class API:
    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    @property
    def session(self) -> aiohttp.ClientSession:
        """The `aiohttp.ClientSession` to use for API requests."""
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session

    async def get_data(self, url: str) -> list[dict[str, typing.Any]]:
        async with self.session.request(
            "GET", f"{os.environ['CNS_ADDRESS']}/{url}"
        ) as r:
            r.raise_for_status()
            return await r.json(loads=orjson.loads)

    async def fetch_group_events_activities(
        self, id: str, group_type: GroupType
    ) -> list[Activity | Event]:
        events = [
            Event.from_payload(d)
            for d in await self.get_data(f"{SITE}/{group_type.value}/{id}/events")
        ]
        activities = [
            Activity.from_payload(d)
            for d in await self.get_data(f"{SITE}/{group_type.value}/{id}/activities")
        ]

        return events + activities

    async def fetch_group(self, group_type: GroupType) -> list[utils.Category]:
        return [
            utils.Category(name=d["name"], identity=d["id"])
            for d in await self.get_data(f"{SITE}/{group_type.value}")
            if not d["is_locked"]
        ]


def filter_category_results(
    categories: list[utils.Category], query: str
) -> list[utils.Category]:
    results: typing.Iterable[tuple[utils.Category, float]] = []

    for item in categories:
        ratio = fuzz.partial_ratio(
            query, item.name, processor=fuzz_utils.default_process
        )
        results.append((item, ratio))

    results = filter(lambda r: r[1] > 80, results)
    results = sorted(results, key=lambda r: r[1], reverse=True)
    return [r[0] for r in results]


def generate_ical_file(events: list[Event | Activity]) -> bytes:
    calendar = icalendar.Calendar()
    calendar.add("METHOD", "PUBLISH")
    calendar.add(
        "PRODID", f"-//timetable.redbrick.dcu.ie//TimetableSync {__version__}//EN"
    )
    calendar.add("VERSION", "2.0")
    calendar.add("DTSTAMP", datetime.datetime.now(datetime.timezone.utc))

    for item in events:
        event = icalendar.Event()
        event.add("UID", uuid.uuid4())
        event.add("LAST-MODIFIED", item.start)
        event.add("DTSTART", item.start)
        event.add("DTEND", item.end)
        event.add("DTSTAMP", item.start)
        event.add("SUMMARY", item.name)
        event.add(
            "DESCRIPTION",
            f"Details: {item.description}\n"
            + (
                f"Cost: {f'€{item.cost:.2f}' if item.cost else 'FREE'}"
                if isinstance(item, Event)
                else ""
            ),
        )
        event.add("LOCATION", item.location)
        event.add("CLASS", "PUBLIC")
        calendar.add_component(event)

    return calendar.to_ical()

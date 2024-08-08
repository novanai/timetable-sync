from __future__ import annotations

import collections
import dataclasses
import datetime
import re
import typing

import icalendar
import orjson

from timetable import models

ORDER: str = "BG123456789"
TIME_FORMAT: str = "%Y-%m-%dT%H:%M:%SZ"


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


def to_isoformat(text: str) -> datetime.datetime | None:
    """Parse a string to a datetime object, returning None upon failure."""
    try:
        return datetime.datetime.fromisoformat(text)
    except ValueError:
        return None

def year_start_end_dates() -> tuple[datetime.datetime, datetime.datetime]:
    now = datetime.datetime.now(datetime.timezone.utc)
    start_year = now.year if now.month >= 9 else now.year - 1
    end_year = now.year + 1 if now.month >= 9 else now.year
    start = datetime.datetime(start_year, 9, 1)
    end = datetime.datetime(end_year, 5, 1)
    return (start, end)


@dataclasses.dataclass
class EventDisplayData:
    """Display data for events."""

    identity: str
    """Event identity."""
    generated_at: datetime.datetime
    """Time this event was generated at."""
    last_modified: datetime.datetime
    """Time this event was last modified at."""
    start_time: datetime.datetime
    """Time this event starts at."""
    end_time: datetime.datetime
    """Time this event ends at."""
    summary: str
    """Summary of this event."""
    location: str
    """Location(s) of this event."""
    description: str
    """Description of this event."""

    @classmethod
    def from_events(cls, events: list[models.Event]) -> list[typing.Self]:
        events.sort(key=lambda x: x.start)

        return [cls.from_event(event) for event in events]

    @classmethod
    def from_event(cls, event: models.Event) -> typing.Self:
        # SUMMARY

        # TODO: this regex is not always guaranteed to remove the semester number, as it is
        # not always contained with square brackets, so it must be updated.
        name = re.sub(r"\[.*?\]", "", n) if (n := event.module_name) else event.name

        # TODO: is this first if block strictly necessary, as this will apply to a minimal set of modules (e.g. CA116)?
        if event.description and event.description.lower().strip() == "lab":
            activity = "Lab"
        elif event.parsed_name_data:
            activity = event.parsed_name_data[0].activity_type.display()
        else:
            activity = ""

        if activity and event.group_name:
            summary = f"({activity}, Group {event.group_name})"
        elif activity:
            summary = f"({activity})"
        elif event.group_name:
            summary = f"(Group {event.group_name})"
        else:
            summary = ""

        summary = (name + (f" {summary}" if summary else "")).strip()

        # LOCATIONS

        if event.locations and len(event.locations) > 1:
            locations: dict[tuple[str, str], list[models.Location]] = (
                collections.defaultdict(list)
            )

            for loc in event.locations:
                locations[(loc.campus, loc.building)].append(loc)

            locs: list[str] = []
            for (campus, building), locs_ in locations.items():
                building = models.BUILDINGS[campus][building]
                campus = models.CAMPUSES[campus]
                locs_ = sorted(locs_, key=lambda r: r.room)
                locs_ = sorted(locs_, key=lambda r: ORDER.index(r.floor))
                locs.append(
                    f"{', '.join((str(loc).split('.')[1] for loc in locs_))} ({building}, {campus})"
                )

            final = ", ".join(locs)

            location = final

        elif event.locations:
            loc = event.locations[0]
            building = models.BUILDINGS[loc.campus][loc.building]
            campus = models.CAMPUSES[loc.campus]
            room = str(loc).split(".")[1]
            location = f"{room} ({building}, {campus})"

            if (e := event.event_type).lower().startswith("synchronous"):
                location += f", {e}"
        else:
            location = event.event_type

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

        description = f"{description}, {event_type}"

        return cls(
            event.identity,
            datetime.datetime.now(datetime.UTC),
            event.last_modified.astimezone(datetime.UTC),
            event.start.astimezone(datetime.UTC),
            event.end.astimezone(datetime.UTC),
            summary,
            location,
            description,
        )


def generate_ical_file(events: list[models.Event]) -> bytes:
    display_data = EventDisplayData.from_events(events)

    calendar = icalendar.Calendar()
    calendar.add("METHOD", "PUBLISH")
    calendar.add("PRODID", "-//nova@redbrick.dcu.ie//TimetableSync//EN")
    calendar.add("VERSION", "2.0")

    for item in display_data:
        event = icalendar.Event()
        event.add("UID", item.identity)
        event.add("DTSTAMP", item.generated_at)
        event.add("LAST-MODIFIED", item.last_modified)
        event.add("DTSTART", item.start_time)
        event.add("DTEND", item.end_time)
        event.add("SUMMARY", item.summary)
        event.add("LOCATION", item.location)
        event.add("DESCRIPTION", item.description)
        event.add("CLASS", "PUBLIC")
        calendar.add_component(event)

    return calendar.to_ical()


def generate_json_file(events: list[models.Event]) -> bytes:
    return orjson.dumps(events)

from __future__ import annotations

import dataclasses
import datetime
import re
import typing

import icalendar  # pyright: ignore[reportMissingTypeStubs]
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

        if event.description and event.description.lower().strip() == "lab":
            ac = "Lab"
        elif event.parsed_name_data:
            ac = event.parsed_name_data.activity_type.display()
        else:
            ac = ""

        if ac and event.group_name:
            summary = f"({ac}, Group {event.group_name})"
        elif ac:
            summary = f"({ac})"
        elif event.group_name:
            summary = f"(Group {event.group_name})"
        else:
            summary = ""

        summary = (name + (f" {summary}" if summary else "")).strip()

        # LOCATIONS

        if event.locations and len(event.locations) > 1:
            locations: dict[tuple[str, str], list[models.Location]] = {}

            for loc in event.locations:
                if (loc.campus, loc.building) in locations:
                    locations[(loc.campus, loc.building)].append(loc)
                else:
                    locations[(loc.campus, loc.building)] = [loc]

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
            location = (
                f"{str(loc).split('.')[1]} ({models.BUILDINGS[loc.campus][loc.building]}, {models.CAMPUSES[loc.campus]})"
                + (
                    f", {e}"
                    if (e := event.event_type).lower().startswith("synchronous")
                    else ""
                )
            )
        else:
            location = event.event_type

        # DESCRIPTION

        if not ac:
            description = event.description
        elif ac and event.description and event.description.lower() != ac.lower():
            description = f"{event.description}, {ac}"
        else:
            description = ac

        event_type = (
            data.delivery_type.display()
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

    calendar = icalendar.Calendar()  # pyright: ignore[reportPrivateImportUsage]
    calendar.add("METHOD", "PUBLISH")  # pyright: ignore[reportUnknownMemberType]
    calendar.add(  # pyright: ignore[reportUnknownMemberType]
        "PRODID", "-//nova@redbrick.dcu.ie//TimetableSync//EN"
    )
    calendar.add("VERSION", "2.0")  # pyright: ignore[reportUnknownMemberType]

    for item in display_data:
        event = icalendar.Event()  # pyright: ignore[reportPrivateImportUsage]
        event.add("UID", item.identity)  # pyright: ignore[reportUnknownMemberType]
        event.add(  # pyright: ignore[reportUnknownMemberType]
            "DTSTAMP", item.generated_at
        )
        event.add(  # pyright: ignore[reportUnknownMemberType]
            "LAST-MODIFIED", item.last_modified
        )
        event.add(  # pyright: ignore[reportUnknownMemberType]
            "DTSTART", item.start_time
        )
        event.add("DTEND", item.end_time)  # pyright: ignore[reportUnknownMemberType]
        event.add("SUMMARY", item.summary)  # pyright: ignore[reportUnknownMemberType]
        event.add("LOCATION", item.location)  # pyright: ignore[reportUnknownMemberType]
        event.add(  # pyright: ignore[reportUnknownMemberType]
            "DESCRIPTION", item.description
        )
        event.add("CLASS", "PUBLIC")  # pyright: ignore[reportUnknownMemberType]
        calendar.add_component(event)  # pyright: ignore[reportUnknownMemberType]

    return calendar.to_ical()


def generate_json_file(events: list[models.Event]) -> bytes:
    return orjson.dumps(events)

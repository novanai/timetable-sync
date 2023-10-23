from __future__ import annotations

import dataclasses
import datetime
import re
import typing

import icalendar  # pyright: ignore[reportMissingTypeStubs]

from timetable import models

ORDER: str = "BG123456789"


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

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

@dataclasses.dataclass
class EventDisplayData:
    identity: str
    generated_at: datetime.datetime
    last_modified: datetime.datetime
    start_time: datetime.datetime
    end_time: datetime.datetime
    summary: str
    location: str
    description: str

    def as_dict(self) -> dict[str, str]:
        return {
            "identity": self.identity,
            "generated_at": self.generated_at.strftime(TIME_FORMAT),
            "last_modified": self.last_modified.strftime(TIME_FORMAT),
            "start_time": self.last_modified.strftime(TIME_FORMAT),
            "end_time": self.last_modified.strftime(TIME_FORMAT),
            "summary": self.summary,
            "location": self.location,
            "description": self.description,
        }

    @classmethod
    def from_events(cls, events: list[models.Event]) -> list[typing.Self]:
        events.sort(key=lambda x: x.start)

        final_events: list[typing.Self] = []

        for item in events:
            # SUMMARY
            name = re.sub(r"\[.*?\]", "", n) if (n := item.module_name) else item.name

            if item.description and item.description.lower().strip() == "lab":
                ac = "Lab"
            elif item.activity_type:
                ac = item.activity_type.display()
            else:
                ac = ""

            if ac and (group := item.group) and isinstance(group, str):
                summary = f"({ac}, Group {group})"
            elif ac:
                summary = f"({ac})"
            elif (group := item.group) and isinstance(group, str):
                summary = f"(Group {group})"
            else:
                summary = ""

            summary = (name + (f" {summary}" if summary else "")).strip()

            # LOCATIONS

            if item.locations and len(item.locations) > 1:
                locations: dict[tuple[str, str], list[models.Location]] = {}

                for loc in item.locations:
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
                        f"{', '.join((str(l).split('.')[1] for l in locs_))} ({building}, {campus})"
                    )

                final = ", ".join(locs)

                location = final

            elif item.locations:
                loc = item.locations[0]
                location = (
                    f"{str(loc).split('.')[1]} ({models.BUILDINGS[loc.campus][loc.building]}, {models.CAMPUSES[loc.campus]})"
                    + (
                        f", {e}"
                        if (e := item.event_type).lower().startswith("synchronous")
                        else ""
                    )
                )
            else:
                location = item.event_type

            # DESCRIPTION

            if not ac:
                description = item.description
            elif ac and item.description and item.description.lower() != ac.lower():
                description = f"{item.description}, {ac}"
            else:
                description = ac

            event_type = dt.display() if (dt := item.delivery_type) else item.event_type

            description = f"{description}, {event_type}"

            final_events.append(
                cls(
                    item.identity,
                    datetime.datetime.now(datetime.UTC),
                    item.last_modified.astimezone(datetime.UTC),
                    item.start.astimezone(datetime.UTC),
                    item.end.astimezone(datetime.UTC),
                    summary,
                    location,
                    description,
                )
            )

        return final_events


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
            "DTSTAMP", item.generate_time
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


def generate_json_file(events: list[models.Event]) -> list[dict[str, str]]:
    display_data = EventDisplayData.from_events(events)

    data: list[dict[str, str]] = []

    for item in display_data:
        data.append(item.as_dict())

    return data

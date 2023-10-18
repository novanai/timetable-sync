from __future__ import annotations

import datetime
import json
import os
import re
import typing

import aiofile
import icalendar  # pyright: ignore[reportMissingTypeStubs]

from timetable import models, redis

ORDER: str = "BG123456789"


async def cache_data(filename: str, data: dict[str, typing.Any]) -> None:
    data["CacheTimestamp"] = datetime.datetime.now(datetime.UTC).timestamp()

    conn = redis.RedisConnection.get_connection()
    conn.set(filename, json.dumps(data))

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


def generate_ical_file(events: list[models.Event]) -> bytes:
    events.sort(key=lambda x: x.start)

    calendar = icalendar.Calendar()  # pyright: ignore[reportPrivateImportUsage]
    calendar.add("METHOD", "PUBLISH")  # pyright: ignore[reportUnknownMemberType]
    calendar.add(  # pyright: ignore[reportUnknownMemberType]
        "PRODID", "-//nova@redbrick.dcu.ie//TimetableSync//EN"
    )
    calendar.add("VERSION", "2.0")  # pyright: ignore[reportUnknownMemberType]

    for item in events:
        event = icalendar.Event()  # pyright: ignore[reportPrivateImportUsage]
        event.add("UID", item.identity)  # pyright: ignore[reportUnknownMemberType]
        event.add(  # pyright: ignore[reportUnknownMemberType]
            "DTSTAMP", datetime.datetime.now(datetime.UTC)
        )
        event.add(  # pyright: ignore[reportUnknownMemberType]
            "LAST-MODIFIED", item.last_modified.astimezone(datetime.UTC)
        )
        event.add(  # pyright: ignore[reportUnknownMemberType]
            "DTSTART", item.start.astimezone(datetime.UTC)
        )
        event.add(  # pyright: ignore[reportUnknownMemberType]
            "DTEND", item.end.astimezone(datetime.UTC)
        )

        name = re.sub(r"\[.*?\]", "", n) if (n := item.module_name) else item.name
        # if "lab" in description, then ac = "lab" else "ac" for both summary and description fields

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

        event.add(  # pyright: ignore[reportUnknownMemberType]
            "SUMMARY", (name + (f" {summary}" if summary else "")).strip()
        )

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

            event.add(  # pyright: ignore[reportUnknownMemberType]
                "LOCATION",
                final,
            )
        elif item.locations:
            loc = item.locations[0]
            event.add(  # pyright: ignore[reportUnknownMemberType]
                "LOCATION",
                (
                    f"{str(loc).split('.')[1]} ({models.BUILDINGS[loc.campus][loc.building]}, {models.CAMPUSES[loc.campus]})"
                    + (
                        f", {e}"
                        if (e := item.event_type).lower().startswith("synchronous")
                        else ""
                    )
                ),
            )
        else:
            event.add(  # pyright: ignore[reportUnknownMemberType]
                "LOCATION", item.event_type
            )

        if not ac:
            description = item.description
        elif ac and item.description and item.description.lower() != ac.lower():
            description = f"{item.description}, {ac}"
        else:
            description = ac

        event_type = dt.display() if (dt := item.delivery_type) else item.event_type

        event.add(  # pyright: ignore[reportUnknownMemberType]
            "DESCRIPTION", f"{description}, {event_type}"
        )
        event.add("CLASS", "PUBLIC")  # pyright: ignore[reportUnknownMemberType]
        calendar.add_component(event)  # pyright: ignore[reportUnknownMemberType]

    return calendar.to_ical()

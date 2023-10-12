from __future__ import annotations

import datetime
import json
import os
import typing

import aiofile
import icalendar  # pyright: ignore[reportMissingTypeStubs]

from timetable import models


async def cache_data(filename: str, data: dict[str, typing.Any]) -> None:
    data["CacheTimestamp"] = datetime.datetime.now(datetime.UTC).timestamp()

    if not os.path.exists("./cache/"):
        os.mkdir("./cache/")

    async with aiofile.async_open(f"./cache/{filename}.json", "w") as f:
        await f.write(json.dumps(data, indent=4))


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
    calendar.add("METHOD", "PUBLISH")
    calendar.add("PRODID", "-//nova@redbrick.dcu.ie//TimetableSync//EN")
    calendar.add("VERSION", "2.0")

    for item in events:
        event = icalendar.Event()  # pyright: ignore[reportPrivateImportUsage]
        event.add("UID", f"{item.identity}")
        event.add("DTSTAMP", datetime.datetime.now(datetime.UTC))
        event.add("LAST-MODIFIED", item.last_modified.astimezone(datetime.UTC))
        event.add("DTSTART", item.start.astimezone(datetime.UTC))
        event.add("DTEND", item.end.astimezone(datetime.UTC))

        name = item.module_name or item.name
        event.add(
            "SUMMARY",
            name + (f" ({ac.display()})" if (ac := item.activity_type) else ""),
        )

        if item.locations and len(item.locations) > 1:
            locations: dict[tuple[str, str], list[str]] = {}

            for loc in item.locations:
                room = str(loc).split(".")[1]

                if (loc.campus, loc.building) in locations:
                    locations[(loc.campus, loc.building)].append(room)
                else:
                    locations[(loc.campus, loc.building)] = [room]

            locs: list[str] = []
            for (campus, building), rooms in locations.items():
                building = models.BUILDINGS[campus][building]
                campus = models.CAMPUSES[campus]
                locs.append(f"{', '.join(rooms)} ({building}, {campus})")

            final = ", ".join(locs)

            event.add(
                "LOCATION",
                final,
            )
        elif item.locations:
            loc = item.locations[0]
            event.add(
                "LOCATION",
                f"{str(loc).split('.')[1]} ({models.BUILDINGS[loc.campus][loc.building]}, {models.CAMPUSES[loc.campus]})",
            )
        else:
            event.add("LOCATION", item.event_type)

        if not item.activity_type:
            description = item.description
        elif (
            item.activity_type
            and item.description
            and item.description.lower() != item.activity_type.display().lower()
        ):
            description = f"{item.description}, {item.activity_type.display()}"
        else:
            description = item.activity_type.display()

        event_type = dt.display() if (dt := item.delivery_type) else item.event_type

        event.add("DESCRIPTION", f"{description}, {event_type}")
        event.add("CLASS", "PUBLIC")
        calendar.add_component(event)

    return calendar.to_ical()

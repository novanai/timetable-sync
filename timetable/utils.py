from __future__ import annotations

import datetime
import json
import os
import typing

import aiofile
import icalendar

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


def generate_ical_file(timetable: models.CategoryTimetable) -> bytes:
    events = timetable.events
    events.sort(key=lambda x: x.start)

    calendar = icalendar.Calendar()  # pyright: ignore[reportPrivateImportUsage]
    calendar.add("METHOD", "PUBLISH")
    calendar.add("PRODID", "-//-//DCU Timetables Reader//EN")
    calendar.add("VERSION", "2.0")

    for i, item in enumerate(events, start=1):
        event = icalendar.Event()  # pyright: ignore[reportPrivateImportUsage]
        event.add("UID", f"{item.identity}")
        event.add("DTSTAMP", datetime.datetime.now(datetime.UTC))
        event.add("LAST-MODIFIED", item.last_modified.astimezone(datetime.UTC))
        event.add("DTSTART", item.start.astimezone(datetime.UTC))
        event.add("DTEND", item.end.astimezone(datetime.UTC))
        event.add(
            "SUMMARY",
            (item.module_name if item.module_name else item.name)
            # + f" {item.description}"
            # + " "
            # + f"({item.locations[0]})" if item.locations else ""
        )  # "[CA116] Computer Programming Lecture (HG20)"
        if item.locations:
            event.add(
                "LOCATION",
                ", ".join(str(loc).split(".")[1] for loc in item.locations)
                + f" ({models.BUILDINGS[item.locations[0].campus][item.locations[0].building]}"
                + f", {models.CAMPUSES[item.locations[0].campus]})",
            )
        else:
            event.add("LOCATION", item.event_type)
        event.add(
            "DESCRIPTION",
            f"{item.description}, {item.event_type}"
            # + (
            #     f" - {', '.join(str(loc).split('.')[1] for loc in item.locations)}"
            #     if item.locations else ""
            # )
        )
        event.add("CLASS", "PUBLIC")
        calendar.add_component(event)

    return calendar.to_ical()

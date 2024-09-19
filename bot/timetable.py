import datetime
import itertools

import arc
import hikari
import human_readable
import parsedatetime

from timetable import api as api_
from timetable import models, utils

from bot import autocomplete

plugin = arc.GatewayPlugin("timetable")


PARSE_RESULT: dict[int, str] = {
    0: "none",
    1: "date",
    2: "time",
    3: "datetime",
}


@plugin.inject_dependencies
def str_to_datetime(
    text: str, include_day: bool = False, parser: parsedatetime.Calendar = arc.inject()
) -> tuple[str, datetime.datetime] | None:
    time, result = parser.parseDT(text)
    assert isinstance(time, datetime.datetime)

    if isinstance(result, parsedatetime.pdtContext):
        result = result.dateTimeFlag

    time_period = PARSE_RESULT[result]

    if time_period == "none":
        return None

    if time_period == "date":
        name = time.strftime("%A %d %b")
        time = time.replace(hour=0, minute=0, second=0, microsecond=0)
        if include_day:
            time += datetime.timedelta(days=1)
    else:
        name = time.strftime("%H:%M %A %d %b")

    relative = human_readable.day(time.date(), formatting="")
    if relative:
        name += f" ({relative})"

    return name, time


async def datetime_autocomplete(
    data: arc.AutocompleteData[arc.GatewayClient, str],
) -> dict[str, str]:
    if not (data.focused_option and data.focused_value):
        return {}

    values = str_to_datetime(data.focused_value)
    if not values:
        return {}

    name, time = values

    return {name: time.isoformat()}


@plugin.include
@arc.slash_command("timetable", "description")
async def plugin_cmd(
    ctx: arc.GatewayContext,
    course: arc.Option[
        str | None,
        arc.StrParams(
            "The course to fetch a timetable for.", autocomplete_with=autocomplete.search_categories
        ),
    ] = None,
    module: arc.Option[
        str | None,
        arc.StrParams(
            "The module to fetch a timetable for.", autocomplete_with=autocomplete.search_categories
        ),
    ] = None,
    start: arc.Option[
        str | None,
        arc.StrParams(
            "The start time of events to fetch.",
            autocomplete_with=datetime_autocomplete,
        ),
    ] = None,
    end: arc.Option[
        str | None,
        arc.StrParams(
            "The end time of events to fetch.", autocomplete_with=datetime_autocomplete
        ),
    ] = None,
    range_: arc.Option[
        str | None,
        arc.StrParams(
            "The time range of events to fetch (default 'day').", name="range", choices=["day", "week"],
        ),
    ] = None,
    api: api_.API = arc.inject(),
) -> None:
    if start:
        try:
            start_date = datetime.datetime.fromisoformat(start)
        except ValueError:
            date = str_to_datetime(start)
            start_date = date[1] if date else None
    else:
        start_date = datetime.datetime.now(datetime.timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    if start_date is None:
        await ctx.respond("Invalid start time.", flags=hikari.MessageFlag.EPHEMERAL)
        return

    if end:
        try:
            end_date = datetime.datetime.fromisoformat(end)
        except ValueError:
            date = str_to_datetime(end, include_day=True)
            end_date = date[1] if date else None
    elif range_ and range_ == "week":
        end_date = start_date + datetime.timedelta(weeks=1)
    else:
        end_date = start_date + datetime.timedelta(days=1)

    if end_date is None:
        await ctx.respond("Invalid end time.", flags=hikari.MessageFlag.EPHEMERAL)
        return

    if end_date < start_date:
        await ctx.respond(
            "End time cannot be earlier than start time.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        return

    events: list[utils.EventDisplayData] = []

    if course:
        course_events = await api.gather_events_for_courses(
            [course], start_date, end_date
        )
        events.extend(utils.EventDisplayData.from_events(course_events))
    if module:
        module_events = await api.gather_events_for_modules(
            [module], start_date, end_date
        )
        events.extend(utils.EventDisplayData.from_events(module_events))

    if not events:
        await ctx.respond(
            "No events for this time period.", flags=hikari.MessageFlag.EPHEMERAL
        )
        return

    await ctx.respond(embed=format_events(events))


def format_events(events: list[utils.EventDisplayData]) -> hikari.Embed:
    embed = hikari.Embed()

    for date, events_ in itertools.groupby(
        sorted(events, key=lambda e: e.original_event.start),
        key=lambda e: e.original_event.start.date(),
    ):
        formatted_events = [
            (
                f"> {e.summary}\n> 🕑 <t:{int(e.original_event.start.timestamp())}:t>"
                f"-<t:{int(e.original_event.end.timestamp())}:t> 📍 {e.location}"
            )
            for e in sorted(events_, key=lambda e: e.original_event.start)
        ]
        embed.add_field(date.strftime("%A %d %b"), "\n\n".join(formatted_events))

    return embed


@arc.loader
def loader(client: arc.GatewayClient) -> None:
    client.add_plugin(plugin)

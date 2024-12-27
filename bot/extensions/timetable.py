import datetime
import enum
import itertools

import arc
import hikari
import human_readable
import parsedatetime

from bot import autocomplete
from bot.database import Database
from timetable import api as api_
from timetable import models, utils

plugin = arc.GatewayPlugin("timetable")


class TimePeriod(enum.Enum):
    NONE = 0
    DATE = 1
    TIME = 2
    DATETIME = 3


@plugin.inject_dependencies
def str_to_datetime(
    text: str, include_day: bool = False, parser: parsedatetime.Calendar = arc.inject()
) -> tuple[str, datetime.datetime] | None:
    time, result = parser.parseDT(text)
    assert isinstance(time, datetime.datetime)

    if isinstance(result, parsedatetime.pdtContext):
        result = result.dateTimeFlag

    time_period = TimePeriod(result)

    if time_period is TimePeriod.NONE:
        return None

    if time_period is TimePeriod.DATE:
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
@arc.slash_command("timetable", "Fetch a timetable.")
async def timetable_cmd(
    ctx: arc.GatewayContext,
    course: arc.Option[
        str | None,
        arc.StrParams(
            "The course to fetch a timetable for.",
            autocomplete_with=autocomplete.search_categories,
        ),
    ] = None,
    module: arc.Option[
        str | None,
        arc.StrParams(
            "The module to fetch a timetable for.",
            autocomplete_with=autocomplete.search_categories,
        ),
    ] = None,
    location: arc.Option[
        str | None,
        arc.StrParams(
            "The location to fetch a timetable for.",
            autocomplete_with=autocomplete.search_categories,
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
            "The time range of events to fetch (default 'day').",
            name="range",
            choices=["day", "week"],
        ),
    ] = None,
    api: api_.API = arc.inject(),
    db: Database = arc.inject(),
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
    elif start and range_ and range_ == "week":
        end_date = start_date + datetime.timedelta(weeks=1)
    elif not start and range_ and range_ == "week":
        now = datetime.datetime.now(datetime.timezone.utc)
        start_date = datetime.datetime(now.year, now.month, now.day - now.weekday())
        end_date = start_date + datetime.timedelta(weeks=1)
    else:
        range_ = "day"
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

    if not (course or module or location):
        async with db.acquire() as conn:
            course_record = await conn.fetchrow(
                "SELECT course_id FROM default_courses WHERE user_id = $1", ctx.user.id
            )
            modules_record = await conn.fetch(
                "SELECT module_id FROM default_modules WHERE user_id = $1", ctx.user.id
            )

        items = await utils.resolve_to_category_items(
            {
                models.CategoryType.PROGRAMMES_OF_STUDY: [course_record["course_id"]]
                if course_record
                else [],
                models.CategoryType.MODULES: [m["module_id"] for m in modules_record],
            },
            api,
        )
    else:
        items = await utils.resolve_to_category_items(
            {
                models.CategoryType.PROGRAMMES_OF_STUDY: [course] if course else [],
                models.CategoryType.MODULES: [module] if module else [],
                models.CategoryType.LOCATIONS: [location] if location else [],
            },
            api,
        )

    identities = {
        group: [item.identity for item in group_items]
        for group, group_items in items.items()
    }

    events = await utils.gather_events(identities, start_date, end_date, api)
    display_events = utils.EventDisplayData.from_events(events)

    if not events:
        if range_ == "week" or range_ is None:
            range_text = f"<t:{int(start_date.timestamp())}:D> to <t:{int(end_date.timestamp())}:D>"
        else:
            assert range_ == "day"
            range_text = f"<t:{int(start_date.timestamp())}:D>"

        await ctx.respond(
            f"No events for {range_text}.", flags=hikari.MessageFlag.EPHEMERAL
        )
        return

    await ctx.respond(embed=format_events(items, display_events))


def format_events(
    items: dict[models.CategoryType, list[models.CategoryItem]],
    events: list[utils.EventDisplayData],
) -> hikari.Embed:
    descriptions = {
        group: [item.name for item in group_items]
        for group, group_items in items.items()
    }
    descriptions_list: list[str] = []
    # TODO: add display property for CategoryType and __iter__ method
    for group, title in (
        (models.CategoryType.PROGRAMMES_OF_STUDY, "Courses"),
        (models.CategoryType.MODULES, "Modules"),
        (models.CategoryType.LOCATIONS, "Locations"),
    ):
        if group in descriptions and descriptions[group]:
            descriptions_list.append(
                f"**{title}:** {", ".join(descriptions[group])}",
            )

    embed = hikari.Embed(description="\n".join(descriptions_list))

    for date, events_ in itertools.groupby(
        sorted(events, key=lambda e: e.original_event.start),
        key=lambda e: e.original_event.start.date(),
    ):
        formatted_events = [
            (
                f"> {e.summary_long}\n> 🕑 <t:{int(e.original_event.start.timestamp())}:t>"
                f"-<t:{int(e.original_event.end.timestamp())}:t> 📍 {e.location}"
            )
            for e in sorted(events_, key=lambda e: e.original_event.start)
        ]
        embed.add_field(date.strftime("%A %d %b"), "\n\n".join(formatted_events))

    return embed


@arc.loader
def loader(client: arc.GatewayClient) -> None:
    client.add_plugin(plugin)

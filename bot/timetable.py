import datetime
import itertools

import arc
import hikari

from timetable import api as api_
from timetable import models, utils

plugin = arc.GatewayPlugin("timetable")


async def search_courses(
    data: arc.AutocompleteData[arc.GatewayClient, str],
) -> dict[str, str]:
    api = plugin.client.get_type_dependency(api_.API)
    if data.focused_value:
        categories = await api.get_category_results(
            models.CategoryType.PROGRAMMES_OF_STUDY, data.focused_value, 10
        )
        if categories is None:
            await utils.get_basic_category_results(api)
            return {}

        return {course.name: course.code for course in categories.items}

    return {}


@plugin.include
@arc.slash_command("timetable", "description")
async def plugin_cmd(
    ctx: arc.GatewayContext,
    course: arc.Option[
        str | None,
        arc.StrParams(
            "The course to fetch a timetable for.", autocomplete_with=search_courses
        ),
    ] = None,
    api: api_.API = arc.inject(),
) -> None:
    today = datetime.datetime.now(datetime.timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week = today + datetime.timedelta(weeks=1)
    if course:
        events = await api.gather_events_for_courses([course], today, week)
        events = utils.EventDisplayData.from_events(events)
    else:
        events = []

    await ctx.respond(embed=format_events(events))


def format_events(events: list[utils.EventDisplayData]) -> hikari.Embed:
    embed = hikari.Embed()

    if not events:
        embed.description = "No events for this time period."
        return embed

    for date, events_ in itertools.groupby(
        sorted(events, key=lambda e: e.original_event.start),
        key=lambda e: e.original_event.start.date(),
    ):
        formatted_events = [
            (
                f"{e.summary}\n🕑 <t:{int(e.original_event.start.timestamp())}:t>"
                f"-<t:{int(e.original_event.end.timestamp())}:t> 📍 {e.location}"
            )
            for e in sorted(events_, key=lambda e: e.original_event.start)
        ]
        embed.add_field(date.strftime("%A %d %b"), "\n\n".join(formatted_events))

    return embed


@arc.loader
def loader(client: arc.GatewayClient) -> None:
    client.add_plugin(plugin)

import arc
from timetable import api as api_
import datetime
import hikari
from timetable import utils
import collections

plugin = arc.GatewayPlugin("timetable")

@plugin.include
@arc.slash_command("timetable", "description")
async def plugin_cmd(
    ctx: arc.GatewayContext,
    course: arc.Option[str | None, arc.StrParams("The course to fetch a timetable for.")] = None,
    api: api_.API = arc.inject()
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

    await ctx.respond(
        embed=format_events(events)
    )
    
def format_events(events: list[utils.EventDisplayData]) -> hikari.Embed:
    embed = hikari.Embed()

    grouped: dict[datetime.date, list[utils.EventDisplayData]] = collections.defaultdict(list)

    for event in events:
        grouped[event.original_event.start.date()].append(event)

    for date in sorted(grouped):
        formatted_events = [
            (
                f"{e.summary}\n🕑 <t:{int(e.original_event.start.timestamp())}:t>-<t:{int(e.original_event.end.timestamp())}:t>"
                f" 📍 {e.location}"
            )
            for e in sorted(grouped[date], key=lambda e: e.original_event.start)
        ]
        embed.add_field(date.strftime("%a %d %b"), "\n\n".join(formatted_events))

    return embed

@arc.loader
def loader(client: arc.GatewayClient) -> None:
    client.add_plugin(plugin)

import arc
from bot import autocomplete
import hikari
import miru
import logging
from timetable import models, api as api_
import asyncpg
import enum


plugin = arc.GatewayPlugin("Preferences")
group = plugin.include_slash_group("preferences", "Edit your preferences.")

class InteractionType(enum.Enum):
    COURSE_UPDATE = "cu"
    MODULE_ADD = "ma"
    MODULE_REMOVE = "mr"

@group.include
@arc.slash_subcommand("course", "Set your default course for the /timetable command.")
async def set_course(
    ctx: arc.GatewayContext,
    api: api_.API = arc.inject(),
    conn: asyncpg.Connection = arc.inject(),
) -> None:
    course: asyncpg.Record | None = await conn.fetchrow("SELECT course_id FROM default_courses WHERE user_id = $1", ctx.user.id)
    modules: list[asyncpg.Record] = await conn.fetch("SELECT module_id FROM default_modules WHERE user_id = $1", ctx.user.id)

    view = miru.View()
    view.add_item(miru.Button(
        label="Update Course",
        custom_id=f"{InteractionType.COURSE_UPDATE.value}-{ctx.user.id}"
    )).add_item(miru.Button(
        label="Add Module",
        custom_id=f"{InteractionType.MODULE_ADD.value}-{ctx.user.id}"
    )).add_item(miru.TextSelect(
        options=[miru.SelectOption("aA")],
        custom_id=f"{InteractionType.MODULE_REMOVE.value}-{ctx.user.id}",
    ))

    await ctx.respond("a", components=view)

@arc.loader
def loader(client: arc.GatewayClient) -> None:
    client.add_plugin(plugin)

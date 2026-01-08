from __future__ import annotations

import enum

import arc
import hikari
import miru

from src.database import Database
from timetable import api as api_
from timetable import models, utils

plugin = arc.GatewayPlugin("Preferences")


class InteractionType(enum.Enum):
    COURSE_SET = "cs"
    COURSE_REMOVE = "cr"
    MODULE_ADD = "ma"
    MODULE_REMOVE = "mr"


@plugin.inject_dependencies
async def build_response(
    user_id: int, api: api_.API = arc.inject(), db: Database = arc.inject()
) -> tuple[hikari.Embed, miru.View]:
    async with db.acquire() as conn:
        course = await conn.fetchrow(
            "SELECT course_id FROM default_courses WHERE user_id = $1", user_id
        )
        modules = await conn.fetch(
            "SELECT module_id FROM default_modules WHERE user_id = $1", user_id
        )

    view = miru.View()

    view.add_item(
        miru.Button(
            label="Set Course",
            custom_id=f"{InteractionType.COURSE_SET.value}-{user_id}",
        )
    )

    if course:
        view.add_item(
            miru.Button(
                label="Remove Course",
                style=hikari.ButtonStyle.DANGER,
                custom_id=f"{InteractionType.COURSE_REMOVE.value}-{user_id}",
            )
        )

    view.add_item(
        miru.Button(
            label="Add Module",
            custom_id=f"{InteractionType.MODULE_ADD.value}-{user_id}",
            disabled=len(modules) >= 12,
        )
    )

    embed_description: list[str] = []

    if course:
        results = await utils.resolve_to_category_items(
            {models.CategoryType.PROGRAMMES_OF_STUDY: [course["course_id"]]}, api
        )
        item = results[models.CategoryType.PROGRAMMES_OF_STUDY][0]
        embed_description.append(f"**Course:** {item.name}")

    if modules:
        results = await utils.resolve_to_category_items(
            {models.CategoryType.MODULES: [record["module_id"] for record in modules]},
            api,
        )
        items = results[models.CategoryType.MODULES]
        view.add_item(
            miru.TextSelect(
                placeholder="Remove modules",
                custom_id=f"{InteractionType.MODULE_REMOVE.value}-{user_id}",
                options=[
                    miru.SelectOption(label=item.name, value=item.identity)
                    for item in items
                ],
            )
        )
        embed_description.append(
            f"**Modules:**\n{"\n".join([f"- {item.name}" for item in items])}"
        )

    embed = hikari.Embed(
        description="\n".join(embed_description)
        if embed_description
        else "No course/modules chosen."
    )

    return embed, view


@plugin.include
@arc.slash_command("preferences", "Edit your preferences for the /timetable command.")
async def set_preferences(
    ctx: arc.GatewayContext,
) -> None:
    embed, view = await build_response(ctx.user.id)

    await ctx.respond(
        embed=embed,
        components=view,
    )


@plugin.listen(hikari.InteractionCreateEvent)
@plugin.inject_dependencies
async def on_interaction(
    event: hikari.InteractionCreateEvent,
    api: api_.API = arc.inject(),
    db: Database = arc.inject(),
) -> None:
    inter = event.interaction

    if not isinstance(inter, (hikari.ComponentInteraction, hikari.ModalInteraction)):
        return

    type_, user_id = inter.custom_id.split("-")
    type_ = InteractionType(type_)
    user_id = int(user_id)

    if user_id != inter.user.id:
        await inter.create_initial_response(
            hikari.ResponseType.MESSAGE_CREATE,
            "You can't click this!",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        return

    update_response: bool = False

    if isinstance(inter, hikari.ComponentInteraction):
        if type_ is InteractionType.COURSE_SET:
            modal = miru.Modal(
                title="Set Course",
                custom_id=f"{InteractionType.COURSE_SET.value}-{inter.user.id}",
            )
            modal.add_item(
                miru.TextInput(
                    label="Course code",
                    placeholder="e.g. COMSCI1",
                    required=True,
                    custom_id="course-value",
                )
            )
            await inter.create_modal_response(
                modal.title,
                modal.custom_id,
                components=modal,
            )

        elif type_ is InteractionType.COURSE_REMOVE:
            async with db.acquire() as conn:
                await conn.execute(
                    "DELETE FROM default_courses WHERE user_id = $1",
                    inter.user.id,
                )

            update_response = True

        elif type_ is InteractionType.MODULE_ADD:
            modal = miru.Modal(
                title="Add Module",
                custom_id=f"{InteractionType.MODULE_ADD.value}-{inter.user.id}",
            )
            modal.add_item(
                miru.TextInput(
                    label="Module code",
                    placeholder="e.g. CSC1003",
                    required=True,
                    custom_id="module-value",
                )
            )
            await inter.create_modal_response(
                modal.title,
                modal.custom_id,
                components=modal,
            )

        elif type_ is InteractionType.MODULE_REMOVE:
            async with db.acquire() as conn:
                await conn.executemany(
                    "DELETE FROM default_modules WHERE user_id = $1 AND module_id = $2",
                    [(inter.user.id, value) for value in inter.values],
                )
            update_response = True

    else:
        value = inter.components[0].components[0].value

        if type_ is InteractionType.COURSE_SET:
            results = await utils.resolve_to_category_items(
                {models.CategoryType.PROGRAMMES_OF_STUDY: [value]}, api
            )
            item = results[models.CategoryType.PROGRAMMES_OF_STUDY][0]

            async with db.acquire() as conn:
                await conn.execute(
                    "INSERT INTO default_courses (user_id, course_id) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET course_id = $2",
                    inter.user.id,
                    item.identity,
                )

            update_response = True

        elif type_ is InteractionType.MODULE_ADD:
            results = await utils.resolve_to_category_items(
                {models.CategoryType.MODULES: [value]}, api
            )
            item = results[models.CategoryType.MODULES][0]

            async with db.acquire() as conn:
                await conn.execute(
                    "INSERT INTO default_modules (user_id, module_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                    inter.user.id,
                    item.identity,
                )

            update_response = True

    if update_response:
        embed, view = await build_response(inter.user.id)
        await inter.create_initial_response(
            hikari.ResponseType.MESSAGE_UPDATE,
            embed=embed,
            components=view,
        )


@arc.loader
def loader(client: arc.GatewayClient) -> None:
    client.add_plugin(plugin)

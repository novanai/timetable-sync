from __future__ import annotations

import asyncio
import datetime
import logging
import os

import arc
import glide
import hikari
import miru
import parsedatetime
from timetable.api import API as TimetableAPI
from timetable.cache import ValkeyCache
from timetable.cns import API as CNSAPI
from timetable.cns import GroupType
from timetable.models import BasicCategoryItem, CategoryType, InvalidCodeError

from src.database import Database

logger = logging.getLogger(__name__)

bot = hikari.GatewayBot(os.environ["BOT_TOKEN"], banner=None)
client = arc.GatewayClient(bot)

client.set_type_dependency(
    parsedatetime.Calendar, parsedatetime.Calendar(parsedatetime.Constants("en_GB"))
)
client.set_type_dependency(
    miru.Client, miru.Client.from_arc(client, ignore_unknown_interactions=True)
)

client.load_extensions_from("src/extensions")


async def load_all_categories_to_cache(
    timetable_api: TimetableAPI, cns_api: CNSAPI
) -> None:
    for category_type in (
        CategoryType.PROGRAMMES_OF_STUDY,
        CategoryType.MODULES,
        CategoryType.LOCATIONS,
    ):
        logger.info(f"loading timetable category '{category_type.name}'")

        if not (
            await timetable_api.get_category(
                category_type, items_type=BasicCategoryItem
            )
        ):
            await timetable_api.fetch_category(
                category_type, items_type=BasicCategoryItem
            )

    logger.info("loaded all timetable categories")

    for group_type in (GroupType.CLUB, GroupType.SOCIETY):
        logger.info(f"loading cns category '{group_type.name}'")

        if not (await cns_api.get_group_items(group_type)):
            await cns_api.fetch_group_items(group_type)

    logger.info("loaded all cns categories")


async def populate_cache(timetable_api: TimetableAPI, cns_api: CNSAPI) -> None:
    client = timetable_api.cache.client

    if await client.exists(["cache_ready"]):
        logger.info("cache ready")
        return

    got_lock = await client.set(
        "cache_loading",
        "1",
        conditional_set=glide.ConditionalChange.ONLY_IF_DOES_NOT_EXIST,
        expiry=glide.ExpirySet(glide.ExpiryType.SEC, datetime.timedelta(seconds=150)),
    )

    if got_lock:
        try:
            await load_all_categories_to_cache(timetable_api, cns_api)
            await client.set(
                "cache_ready",
                "1",
                expiry=glide.ExpirySet(
                    glide.ExpiryType.SEC, datetime.timedelta(days=1)
                ),
            )
        finally:
            await client.delete(["cache_loading"])
        return
    logger.info("waiting for cache")

    while not await client.exists(["cache_ready"]):
        await asyncio.sleep(0.2)

    logger.info("cache ready")


@client.add_startup_hook
@client.inject_dependencies
async def startup_hook(client: arc.GatewayClient) -> None:
    valkey_cache = await ValkeyCache.create(
        os.environ["VALKEY_HOST"], int(os.environ["VALKEY_PORT"])
    )
    timetable_api = TimetableAPI(valkey_cache)
    cns_api = CNSAPI(os.environ["CNS_ADDRESS"], valkey_cache)

    await populate_cache(timetable_api, cns_api)

    client.set_type_dependency(TimetableAPI, timetable_api)
    client.set_type_dependency(CNSAPI, cns_api)

    db = Database(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        database=os.environ["POSTGRES_DB"],
    )
    await db.start()

    client.set_type_dependency(
        Database,
        db,
    )


@bot.listen(hikari.ExceptionEvent)
async def error_handler(event: hikari.ExceptionEvent[hikari.Event]) -> None:
    if (
        isinstance(event.failed_event, hikari.InteractionCreateEvent)
        and isinstance(event.failed_event.interaction, hikari.ModalInteraction)
        and isinstance(event.exception, InvalidCodeError)
    ):
        await event.failed_event.interaction.create_initial_response(
            hikari.ResponseType.MESSAGE_CREATE,
            "Invalid code.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        return

    raise event.exception

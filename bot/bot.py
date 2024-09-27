from __future__ import annotations

import os

import arc
import hikari
import miru
import parsedatetime

from bot.database import Database
from timetable import api as api_
from timetable import utils

bot = hikari.GatewayBot(os.environ["BOT_TOKEN"], banner=None)
client = arc.GatewayClient(bot)

client.set_type_dependency(
    parsedatetime.Calendar, parsedatetime.Calendar(parsedatetime.Constants("en_GB"))
)
client.set_type_dependency(api_.API, api_.API())
client.set_type_dependency(
    miru.Client, miru.Client.from_arc(client, ignore_unknown_interactions=True)
)

client.load_extensions_from("bot/extensions")


@client.add_startup_hook
@client.inject_dependencies
async def startup_hook(client: arc.GatewayClient, api: api_.API = arc.inject()) -> None:
    # TODO: if both the backend and bot do this at the same time, there's twice the amount
    # of requests to fetch the same amount of data
    await utils.get_basic_category_results(api)

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

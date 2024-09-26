import os

import arc
import asyncpg
import hikari
import miru
import parsedatetime

from timetable import api as api_
from timetable import utils

bot = hikari.GatewayBot(os.environ["BOT_TOKEN"], banner=None)
client = arc.GatewayClient(bot)

client.set_type_dependency(
    parsedatetime.Calendar, parsedatetime.Calendar(parsedatetime.Constants("en_GB"))
)
client.set_type_dependency(api_.API, api_.API())
client.set_type_dependency(miru.Client, miru.Client.from_arc(client))

client.load_extension("bot.timetable")
# client.load_extension("bot.preferences")


@client.add_startup_hook
@client.inject_dependencies
async def startup_hook(client: arc.GatewayClient, api: api_.API = arc.inject()) -> None:
    await utils.get_basic_category_results(api)

    conn: asyncpg.Connection[asyncpg.Record] = await asyncpg.connect(
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        database=os.environ["POSTGRES_DB"],
    )
    client.set_type_dependency(
        asyncpg.Connection,
        conn,
    )

    with open("bot/build.sql", "r") as f:
        await conn.execute(f.read())

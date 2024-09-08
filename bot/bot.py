import os

import arc
import hikari

from timetable import api as api_
from timetable import utils

bot = hikari.GatewayBot(os.environ["BOT_TOKEN"], banner=None)
client = arc.GatewayClient(bot)

client.set_type_dependency(api_.API, api_.API())
client.load_extension("bot.timetable")


@client.add_startup_hook
@client.inject_dependencies
async def startup_hook(client: arc.GatewayClient, api: api_.API = arc.inject()) -> None:
    await utils.get_basic_category_results(api)

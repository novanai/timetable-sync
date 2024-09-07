import hikari
from timetable import api
import arc
import os

bot = hikari.GatewayBot(os.environ["BOT_TOKEN"], banner=None)
client = arc.GatewayClient(bot)

client.set_type_dependency(api.API, api.API())
client.load_extension("bot.timetable")

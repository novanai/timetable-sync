import os
from typing import AsyncGenerator

from timetable.api import API as TimetableAPI  # noqa: N811
from timetable.cns import API as CNSAPI


async def get_timetable_api() -> AsyncGenerator[TimetableAPI, None]:
    api = TimetableAPI(os.environ["REDIS_ADDRESS"])
    try:
        yield api
    finally:
        await api.session.close()


async def get_cns_api() -> AsyncGenerator[CNSAPI, None]:
    api = CNSAPI(os.environ["CNS_ADDRESS"])
    try:
        yield api
    finally:
        await api.session.close()

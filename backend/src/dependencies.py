from fastapi import Request
from timetable.api import API as TimetableAPI  # noqa: N811
from timetable.cns import API as CNSAPI


async def get_timetable_api(request: Request) -> TimetableAPI:
    return request.app.state.timetable_api


async def get_cns_api(request: Request) -> CNSAPI:
    return request.app.state.cns_api

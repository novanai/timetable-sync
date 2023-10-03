import datetime

import aiohttp
from sanic import Sanic, request, response

from timetable import api, models, utils

app = Sanic("DCUTimetableAPI")


@app.get("/")
async def index(request: request.Request) -> response.HTTPResponse:
    return response.HTTPResponse(status=403)


@app.get("/timetable")
async def hello_world(request: request.Request):
    print(f"Received request from {request.ip}")
    try:
        course = request.args.get("course", None)
        if not course:
            return response.HTTPResponse(b"No course code provided.", 400)

        course = await api.fetch_category_results(
            models.CategoryType.PROGRAMMES_OF_STUDY, course, cache=False
        )
        if not course.categories:
            return response.HTTPResponse(b"Invalid course code.", 400)

        timetable = await api.fetch_category_timetable(
            models.CategoryType.PROGRAMMES_OF_STUDY,
            course.categories[0].identity,
            datetime.datetime(2023, 9, 11),
            datetime.datetime(2024, 4, 14),
            cache=False,
        )

        calendar = utils.generate_ical_file(timetable)

        print(f"Generated ical file for course {course.categories[0].name}")

        return response.HTTPResponse(calendar, content_type="text/calendar")

    except aiohttp.ClientResponseError as e:
        return response.HTTPResponse(status=e.status)

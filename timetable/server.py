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
        modules = request.args.get("modules", None)
        if not course and not modules:
            return response.HTTPResponse(b"No course or modules provided.", 400)
        elif course and modules:
            return response.HTTPResponse(
                b"Cannot provide both course and modules.", 400
            )

        if course:
            calendar = await gen_course_ical(course)
        else:
            assert modules
            calendar = await gen_modules_ical(modules)

        return response.HTTPResponse(calendar, content_type="text/calendar")

    except aiohttp.ClientResponseError as e:
        print(e)
        return response.HTTPResponse(status=e.status)


async def gen_course_ical(course_code: str) -> bytes | response.HTTPResponse:
    print(f"Fetching timetable for course {course_code}")

    course = await api.fetch_category_results(
        models.CategoryType.PROGRAMMES_OF_STUDY, course_code, cache=False
    )
    if not course.categories:
        return response.HTTPResponse(
            f"Invalid course code '{course_code}'.".encode(), 400
        )

    timetable = await api.fetch_category_timetable(
        models.CategoryType.PROGRAMMES_OF_STUDY,
        course.categories[0].identity,
        datetime.datetime(2023, 9, 11),
        datetime.datetime(2024, 4, 14),
        cache=False,
    )

    calendar = utils.generate_ical_file(timetable.events)

    print(f"Generated ical file for course {course.categories[0].name}")

    return calendar


async def gen_modules_ical(modules_str: str) -> bytes | response.HTTPResponse:
    modules = [m.strip() for m in modules_str.split(",")]

    print(f"Fetching timetables for modules {', '.join(modules)}")

    events: list[models.Event] = []

    for mod in modules:
        module = await api.fetch_category_results(
            models.CategoryType.MODULES, mod, cache=False
        )
        if not module.categories:
            return response.HTTPResponse(f"Invalid module code '{mod}'.".encode(), 400)

        timetable = await api.fetch_category_timetable(
            models.CategoryType.MODULES,
            module.categories[0].identity,
            datetime.datetime(2023, 9, 11),
            datetime.datetime(2024, 4, 14),
            cache=False,
        )
        events.extend(timetable.events)

    calendar = utils.generate_ical_file(events)

    print(f"Generated ical file for modules {', '.join(modules)}")

    return calendar

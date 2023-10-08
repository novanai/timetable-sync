import datetime
import traceback

import aiohttp
import sanic
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from httptools.parser import errors
from sanic import Sanic, exceptions, request, response
from sanic.log import logger

from timetable import api, models, utils

app = Sanic("DCUTimetableAPI")


fake_events: list[models.Event] = []
scheduler = AsyncIOScheduler()


async def add_fake_event():
    fake_events.append(
        models.Event(
            identity=str(len(fake_events)) + "@fake-events-id",
            start=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=5),
            end=datetime.datetime.now(datetime.UTC)
            + datetime.timedelta(days=5, hours=1),
            status_identity=str(len(fake_events)) + "@fake-events-status-id",
            locations=None,
            description=f"Test Event {len(fake_events)} Description",
            name=f"Test Event {len(fake_events)} Name",
            event_type="Lecture",
            last_modified=datetime.datetime.now(datetime.UTC),
            module_name="CA123",
            staff_member="Someone",
            weeks=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        )
    )
    logger.debug(f"Fake event added. Total: {len(fake_events)}")


@app.before_server_start
async def before_server(app: Sanic) -> None:
    scheduler.add_job(add_fake_event, CronTrigger(minute=0))
    scheduler.start()
    logger.debug("Fake event task started")


@app.get("/")
async def index(request: request.Request) -> response.HTTPResponse:
    return response.HTTPResponse(status=403)


@app.get("/healthcheck")
async def healthcheck(request: request.Request) -> response.HTTPResponse:
    return response.HTTPResponse(status=200)


@app.get("/test")
async def test(request: request.Request) -> response.HTTPResponse:
    logger.debug(f"[TEST] Received request from {request.ip}:{request.port}")

    calendar = utils.generate_ical_file(fake_events)
    return response.HTTPResponse(calendar, content_type="text/calendar")


@app.get("/timetable")
async def timetable(request: request.Request) -> response.HTTPResponse:
    logger.debug(f"Received request from {request.ip}:{request.port}")
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
        logger.info("aiohttp error:\n", "".join(traceback.format_exception(e)))
        return response.HTTPResponse(status=e.status)


async def gen_course_ical(course_code: str) -> bytes | response.HTTPResponse:
    logger.debug(f"Fetching timetable for course {course_code}")

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

    logger.debug(f"Generated ical file for course {course.categories[0].name}")

    return calendar


async def gen_modules_ical(modules_str: str) -> bytes | response.HTTPResponse:
    modules = [m.strip() for m in modules_str.split(",")]

    logger.debug(f"Fetching timetables for modules {', '.join(modules)}")

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

    logger.debug(f"Generated ical file for modules {', '.join(modules)}")

    return calendar


@app.exception(errors.HttpParserInvalidURLError, exceptions.BadRequest)
async def handle_badurl(
    request: request.Request,
    exception: errors.HttpParserInvalidURLError | exceptions.BadRequest,
):
    logger.exception(
        f"Bad Request Exception: {type(exception)}\nIP: {request.ip}\nPath: {request.server_path}\nHeaders: {request.headers}",
        exc_info=exception,
    )

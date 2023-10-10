import datetime
import traceback

import aiohttp
import blacksheep
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from timetable import api, models, utils, logger

app = blacksheep.Application(debug=True)


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
    logger.info(f"Fake event added. Total: {len(fake_events)}")


async def before_server(app: blacksheep.Application) -> None:
    scheduler.add_job(add_fake_event, CronTrigger(minute=0))  # pyright: ignore[reportUnknownMemberType]
    scheduler.start()
    logger.info("Fake event task started")


app.on_start += before_server


@app.route("/")
async def index(request: blacksheep.Request) -> blacksheep.Response:
    return blacksheep.Response(status=403)


@app.route("/healthcheck")
async def healthcheck(request: blacksheep.Request) -> blacksheep.Response:
    return blacksheep.Response(status=200)


@app.route("/test")
async def test(request: blacksheep.Request) -> blacksheep.Response:
    calendar = utils.generate_ical_file(fake_events)
    return blacksheep.Response(
        200, content=blacksheep.Content(content_type=b"text/calendar", data=calendar)
    )


@app.route("/api")
async def timetable_api(request: blacksheep.Request) -> blacksheep.Response:
    course = request.query.get("course", None)
    modules = request.query.get("modules", None)
    if not course and not modules:
        return blacksheep.Response(
            400,
            content=blacksheep.Content(
                content_type=b"text/plain", data=b"No course or modules provided."
            ),
        )
    elif course and modules:
        return blacksheep.Response(
            400,
            content=blacksheep.Content(
                content_type=b"text/plain",
                data=b"Cannot provide both course and modules.",
            ),
        )
    if course:
        calendar = await gen_course_ical(course[0])
    else:
        assert modules
        calendar = await gen_modules_ical(modules[0])

    if isinstance(calendar, blacksheep.Response):
        return calendar

    return blacksheep.Response(
        200,
        content=blacksheep.Content(
            b"text/calendar",
            data=calendar,
        ),
    )


async def gen_course_ical(course_code: str) -> bytes | blacksheep.Response:
    logger.info(f"Fetching timetable for course {course_code}")

    course = await api.fetch_category_results(
        models.CategoryType.PROGRAMMES_OF_STUDY, course_code, cache=False
    )
    if not course.categories:
        return blacksheep.Response(
            400,
            content=blacksheep.Content(
                content_type=b"text/plain",
                data=f"Invalid course code '{course_code}'.".encode(),
            ),
        )

    timetable = await api.fetch_category_timetable(
        models.CategoryType.PROGRAMMES_OF_STUDY,
        course.categories[0].identity,
        datetime.datetime(2023, 9, 11),
        datetime.datetime(2024, 4, 14),
        cache=False,
    )

    calendar = utils.generate_ical_file(timetable.events)

    logger.info(f"Generated ical file for course {course.categories[0].name}")

    return calendar


async def gen_modules_ical(modules_str: str) -> bytes | blacksheep.Response:
    modules = [m.strip() for m in modules_str.split(",")]

    logger.info(f"Fetching timetables for modules {', '.join(modules)}")

    events: list[models.Event] = []

    for mod in modules:
        module = await api.fetch_category_results(
            models.CategoryType.MODULES, mod, cache=False
        )
        if not module.categories:
            return blacksheep.Response(
                400,
                content=blacksheep.Content(
                    content_type=b"text/plain",
                    data=f"Invalid module code '{mod}'.".encode(),
                ),
            )

        timetable = await api.fetch_category_timetable(
            models.CategoryType.MODULES,
            module.categories[0].identity,
            datetime.datetime(2023, 9, 11),
            datetime.datetime(2024, 4, 14),
            cache=False,
        )
        events.extend(timetable.events)

    calendar = utils.generate_ical_file(events)

    logger.info(f"Generated ical file for modules {', '.join(modules)}")

    return calendar

@app.exception_handler(aiohttp.ClientResponseError)
async def handle_badurl(
    request: blacksheep.Request,
    exception: aiohttp.ClientResponseError,
):
    logger.error(
        traceback.format_exception(exception)
    )
    return blacksheep.Response(500, content=blacksheep.Content(b"text/plain", b"500 Internal Server Error"))

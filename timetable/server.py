import time
import traceback
import aiohttp
import blacksheep
import datetime
from blacksheep.server.templating import (
    use_templates,  # pyright: ignore[reportUnknownVariableType]
)
from jinja2 import PackageLoader

from timetable import api, logger, models, utils

app = blacksheep.Application()

view = use_templates(  # pyright: ignore[reportUnknownVariableType]
    app, loader=PackageLoader("timetable", "templates"), enable_async=True
)


@app.on_start
async def start_session(app: blacksheep.Application) -> None:
    api.session = aiohttp.ClientSession()
    await get_or_fetch_and_cache_categories()


@app.on_stop
async def stop_session(app: blacksheep.Application) -> None:
    assert api.session
    await api.session.close()


async def get_or_fetch_and_cache_categories() -> tuple[
    models.Category, models.Category
]:
    if not (
        courses := await api.get_category_results(
            models.CategoryType.PROGRAMMES_OF_STUDY
        )
    ):
        start = time.time()
        logger.info("Caching Programmes of Study")
        courses = await api.fetch_category_results(
            models.CategoryType.PROGRAMMES_OF_STUDY, cache=True
        )
        logger.info(f"Cached Programmes of Study in {time.time()-start}s")

    if not (modules := await api.get_category_results(models.CategoryType.MODULES)):
        start = time.time()
        logger.info("Caching Modules")
        modules = await api.fetch_category_results(
            models.CategoryType.MODULES, cache=True
        )
        logger.info(f"Cached Modules in {time.time()-start}s")

    return courses, modules


@app.route("/healthcheck")
async def healthcheck(request: blacksheep.Request) -> blacksheep.Response:
    return blacksheep.Response(status=200)


@app.route("/timetable")
async def timetable_ui(request: blacksheep.Request) -> blacksheep.Response:
    courses, modules = await get_or_fetch_and_cache_categories()

    return await view(  # pyright: ignore[reportUnknownVariableType, reportGeneralTypeIssues]
        "timetable",
        {
            "courses": [c.name for c in courses.categories],
            "modules": [
                {
                    "name": m.name,
                    "value": m.code,
                }
                for m in modules.categories
            ],
        },
    )


@app.route("/")
async def howto(request: blacksheep.Request) -> blacksheep.Response:
    return await view(  # pyright: ignore[reportUnknownVariableType, reportGeneralTypeIssues]
        "howto",
        {},
    )


@app.route("/api")
async def timetable_api(request: blacksheep.Request) -> blacksheep.Response:
    course = request.query.get("course")
    modules = request.query.get("modules")
    format = request.query.get("format")
    start = request.query.get("start")
    end = request.query.get("end")

    format = models.ResponseFormat.from_str(format[0] if format else None)
    start_date = utils.to_isoformat(start[0]) if start else None
    end_date = utils.to_isoformat(end[0]) if end else None

    message: str | None = None

    if not course and not modules:
        message = "No course or modules provided."
    elif course and modules:
        message = "Cannot provide both course and modules."
    elif format is models.ResponseFormat.UNKNOWN:
        message = f"Invalid format '{format}'."
    elif start and not start_date:
        message = f"Invalid start date '{start}'."
    elif end and not end_date:
        message = f"Invalid end date '{end}'."
    elif start_date and end_date and start_date > end_date:
        message = "Start date cannot be later then end date."

    if message:
        logger.error(f"400 on /api: {message}")
        return blacksheep.Response(
            400,
            content=blacksheep.Content(
                content_type=b"text/plain", data=message.encode()
            ),
        )

    if course:
        calendar, error = await gen_course_timetable(
            course[0], format, start_date, end_date
        )
    else:
        assert modules
        calendar, error = await gen_modules_timetable(
            modules[0], format, start_date, end_date
        )

    if error:
        logger.error(f"400 on /api: {calendar.decode()}")
        return blacksheep.Response(
            400,
            content=blacksheep.Content(content_type=b"text/plain", data=calendar),
        )

    return blacksheep.Response(
        200,
        content=blacksheep.Content(
            format.content_type.encode(),
            data=calendar,
        ),
    )


async def gen_course_timetable(
    course_code: str,
    format: models.ResponseFormat,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
) -> tuple[bytes, bool]:
    now = time.time()
    logger.info(f"Generating timetable for course {course_code}")

    course = await api.fetch_category_results(
        models.CategoryType.PROGRAMMES_OF_STUDY, course_code, cache=False
    )
    if not course.categories:
        return f"Invalid course code '{course_code}'.".encode(), True

    if timetable := await api.get_category_timetable(
        course.categories[0].identity, start=start, end=end
    ):
        logger.info(f"Using cached timetable for course {course_code}")
    else:
        logger.info(f"Fetching timetable for course {course_code}")
        timetables = await api.fetch_category_timetable(
            models.CategoryType.PROGRAMMES_OF_STUDY,
            [course.categories[0].identity],
            start=start,
            end=end,
            cache=True,
        )
        timetable = timetables[0]

    if format is models.ResponseFormat.ICAL:
        calendar = utils.generate_ical_file(timetable.events)
    else:
        assert format is models.ResponseFormat.JSON
        calendar = utils.generate_json_file(timetable.events)

    logger.info(
        f"Generated {format.value} file for course {course.categories[0].name} in {round(time.time() - now, 3)}s"
    )

    return calendar, False


async def gen_modules_timetable(
    modules_str: str,
    format: models.ResponseFormat,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
) -> tuple[bytes, bool]:
    now = time.time()
    modules = [m.strip() for m in modules_str.split(",")]

    logger.info(f"Generating timetable for modules {', '.join(modules)}")

    identities: list[str] = []

    for mod in modules:
        module = await api.fetch_category_results(
            models.CategoryType.MODULES, mod, cache=False
        )
        if not module.categories:
            return f"Invalid module code '{mod}'.".encode(), True

        identities.append(module.categories[0].identity)

    events: list[models.Event] = []
    to_fetch: list[str] = []

    for mod, id_ in zip(modules, identities):
        if timetable := await api.get_category_timetable(id_, start=start, end=end):
            logger.info(f"Using cached timetable for module {mod}")
            events.extend(timetable.events)
        else:
            logger.info(f"Fetching timetable for module {mod}")
            to_fetch.append(id_)

    if to_fetch:
        timetables = await api.fetch_category_timetable(
            models.CategoryType.MODULES,
            to_fetch,
            start=start,
            end=end,
            cache=True,
        )
        for timetable in timetables:
            events.extend(timetable.events)

    if format is models.ResponseFormat.ICAL:
        calendar = utils.generate_ical_file(events)
    else:
        assert format is models.ResponseFormat.JSON
        calendar = utils.generate_json_file(events)

    logger.info(
        f"Generated {format.value} file for modules {', '.join(modules)} in {round(time.time() - now, 3)}s"
    )

    return calendar, False


@app.exception_handler(aiohttp.ClientResponseError)
async def handle_badurl(
    request: blacksheep.Request,
    exception: aiohttp.ClientResponseError,
):
    logger.error(traceback.format_exception(exception))
    return blacksheep.Response(
        500, content=blacksheep.Content(b"text/plain", b"500 Internal Server Error")
    )

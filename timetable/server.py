import datetime
import time
import traceback
import json
import aiohttp
import blacksheep
from blacksheep.server.templating import (
    use_templates,  # pyright: ignore[reportUnknownVariableType]
)
from jinja2 import PackageLoader

from timetable import api, logger, models, utils

app = blacksheep.Application(debug=True)

view = use_templates(  # pyright: ignore[reportUnknownVariableType]
    app, loader=PackageLoader("timetable", "templates"), enable_async=True
)


@app.on_start
async def start_session(app: blacksheep.Application) -> None:
    api.session = aiohttp.ClientSession()


@app.on_stop
async def stop_session(app: blacksheep.Application) -> None:
    assert api.session
    await api.session.close()


@app.on_start
async def cache_categories(
    app: blacksheep.Application,
) -> tuple[models.Category, models.Category]:
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
    courses = await api.get_category_results(models.CategoryType.PROGRAMMES_OF_STUDY)
    modules = await api.get_category_results(models.CategoryType.MODULES)
    if not courses or not modules:
        courses, modules = await cache_categories(app)

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
    course = request.query.get("course", None)
    modules = request.query.get("modules", None)
    format = request.query.get("format", None)
    format = format[0] if format else "ical"
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
    if format not in {"ical", "json"}:
        return blacksheep.Response(
            400,
            content=blacksheep.Content(
                content_type=b"text/plain",
                data=b"Invalid format.",
            ),
        )

    if course:
        calendar = await gen_course_timetable(course[0], format)
    else:
        assert modules
        calendar = await gen_modules_timetable(modules[0], format)

    if isinstance(calendar, blacksheep.Response):
        return calendar
    elif isinstance(calendar, bytes):
        return blacksheep.Response(
            200,
            content=blacksheep.Content(
                b"text/calendar",
                data=calendar,
            ),
        )
    else:
        return blacksheep.Response(
            200,
            content=blacksheep.Content(
                b"application/json",
                data=json.dumps(calendar).encode(),
            ),
        )


async def gen_course_timetable(course_code: str, format: str) -> blacksheep.Response | bytes | list[dict[str, str]]:
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

    timetables = await api.fetch_category_timetable(
        models.CategoryType.PROGRAMMES_OF_STUDY,
        [course.categories[0].identity],
        datetime.datetime(2023, 9, 11),
        datetime.datetime(2024, 4, 14),
        cache=False,
    )
    events = timetables[0].events
    if format == "ical":
        calendar = utils.generate_ical_file(events)
    else:
        assert format == "json"
        calendar = utils.generate_json_file(events)

    logger.info(f"Generated {format} file for course {course.categories[0].name}")

    return calendar


async def gen_modules_timetable(modules_str: str, format: str) -> blacksheep.Response | bytes | list[dict[str, str]]:
    modules = [m.strip() for m in modules_str.split(",")]

    logger.info(f"Fetching timetables for modules {', '.join(modules)}")

    identities: list[str] = []

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

        identities.append(module.categories[0].identity)

    events: list[models.Event] = []

    timetables = await api.fetch_category_timetable(
        models.CategoryType.MODULES,
        identities,
        datetime.datetime(2023, 9, 11),
        datetime.datetime(2024, 4, 14),
        cache=False,
    )
    for timetable in timetables:
        events.extend(timetable.events)

    if format == "ical":
        calendar = utils.generate_ical_file(events)
    else:
        assert format == "json"
        calendar = utils.generate_json_file(events)

    logger.info(f"Generated {format} file for modules {', '.join(modules)}")

    return calendar


@app.exception_handler(aiohttp.ClientResponseError)
async def handle_badurl(
    request: blacksheep.Request,
    exception: aiohttp.ClientResponseError,
):
    logger.error(traceback.format_exception(exception))
    return blacksheep.Response(
        500, content=blacksheep.Content(b"text/plain", b"500 Internal Server Error")
    )

import time
import traceback
import aiohttp
import blacksheep
import orjson
import datetime
import logging
from backend import __version__
from timetable import api as api_, models, utils


from backend import api_docs
from blacksheep.server.openapi.v3 import OpenAPIHandler
from openapidocs.v3 import Info  # pyright: ignore[reportMissingTypeStubs]


logger = logging.getLogger(__name__)


app = blacksheep.Application()
api = api_.API()

docs = OpenAPIHandler(
    info=Info(title="TimetableSync API", version=__version__), ui_path="/api_docs"
)
docs.bind_app(app)



@app.on_start
async def start_session() -> None:
    await get_or_fetch_and_cache_categories()


@app.on_stop
async def stop_session() -> None:
    await api.session.close()


async def get_or_fetch_and_cache_categories() -> (
    tuple[models.Category, models.Category]
):
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


@docs.ignore()
@blacksheep.route("/healthcheck")
async def healthcheck() -> blacksheep.Response:
    return blacksheep.Response(status=200)



@docs(api_docs.API)
@blacksheep.route("/api")
async def timetable_api(
    course: blacksheep.FromQuery[str] | None = None,
    modules: blacksheep.FromQuery[str] | None = None,
    format: blacksheep.FromQuery[str] | None = None,
    start: blacksheep.FromQuery[str] | None = None,
    end: blacksheep.FromQuery[str] | None = None,
) -> blacksheep.Response:
    format_ = models.ResponseFormat.from_str(format.value if format else None)
    start_date = utils.to_isoformat(start.value) if start else None
    end_date = utils.to_isoformat(end.value) if end else None

    message: str | None = None

    if not course and not modules:
        message = "No course or modules provided."
    elif course and modules:
        message = "Cannot provide both course and modules."
    elif format_ is models.ResponseFormat.UNKNOWN:
        message = f"Invalid format '{format_}'."
    elif start and not start_date:
        message = f"Invalid start date '{start.value}'."
    elif end and not end_date:
        message = f"Invalid end date '{end.value}'."
    elif start_date and end_date and start_date > end_date:
        message = "Start date cannot be later then end date."

    if message:
        logger.error(f"400 on /api: {message}")
        if format_ in (models.ResponseFormat.UNKNOWN, models.ResponseFormat.ICAL):
            content = blacksheep.Content(
                content_type=b"text/plain", data=message.encode()
            )
        else:
            assert format_ is models.ResponseFormat.JSON
            content = blacksheep.Content(
                content_type=b"application/json",
                data=orjson.dumps(models.APIError(400, message)),
            )

        return blacksheep.Response(
            400,
            content=content,
        )

    if course:
        calendar, error = await gen_course_timetable(
            course.value, format_, start_date, end_date
        )
    else:
        assert modules
        calendar, error = await gen_modules_timetable(
            modules.value, format_, start_date, end_date
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
            format_.content_type.encode(),
            data=calendar,
        ),
    )


async def gen_course_timetable(
    course_code: str,
    format: models.ResponseFormat,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
) -> tuple[bytes, bool]:
    # now = time.time()
    logger.info(f"Generating timetable for course {course_code}")

    try:
        events = await api.generate_course_timetable(course_code, start, end)
    except models.InvalidCodeError as e:
        return f"Invalid course code '{e.code}'.".encode(), True

    if format is models.ResponseFormat.ICAL:
        calendar = utils.generate_ical_file(events)
    else:
        assert format is models.ResponseFormat.JSON
        calendar = utils.generate_json_file(events)

    # logger.info(
    #     f"Generated {format.value} file for course {course.categories[0].name} in {round(time.time() - now, 3)}s"
    # )

    return calendar, False


async def gen_modules_timetable(
    modules_str: str,
    format: models.ResponseFormat,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
) -> tuple[bytes, bool]:
    # now = time.time()
    modules = [m.strip() for m in modules_str.split(",")]

    logger.info(f"Generating timetable for modules {', '.join(modules)}")

    try:
        events = await api.generate_modules_timetable(modules, start, end)
    except models.InvalidCodeError as e:
        return f"Invalid module code '{e.code}'.".encode(), True

    if format is models.ResponseFormat.ICAL:
        calendar = utils.generate_ical_file(events)
    else:
        assert format is models.ResponseFormat.JSON
        calendar = utils.generate_json_file(events)

    # logger.info(
    #     f"Generated {format.value} file for modules {', '.join(modules)} in {round(time.time() - now, 3)}s"
    # )

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

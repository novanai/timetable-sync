import datetime
import logging
import time

import blacksheep
import orjson
from blacksheep.server.openapi.v3 import OpenAPIHandler
from openapidocs.v3 import Info  # pyright: ignore[reportMissingTypeStubs]

from backend import __version__, api_docs
from timetable import api as api_
from timetable import models, utils

logger = logging.getLogger(__name__)


app = blacksheep.Application()
api = api_.API()

docs = OpenAPIHandler(
    info=Info(title="TimetableSync API", version=__version__),
    ui_path="/api/api_docs",
    json_spec_path="/api/openapi.json",
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
        courses = await api.fetch_category_results(
            models.CategoryType.PROGRAMMES_OF_STUDY, cache=True
        )
        logger.info(f"Cached Programmes of Study in {time.time()-start:.2f}s")

    if not (modules := await api.get_category_results(models.CategoryType.MODULES)):
        start = time.time()
        modules = await api.fetch_category_results(
            models.CategoryType.MODULES, cache=True
        )
        logger.info(f"Cached Modules in {time.time()-start:.2f}s")

    return courses, modules


@docs.ignore()
@blacksheep.route("/api/healthcheck")
async def healthcheck() -> blacksheep.Response:
    return blacksheep.Response(status=200)


@docs.ignore()
@blacksheep.route("/api/all/{category_type}")
async def all_category_values(
    category_type: str,
) -> blacksheep.Response:
    if category_type not in ("courses", "modules"):
        return blacksheep.Response(
            status=400,
            content=blacksheep.Content(
                content_type=b"text/plain",
                data=b"Invalid value provided.",
            ),
        )

    courses, modules = await get_or_fetch_and_cache_categories()

    data: list[str | dict[str, str]]

    if category_type == "courses":
        data = list(set(c.name for c in courses.items))
        data.sort(key=str)
    else:
        assert category_type == "modules"
        codes: list[str] = []
        data = []

        for m in modules.items:
            if m.code not in codes:
                data.append(
                    {
                        "name": m.name,
                        "value": m.code,
                    }
                )
                codes.append(m.code)

    return blacksheep.Response(
        status=200,
        content=blacksheep.Content(
            content_type=b"application/json",
            data=orjson.dumps(data),
        ),
    )


@docs(api_docs.API)
@blacksheep.route("/api")
async def timetable_api(
    course: str | None = None,
    courses: str | None = None,
    modules: str | None = None,
    format: str | None = None,
    display: bool | None = None,
    start: str | None = None,
    end: str | None = None,
) -> blacksheep.Response:
    format_ = models.ResponseFormat.from_str(format if format else None)
    start_date = datetime.datetime.fromisoformat(start) if start else None
    end_date = datetime.datetime.fromisoformat(end) if end else None

    if not course and not courses and not modules:
        raise ValueError("No courses or modules provided.")
    elif format_ is models.ResponseFormat.UNKNOWN:
        raise ValueError(f"Invalid format '{format_}'.")

    events: list[models.Event] = []

    if course or courses:
        codes = [c.strip() for c in courses.split(",")] if courses else []
        if course and course.strip() not in codes:
            codes.append(course.strip())

        events.extend(await generate_courses_timetables(codes, start_date, end_date))
    if modules:
        codes = [m.strip() for m in modules.split(",")]

        events.extend(await generate_modules_timetables(codes, start_date, end_date))

    if format_ is models.ResponseFormat.ICAL:
        timetable = utils.generate_ical_file(events)
    else:
        assert format_ is models.ResponseFormat.JSON
        timetable = utils.generate_json_file(events, display)

    return blacksheep.Response(
        200,
        content=blacksheep.Content(
            format_.content_type.encode(),
            data=timetable,
        ),
    )


async def generate_courses_timetables(
    course_codes: list[str],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
) -> list[models.Event]:
    logger.info(f"Generating timetables for courses {', '.join(course_codes)}")

    events = await api.gather_events_for_courses(course_codes, start, end)

    return events


async def generate_modules_timetables(
    module_codes: list[str],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
) -> list[models.Event]:
    logger.info(f"Generating timetable for modules {', '.join(module_codes)}")

    events = await api.gather_events_for_modules(module_codes, start, end)

    return events


# TODO: add error handler

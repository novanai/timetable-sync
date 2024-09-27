import collections
import datetime
import logging

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
    await utils.get_basic_category_results(api)


@app.on_stop
async def stop_session() -> None:
    await api.session.close()


@docs.ignore()
@blacksheep.route("/api/healthcheck")
async def healthcheck() -> blacksheep.Response:
    return blacksheep.ok()


@docs.ignore()
@blacksheep.route("/api/all/{category_type}")
async def all_category_values(
    category_type: str,
) -> blacksheep.Response:
    if category_type not in ("courses", "modules", "locations"):
        return blacksheep.status_code(
            400,
            "Invalid value provided.",
        )

    categories = await utils.get_basic_category_results(api)

    return blacksheep.Response(
        status=200,
        content=blacksheep.Content(
            content_type=b"application/json",
            data=orjson.dumps(getattr(categories, category_type)),
        ),
    )


@docs(api_docs.API)
@blacksheep.route("/api")
async def timetable_api(
    course: str | None = None,  # NOTE: backwards compatibility only
    courses: str | None = None,
    modules: str | None = None,
    locations: str | None = None,
    format: str | None = None,
    display: bool | None = None,
    start: str | None = None,
    end: str | None = None,
) -> blacksheep.Response:
    format_ = models.ResponseFormat.from_str(format if format else None)
    start_date = datetime.datetime.fromisoformat(start) if start else None
    end_date = datetime.datetime.fromisoformat(end) if end else None

    if not course and not courses and not modules and not locations:
        raise ValueError("No courses, modules or locations provided.")
    elif format_ is models.ResponseFormat.UNKNOWN:
        raise ValueError(f"Invalid format '{format_}'.")

    codes: dict[models.CategoryType, list[str]] = collections.defaultdict(list)

    def str_to_list(text: str) -> list[str]:
        return [t.strip() for t in text.split(",")]

    if courses and courses.strip():
        codes[models.CategoryType.PROGRAMMES_OF_STUDY].extend(str_to_list(courses))
    if course and course.strip() not in codes[models.CategoryType.PROGRAMMES_OF_STUDY]:
        codes[models.CategoryType.PROGRAMMES_OF_STUDY].append(course.strip())
    if modules:
        codes[models.CategoryType.MODULES].extend(str_to_list(modules))
    if locations:
        codes[models.CategoryType.LOCATIONS].extend(str_to_list(locations))

    items = await utils.resolve_to_category_items(codes, api)
    identities = {
        group: [item.identity for item in group_items]
        for group, group_items in items.items()
    }
    events = await utils.gather_events(identities, start_date, end_date, api)

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


# TODO: add error handler

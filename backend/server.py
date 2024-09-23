import datetime
import logging

import blacksheep
import orjson
from blacksheep.server.openapi.v3 import OpenAPIHandler
from openapidocs.v3 import Info  # pyright: ignore[reportMissingTypeStubs]

from backend import __version__, api_docs
from timetable import api as api_
from timetable import models, utils
import collections

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
    return blacksheep.Response(status=200)


@docs.ignore()
@blacksheep.route("/api/all/{category_type}")
async def all_category_values(
    category_type: str,
) -> blacksheep.Response:
    # TODO: set category_type to a Final and move this into error handler
    if category_type not in ("courses", "modules", "locations"):
        return blacksheep.Response(
            status=400,
            content=blacksheep.Content(
                content_type=b"text/plain",
                data=b"Invalid value provided.",
            ),
        )

    categories = await utils.get_basic_category_results(api)

    return blacksheep.Response(
        status=200,
        content=blacksheep.Content(
            content_type=b"application/json",
            data=orjson.dumps(
                getattr(categories, category_type)
            ),
        ),
    )


@docs(api_docs.API)
@blacksheep.route("/api")
async def timetable_api(
    course: str | None = None, # Deprecated, cannot remove for backwards compatibility
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
    # TODO: remove this format and have proper allowed values
    elif format_ is models.ResponseFormat.UNKNOWN:
        raise ValueError(f"Invalid format '{format_}'.")

    events: list[models.Event] = []
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

    for group, cat_codes in codes.items():
        for code in cat_codes:
            # code is a category item identity and timetable is cached
            timetable = await api.get_category_item_timetable(code, start=start_date, end=end_date)
            if timetable:
                events.extend(timetable.events)
                logger.info(
                    f"Using cached events for {group} {timetable.identity} (total {len(timetable.events)})"
                )
                continue

            # code is a category item identity and timetable must be fetched
            item = await api.get_category_item(group, code)
            if item:
                timetables = await api.fetch_category_timetables(
                    group,
                    [item.identity],
                    start=start_date,
                    end=end_date,
                )
                events.extend(timetables[0].events)
                logger.info(
                    f"Fetched events for {group} {timetables[0].identity} (total {len(timetables[0].events)})"
                )
                continue

            # code is not a category item, search cached category items for it
            category = await api.get_category(group, query=code, count=1)
            if not category or not category.items:
                # could not find category item in cache, fetch it
                category = await api.fetch_category(group, query=code)
                if not category.items:
                    raise ValueError(f"Invalid code/identity: {code}")
            
            item = category.items[0]

            # timetable is cached
            timetable = await api.get_category_item_timetable(item.identity, start=start_date, end=end_date)
            if timetable:
                events.extend(timetable.events)
                logger.info(
                    f"Using cached events for {group} {timetable.identity} (total {len(timetable.events)})"
                )
                continue

            # timetable is not cached
            timetables = await api.fetch_category_timetables(
                group,
                [item.identity],
                start=start_date,
                end=end_date,
            )
            logger.info(
                f"Fetched events for {group} {timetables[0].identity} (total {len(timetables[0].events)})"
            )
            events.extend(timetables[0].events)

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

import datetime
import logging
import time

import colorhash
import traceback

import aiohttp
import blacksheep
import orjson
from blacksheep.server.openapi.v3 import OpenAPIHandler
from openapidocs.v3 import Info  # pyright: ignore[reportMissingTypeStubs]
import zoneinfo
from backend import __version__, api_docs
from timetable import api as api_
from timetable import models, utils
import dataclasses
import typing

logger = logging.getLogger(__name__)


IRELAND_UTC_OFFSET = zoneinfo.ZoneInfo("Europe/Dublin").utcoffset(datetime.datetime.now(datetime.timezone.utc))

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
                data.append({
                    "name": m.name,
                    "value": m.code,
                })
                codes.append(m.code)

    return blacksheep.Response(
        status=200,
        content=blacksheep.Content(
            content_type=b"application/json",
            data=orjson.dumps(data),
        ),
    )

# TODO: ideally all of the below calendar stuff should be handled on the frontend,
# this is only a temporary solution

@dataclasses.dataclass
class CalendarEvent:
    id: str
    start: datetime.datetime
    end: datetime.datetime
    title: "CalendarEventContent"
    background_colour: str

    # TODO: calc dst offset for the event time
    def to_json(self) -> dict[str, typing.Any]:
        return {
            "id": self.id,
            "start": self.start + IRELAND_UTC_OFFSET if IRELAND_UTC_OFFSET is not None else 0,
            "end": self.end + IRELAND_UTC_OFFSET if IRELAND_UTC_OFFSET is not None else 0,
            "title": self.title.to_object(),
            "backgroundColor": self.background_colour,
        }

@dataclasses.dataclass
class CalendarEventContent:
    summary: str
    description: str
    location: str

    def to_object(self) -> dict[str, str]:
        return {
            "html": f"<b>{self.summary}</b><p>{self.description}</p><p>{self.location}</p>"
        }

def gather_events(events: list[models.Event]) -> list[CalendarEvent]:
    all_events: list[CalendarEvent] = []

    for event in events:
        modules_codes: set[str] = set()
        for data in event.parsed_name_data:
            modules_codes.update(data.module_codes)

        event_type = event.parsed_name_data[0].activity_type.display() if event.parsed_name_data else ""

        all_events.append(
            CalendarEvent(
                id=event.identity,
                start=event.start,
                end=event.end,
                title=CalendarEventContent(
                    summary=f"{"/".join(sorted(modules_codes))} {event_type}",
                    description=("📄 " + event.module_name.split(" ", maxsplit=1)[1]) if event.module_name else "",
                    # location=utils.generate_location_string(event),
                    location=("📍 " + ", ".join([f"{loc.building}{loc.floor}{loc.room}" for loc in event.locations])) if event.locations else "",
                ),
                background_colour=colorhash.ColorHash("".join(modules_codes), lightness=[0.7], saturation=[0.5]).hex,
            )
        )

    return all_events

@docs.ignore()
@blacksheep.route("/api/calendar")
async def calendar_api(
    start: blacksheep.FromQuery[str],
    end: blacksheep.FromQuery[str],
    courses: blacksheep.FromQuery[str] | None = None,
    modules: blacksheep.FromQuery[str] | None = None,
    
) -> blacksheep.Response:
    start_date = utils.to_isoformat(start.value) 
    end_date = utils.to_isoformat(end.value)

    all_events: list[CalendarEvent] = []

    if courses:
        codes = courses.value.split(",")
        logger.info(f"Generating calendar for courses {', '.join(codes)}")
        events = await api.gather_events_for_courses(
            codes,
            start_date,
            end_date
        )
        all_events.extend(gather_events(events))
            

    if modules:
        codes = modules.value.split(",")
        logger.info(f"Generating calendar for modules {', '.join(codes)}")
        events = await api.gather_events_for_modules(
            codes, 
            start_date,
            end_date
        )
        all_events.extend(gather_events(events))

    return blacksheep.Response(
        200,
        content=blacksheep.Content(
            content_type=b"application/json",
            data=orjson.dumps([e.to_json() for e in all_events]),
        )
    )

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
        calendar, error = await generate_courses_timetables(
            course.value, format_, start_date, end_date
        )
    else:
        assert modules
        calendar, error = await generate_modules_timetables(
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


async def generate_courses_timetables(
    course_codes: str,
    format: models.ResponseFormat,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
) -> tuple[bytes, bool]:
    courses = [c.strip() for c in course_codes.split(",")]
    logger.info(f"Generating timetables for courses {', '.join(courses)}")

    try:
        events = await api.gather_events_for_courses(courses, start, end)
    except models.InvalidCodeError as e:
        return f"Invalid course code '{e.code}'.".encode(), True

    if format is models.ResponseFormat.ICAL:
        calendar = utils.generate_ical_file(events)
    else:
        assert format is models.ResponseFormat.JSON
        calendar = utils.generate_json_file(events)

    return calendar, False


async def generate_modules_timetables(
    module_codes: str,
    format: models.ResponseFormat,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
) -> tuple[bytes, bool]:
    modules = [m.strip() for m in module_codes.split(",")]

    logger.info(f"Generating timetable for modules {', '.join(modules)}")

    try:
        events = await api.gather_events_for_modules(modules, start, end)
    except models.InvalidCodeError as e:
        return f"Invalid module code '{e.code}'.".encode(), True

    if format is models.ResponseFormat.ICAL:
        calendar = utils.generate_ical_file(events)
    else:
        assert format is models.ResponseFormat.JSON
        calendar = utils.generate_json_file(events)

    return calendar, False

# Handle other errors, e.g. ValueError raised by timetable api
@app.exception_handler(aiohttp.ClientResponseError)
async def handle_badurl(
    request: blacksheep.Request,
    exception: aiohttp.ClientResponseError,
):
    logger.error(traceback.format_exception(exception))
    return blacksheep.Response(
        500, content=blacksheep.Content(b"text/plain", b"500 Internal Server Error")
    )

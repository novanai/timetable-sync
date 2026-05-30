import collections
import datetime
import enum
import logging
import time
from typing import Annotated
from uuid import UUID

import msgspec
from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Response
from timetable import cns, models, utils
from timetable.api import API as TimetableAPI  # noqa: N811
from timetable.cns import API as CNSAPI

from src import metrics
from src.dependencies import get_cns_api, get_timetable_api

logger = logging.getLogger(__name__)


class ExtraDetails(enum.Enum):
    NONE = "none"
    ALL = "all"
    ONLY = "only"


class CategoryType(enum.Enum):
    COURSE = "course"
    MODULE = "module"
    LOCATION = "location"

    def to_model(self) -> models.CategoryType:
        match self:
            case CategoryType.COURSE:
                return models.CategoryType.PROGRAMMES_OF_STUDY
            case CategoryType.MODULE:
                return models.CategoryType.MODULES
            case CategoryType.LOCATION:
                return models.CategoryType.LOCATIONS


timetable_router = APIRouter(prefix="/timetable")


@timetable_router.get("/category/{category_type}/items")
async def get_timetable_category_items(
    timetable_api: Annotated[TimetableAPI, Depends(get_timetable_api)],
    category_type: Annotated[CategoryType, Path()],
    query: Annotated[str | None, Query()] = None,
) -> Response:
    start = time.perf_counter()
    used_cache: bool = True

    category = await timetable_api.get_category(
        category_type.to_model(), query=query, items_type=models.BasicCategoryItem
    )
    if not category:
        used_cache = False
        category = await timetable_api.fetch_category(
            category_type.to_model(), query=query, items_type=models.BasicCategoryItem
        )

    data = msgspec.json.encode(category.items)

    duration = time.perf_counter() - start
    metrics.REQUEST_LATENCY.labels(
        endpoint="/v3/timetable/category/:category_type/items", used_cache=used_cache
    ).observe(duration)

    return Response(
        content=data,
        media_type="application/json",
    )


@timetable_router.get("/category/{category_type}/items/{item_id}")
async def get_timetable_category_item(
    timetable_api: Annotated[TimetableAPI, Depends(get_timetable_api)],
    category_type: Annotated[CategoryType, Path()],
    item_id: Annotated[UUID, Path()],
) -> Response:
    start = time.perf_counter()
    used_cache: bool = True

    item = await timetable_api.get_category_item(item_id)
    if not item:
        used_cache = False
        await timetable_api.fetch_category_item(category_type.to_model(), item_id)

    data = msgspec.json.encode(item)

    duration = time.perf_counter() - start
    metrics.REQUEST_LATENCY.labels(
        endpoint="/v3/timetable/category/:category_type/items/:item_id",
        used_cache=used_cache,
    ).observe(duration)

    return Response(
        content=data,
        media_type="application/json",
    )


@timetable_router.get("/category/{category_type}/items/{item_id}/events")
async def get_timetable_category_item_events(
    timetable_api: Annotated[TimetableAPI, Depends(get_timetable_api)],
    category_type: Annotated[CategoryType, Path()],
    item_id: Annotated[UUID, Path()],
    start: Annotated[datetime.datetime | None, Query()] = None,
    end: Annotated[datetime.datetime | None, Query()] = None,
    extra_details: Annotated[ExtraDetails, Query()] = ExtraDetails.NONE,
    media_type: Annotated[str, Header()] = "text/calendar",
) -> Response:
    start_ = time.perf_counter()

    if media_type not in {"text/calendar", "application/json"}:
        raise HTTPException(400, "Invalid media type provided.")

    identities = {category_type.to_model(): [item_id]}
    events = await utils.gather_events(identities, start, end, timetable_api)

    if media_type == "text/calendar":
        timetable = utils.to_ics_file(events)
    else:
        assert media_type == "application/json"
        # TODO: handle extra_details
        # display = extra_details is ExtraDetails.ALL
        timetable = msgspec.json.encode(events)

    duration = time.perf_counter() - start_
    metrics.REQUEST_LATENCY.labels(
        endpoint="/v3/timetable/category/:category_type/items/:item_id/events",
        used_cache=None,
    ).observe(duration)
    metrics.EVENTS_COUNT.labels(category_type=category_type.to_model().name).observe(
        len(events)
    )

    return Response(
        content=timetable,
        media_type=media_type,
    )


@timetable_router.get(
    "/events",
)
async def get_timetable_calendar_events(
    timetable_api: Annotated[TimetableAPI, Depends(get_timetable_api)],
    course: Annotated[
        list[UUID],
        Query(),
    ] = [],
    module: Annotated[
        list[UUID],
        Query(),
    ] = [],
    location: Annotated[
        list[UUID],
        Query(),
    ] = [],
    start: Annotated[datetime.datetime | None, Query()] = None,
    end: Annotated[datetime.datetime | None, Query()] = None,
    extra_details: Annotated[ExtraDetails, Query()] = ExtraDetails.NONE,
    media_type: Annotated[str, Header()] = "text/calendar",
) -> Response:
    start_ = time.perf_counter()
    if not course and not module and not location:
        raise HTTPException(
            status_code=400, detail="No course(s), module(s) or location(s) provided."
        )

    if media_type not in {"text/calendar", "application/json"}:
        raise HTTPException(400, "Invalid media type provided.")

    identities = {
        models.CategoryType.PROGRAMMES_OF_STUDY: course,
        models.CategoryType.MODULES: module,
        models.CategoryType.LOCATIONS: location,
    }

    events = await utils.gather_events(identities, start, end, timetable_api)

    if media_type == "text/calendar":
        timetable = utils.to_ics_file(events)
    else:
        assert media_type == "application/json"
        # TODO: handle extra_details
        # display = extra_details is ExtraDetails.ALL
        timetable = msgspec.json.encode(events)

    duration = time.perf_counter() - start_
    metrics.REQUEST_LATENCY.labels(
        endpoint="/v3/timetable/events", used_cache=None
    ).observe(duration)
    metrics.EVENTS_COUNT.labels(
        category_type=",".join(
            sorted(
                [category_type.name for category_type, ids in identities.items() if ids]
            )
        )
    ).observe(len(events))

    return Response(
        content=timetable,
        media_type=media_type,
    )


cns_router = APIRouter(prefix="/cns")


@cns_router.get("/category/{category_type}/items")
async def get_cns_category_items(
    cns_api: Annotated[CNSAPI, Depends(get_cns_api)],
    category_type: Annotated[cns.GroupType, Path()],
    query: Annotated[str | None, Query()] = None,
) -> Response:
    start = time.perf_counter()
    used_cache: bool = True

    items = await cns_api.get_group_items(category_type, query)
    if not items:
        used_cache = False
        items = await cns_api.fetch_group_items(category_type, query)

    data = msgspec.json.encode(items)

    duration = time.perf_counter() - start
    metrics.REQUEST_LATENCY.labels(
        endpoint="/v3/cns/category/:category_type/items", used_cache=used_cache
    ).observe(duration)

    return Response(
        content=data,
        media_type="application/json",
    )


@cns_router.get("/category/{category_type}/items/{item_id}")
async def get_cns_category_item(
    cns_api: Annotated[CNSAPI, Depends(get_cns_api)],
    category_type: Annotated[cns.GroupType, Path()],
    item_id: Annotated[str, Path()],
) -> Response:
    start = time.perf_counter()
    used_cache: bool = True

    item = await cns_api.get_item(item_id)
    if not item:
        used_cache = False
        item = await cns_api.fetch_item(category_type, item_id)

    data = msgspec.json.encode(item)

    duration = time.perf_counter() - start
    metrics.REQUEST_LATENCY.labels(
        endpoint="/v3/cns/category/:category_type/items/:item_id", used_cache=used_cache
    ).observe(duration)

    return Response(
        content=data,
        media_type="application/json",
    )


@cns_router.get(
    "/events",
)
async def get_cns_calendar_events(
    cns_api: Annotated[CNSAPI, Depends(get_cns_api)],
    society: Annotated[list[str], Query()] = [],
    club: Annotated[list[str], Query()] = [],
) -> Response:
    start = time.perf_counter()

    if not (society or club):
        raise HTTPException(
            status_code=400, detail="No club(s) or society(s) provided."
        )

    events: dict[str, list[cns.Event | cns.Activity | cns.Fixture]] = (
        collections.defaultdict(list)
    )

    for group_type, ids in (
        (cns.GroupType.SOCIETY, society),
        (cns.GroupType.CLUB, club),
    ):
        for item_id in ids:
            item = await cns_api.get_item(item_id)
            if not item:
                item = await cns_api.fetch_item(group_type, item_id)

            events_ = await cns_api.get_group_events_activities_fixtures(item_id)
            if events_ is None:
                events_ = await cns_api.fetch_group_events_activities_fixtures(
                    group_type, item_id
                )

            events[item.name].extend(events_)

    calendar = cns.generate_ical_file(events)

    duration = time.perf_counter() - start
    metrics.REQUEST_LATENCY.labels(endpoint="/v3/cns/events", used_cache=None).observe(
        duration
    )

    return Response(
        content=calendar,
        media_type="text/calendar",
    )

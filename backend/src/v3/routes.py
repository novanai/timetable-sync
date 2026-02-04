import collections
import datetime
import enum
import logging
from typing import Annotated
from uuid import UUID

import msgspec
from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Response
from timetable import cns, models, utils
from timetable.api import API as TimetableAPI  # noqa: N811
from timetable.cns import API as CNSAPI

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
    category = await timetable_api.get_category(
        category_type.to_model(), query=query, items_type=models.BasicCategoryItem
    )
    if not category:
        category = await timetable_api.fetch_category(
            category_type.to_model(), query=query, items_type=models.BasicCategoryItem
        )

    return Response(
        content=msgspec.json.encode(category.items),
        media_type="application/json",
    )


@timetable_router.get("/category/{category_type}/items/{item_id}")
async def get_timetable_category_item(
    timetable_api: Annotated[TimetableAPI, Depends(get_timetable_api)],
    category_type: Annotated[CategoryType, Path()],
    item_id: Annotated[UUID, Path()],
) -> Response:
    item = await timetable_api.get_category_item(
        str(item_id)
    ) or await timetable_api.fetch_category_item(category_type.to_model(), str(item_id))
    return Response(
        content=msgspec.json.encode(item),
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
    if media_type not in {"text/calendar", "application/json"}:
        raise HTTPException(400, "Invalid media type provided.")

    identities = {category_type.to_model(): [str(item_id)]}
    events = await utils.gather_events(identities, start, end, timetable_api)

    if media_type == "text/calendar":
        timetable = utils.generate_ical_file(events)
    else:
        assert media_type == "application/json"
        # TODO: handle extra_details
        # display = extra_details is ExtraDetails.ALL
        timetable = msgspec.json.encode(events)

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
    if not course and not module and not location:
        raise HTTPException(
            status_code=400, detail="No course(s), module(s) or location(s) provided."
        )

    if media_type not in {"text/calendar", "application/json"}:
        raise HTTPException(400, "Invalid media type provided.")

    identities = {
        models.CategoryType.PROGRAMMES_OF_STUDY: [str(id_) for id_ in course],
        models.CategoryType.MODULES: [str(id_) for id_ in module],
        models.CategoryType.LOCATIONS: [str(id_) for id_ in location],
    }

    events = await utils.gather_events(identities, start, end, timetable_api)

    if media_type == "text/calendar":
        timetable = utils.generate_ical_file(events)
    else:
        assert media_type == "application/json"
        # TODO: handle extra_details
        # display = extra_details is ExtraDetails.ALL
        timetable = msgspec.json.encode(events)

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
    items = await cns_api.get_group_items(category_type, query)
    if not items:
        items = await cns_api.fetch_group_items(category_type, query)

    return Response(
        content=msgspec.json.encode(items),
        media_type="application/json",
    )


@cns_router.get("/category/{category_type}/items/{item_id}")
async def get_cns_category_item(
    cns_api: Annotated[CNSAPI, Depends(get_cns_api)],
    category_type: Annotated[cns.GroupType, Path()],
    item_id: Annotated[str, Path()],
) -> Response:
    item = await cns_api.get_item(item_id)
    if not item:
        item = await cns_api.fetch_item(category_type, item_id)

    return Response(
        content=msgspec.json.encode(item),
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

    return Response(
        content=calendar,
        media_type="text/calendar",
    )

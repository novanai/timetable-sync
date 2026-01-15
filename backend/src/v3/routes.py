import collections
import datetime
import enum
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Response
from timetable import cns, models, utils
from timetable.api import API as TimetableAPI  # noqa: N811
from timetable.cns import API as CNSAPI

from src.dependencies import get_cns_api, get_timetable_api


class ExtraDetails(enum.Enum):
    NONE = "none"
    ALL = "all"
    ONLY = "only"


timetable_router = APIRouter(prefix="/timetable")


@timetable_router.get("/category/{category_type}/items")
async def get_timetable_category_items(
    timetable_api: Annotated[TimetableAPI, Depends(get_timetable_api)],
    category_type: Annotated[models.CategoryType, Path()],
    query: Annotated[str | None, Query()] = None,
) -> list[utils.BasicCategoryItem]:
    return await utils.get_basic_category_items(timetable_api, category_type, query)


@timetable_router.get("/category/{category_type}/items/{item_id}")
async def get_timetable_category_item(
    timetable_api: Annotated[TimetableAPI, Depends(get_timetable_api)],
    category_type: Annotated[models.CategoryType, Path()],
    item_id: Annotated[UUID, Path()],
) -> models.CategoryItem:
    return await timetable_api.get_category_item(
        category_type, str(item_id)
    ) or await timetable_api.fetch_category_item(category_type, str(item_id))


@timetable_router.get("/category/{category_type}/items/{item_id}/events")
async def get_timetable_category_item_events(
    timetable_api: Annotated[TimetableAPI, Depends(get_timetable_api)],
    category_type: Annotated[models.CategoryType, Path()],
    item_id: Annotated[UUID, Path()],
    start: Annotated[datetime.datetime | None, Query()] = None,
    end: Annotated[datetime.datetime | None, Query()] = None,
    extra_details: Annotated[ExtraDetails, Query()] = ExtraDetails.NONE,
    media_type: Annotated[str, Header()] = "text/calendar",
) -> Response:
    if media_type not in {"text/calendar", "application/json"}:
        raise HTTPException(400, "Invalid media type provided.")

    identities = {category_type: [str(item_id)]}
    events = await utils.gather_events(identities, start, end, timetable_api)

    if media_type == "text/calendar":
        timetable = utils.generate_ical_file(events)
    else:
        assert media_type == "application/json"
        # TODO: handle extra_details
        display = extra_details is ExtraDetails.ALL
        timetable = utils.generate_json_file(events, display)

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
        display = extra_details is ExtraDetails.ALL
        timetable = utils.generate_json_file(events, display)

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
) -> list[utils.BasicCategoryItem]:
    categories = await cns_api.fetch_unlocked_groups(category_type)

    if query:
        categories = cns.filter_category_results(categories, query)

    return categories


@cns_router.get("/category/{category_type}/items/{item_id}")
async def get_cns_category_item(
    cns_api: Annotated[CNSAPI, Depends(get_cns_api)],
    category_type: Annotated[cns.GroupType, Path()],
    item_id: Annotated[UUID, Path()],
) -> utils.BasicCategoryItem:
    return await cns_api.fetch_group_info(category_type, str(item_id))


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
            status_code=400, detail="No society(s) or club(s) provided."
        )

    events: dict[str, list[cns.Event | cns.Activity | cns.Fixture]] = (
        collections.defaultdict(list)
    )

    for group_type, ids in (
        (cns.GroupType.SOCIETY, society),
        (cns.GroupType.CLUB, club),
    ):
        for id_ in ids:
            group = await cns_api.fetch_group_info(group_type, id_)
            events[group.name].extend(
                await cns_api.fetch_group_events_activities_fixtures(group_type, id_)
            )

    calendar = cns.generate_ical_file(events)

    return Response(
        content=calendar,
        media_type="text/calendar",
    )

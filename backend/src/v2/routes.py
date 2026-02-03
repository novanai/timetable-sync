import collections
import datetime
from typing import Annotated

import msgspec
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from timetable import cns, models, utils
from timetable.api import API as TimetableAPI  # noqa: N811
from timetable.cns import API as CNSAPI

from src.dependencies import get_cns_api, get_timetable_api

router = APIRouter()


def str_to_list(text: str) -> list[str]:
    return [t.strip() for t in text.split(",")]


CATEGORY_TYPES: dict[str, models.CategoryType] = {
    "course": models.CategoryType.PROGRAMMES_OF_STUDY,
    "module": models.CategoryType.MODULES,
    "location": models.CategoryType.LOCATIONS,
}


@router.get("/all/{category_type}")
async def get_all_category_items(
    timetable_api: Annotated[TimetableAPI, Depends(get_timetable_api)],
    cns_api: Annotated[CNSAPI, Depends(get_cns_api)],
    category_type: Annotated[str, Path()],
    query: Annotated[str | None, Query()] = None,
) -> Response:
    if category_type not in ("course", "module", "location", "club", "society"):
        raise HTTPException(status_code=400, detail="Invalid value provided.")

    if category_type in CATEGORY_TYPES:
        category = await timetable_api.get_category(
            CATEGORY_TYPES[category_type],
            query=query,
            items_type=models.BasicCategoryItem,
        )
        if not category:
            category = await timetable_api.fetch_category(
                CATEGORY_TYPES[category_type],
                query=query,
                items_type=models.BasicCategoryItem,
            )

        items = category.items

    else:
        group_type = cns.GroupType(category_type)
        items = await cns_api.get_group_items(group_type, query)
        if not items:
            items = await cns_api.fetch_group_items(group_type, query)

        items = [
            models.BasicCategoryItem(name=item.name, identity=item.id) for item in items
        ]

    return Response(
        content=msgspec.json.encode(items),
        media_type="application/json",
    )


@router.get(
    "/",
    summary="Generate a timetable.",
    description="One of 'course', 'courses' or 'modules' must be provided, but not both. All other parameters are optional.",
)
async def get_calendar_events(
    timetable_api: Annotated[TimetableAPI, Depends(get_timetable_api)],
    course: Annotated[  # NOTE: backwards compatibility only
        str | None,
        Query(
            description="The course to generate a timetable for.",
            examples=["COMSCI1"],
            deprecated=True,
        ),
    ] = None,
    courses: Annotated[
        str | None,
        Query(
            description="The course(s) to generate a timetable for.",
            examples=["COMSCI1,COMSCI2"],
        ),
    ] = None,
    modules: Annotated[
        str | None,
        Query(
            description="The module(s) to generate a timetable for.",
            examples=["CSC1061,CSC1003,MTH1025"],
        ),
    ] = None,
    locations: Annotated[
        str | None,
        Query(
            description="The location(s) to generate a timetable for.",
            examples=["GLA.SA101,SPC.E203"],
        ),
    ] = None,
    _format: Annotated[
        str | None,
        Query(
            alias="format",
            description="The response format.\n\nAllowed values: 'ical' or 'json'.\nDefault: 'ical'.",
            examples=["json"],
        ),
    ] = None,
    display: Annotated[
        bool | None,
        Query(
            description="Deprecated. Display details are included regardless.\n\nWhether or not to include additional display info.",
            examples=["true"],
            deprecated=True,
        ),
    ] = None,
    start: Annotated[
        str | None,
        Query(
            description="Only get timetable events later than this datetime.",
            examples=["2023-10-31T13:00:00"],
        ),
    ] = None,
    end: Annotated[
        str | None,
        Query(
            description="Only get timetable events earlier than this datetime.",
            examples=["2024-04-23T10:00:00"],
        ),
    ] = None,
) -> Response:
    if _format is None:
        _format = "ical"

    if _format not in {"ical", "json"}:
        raise HTTPException(status_code=400, detail=f"Invalid format '{_format}'.")

    if not course and not courses and not modules and not locations:
        raise HTTPException(
            status_code=400, detail="No courses, modules or locations provided."
        )

    start_date = datetime.datetime.fromisoformat(start) if start else None
    end_date = datetime.datetime.fromisoformat(end) if end else None

    codes: dict[models.CategoryType, list[str]] = collections.defaultdict(list)

    if courses and courses.strip():
        codes[models.CategoryType.PROGRAMMES_OF_STUDY].extend(str_to_list(courses))
    if course and course.strip() not in codes[models.CategoryType.PROGRAMMES_OF_STUDY]:
        codes[models.CategoryType.PROGRAMMES_OF_STUDY].append(course.strip())
    if modules:
        codes[models.CategoryType.MODULES].extend(str_to_list(modules))
    if locations:
        codes[models.CategoryType.LOCATIONS].extend(str_to_list(locations))

    items = await utils.resolve_to_category_items(codes, timetable_api)
    identities = {
        group: [item.identity for item in group_items]
        for group, group_items in items.items()
    }
    events = await utils.gather_events(identities, start_date, end_date, timetable_api)

    if _format == "ical":
        timetable = utils.generate_ical_file(events)
        return Response(
            content=timetable,
            media_type="text/calendar",
        )
    assert _format == "json"
    return Response(
        content=msgspec.json.encode(events),
        media_type="application/json",
    )


@router.get("/cns")
async def get_cns_calendar_events(
    cns_api: Annotated[CNSAPI, Depends(get_cns_api)],
    societies: Annotated[str | None, Query()] = None,
    clubs: Annotated[str | None, Query()] = None,
) -> Response:
    if not (societies or clubs):
        raise HTTPException(status_code=400, detail="No societies or clubs provided.")

    society_ids = str_to_list(societies) if societies else []
    club_ids = str_to_list(clubs) if clubs else []

    events: dict[str, list[cns.Event | cns.Activity | cns.Fixture]] = (
        collections.defaultdict(list)
    )

    for group_type, ids in (
        (cns.GroupType.SOCIETY, society_ids),
        (cns.GroupType.CLUB, club_ids),
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

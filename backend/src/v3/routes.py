from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from timetable import models, utils
from timetable.api import API as TimetableAPI  # noqa: N811

from src.dependencies import get_timetable_api

timetable_router = APIRouter(prefix="/timetable")


@timetable_router.get("/{category_type}/{item_id}")
async def get_category_item(
    timetable_api: Annotated[TimetableAPI, Depends(get_timetable_api)],
    category_type: Annotated[models.CategoryType, Path()],
    item_id: Annotated[UUID, Path()],
) -> models.CategoryItem:
    return await timetable_api.get_category_item(category_type, str(item_id)) or await timetable_api.fetch_category_item(category_type, str(item_id))


@timetable_router.get("/{category_type}")
async def get_category_items(
    timetable_api: Annotated[TimetableAPI, Depends(get_timetable_api)],
    category_type: Annotated[models.CategoryType, Path()],
    query: Annotated[str | None, Query()] = None,
) -> list[utils.BasicCategoryItem]:
    return await utils.get_basic_category_items(timetable_api, category_type, query)

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from timetable import utils
from timetable.models import CategoryType

from src.dependencies import get_cns_api, get_timetable_api
from src.v2.routes import router as v2_router
from src.v3.routes import timetable_router as v3_timetable_router

import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    get_timetable_api_context = asynccontextmanager(get_timetable_api)
    async with get_timetable_api_context() as timetable_api:
        for category_type in (
            CategoryType.PROGRAMMES_OF_STUDY,
            CategoryType.MODULES,
            CategoryType.LOCATIONS,
        ):
            logger.info(f"loading {category_type.name}...")
            await utils.get_basic_category_items(timetable_api, category_type)
            
    logger.info("loaded all")

    yield

    async with get_timetable_api_context() as timetable_api:
        await timetable_api.session.close()

    get_cns_api_context = asynccontextmanager(get_cns_api)
    async with get_cns_api_context() as cns_api:
        await cns_api.session.close()


OPENAPI_TAGS = [
    {"name": "v2", "description": "Deprecated"},
    {"name": "v3", "description": "Latest"},
]

app = FastAPI(
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)
app.include_router(v2_router, prefix="/api", tags=["v2"], deprecated=True)
app.include_router(v3_timetable_router, prefix="/api/v3", tags=["v3"])


@app.get("/api/healthcheck")
async def healthcheck() -> str:
    return ":3"

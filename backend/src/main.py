import asyncio
import datetime
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Awaitable, Callable

import glide
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from timetable.api import API as TimetableAPI  # noqa: N811
from timetable.cache import ValkeyCache
from timetable.cns import API as CNSAPI
from timetable.cns import GroupType
from timetable.models import BasicCategoryItem, CategoryType

from src import metrics
from src.metrics import router as metrics_router
from src.v2.routes import router as v2_router
from src.v3.routes import cns_router as v3_cns_router
from src.v3.routes import timetable_router as v3_timetable_router

logger = logging.getLogger(__name__)

CACHE_READY = asyncio.Event()


async def load_all_categories_to_cache(
    timetable_api: TimetableAPI, cns_api: CNSAPI
) -> None:
    for category_type in (
        CategoryType.PROGRAMMES_OF_STUDY,
        CategoryType.MODULES,
        CategoryType.LOCATIONS,
    ):
        logger.info(f"loading timetable category '{category_type.name}'")

        if not (
            await timetable_api.get_category(
                category_type, items_type=BasicCategoryItem
            )
        ):
            await timetable_api.fetch_category(
                category_type, items_type=BasicCategoryItem
            )

    logger.info("loaded all timetable categories")

    for group_type in (GroupType.CLUB, GroupType.SOCIETY):
        logger.info(f"loading cns category '{group_type.name}'")

        if not (await cns_api.get_group_items(group_type)):
            await cns_api.fetch_group_items(group_type)

    logger.info("loaded all cns categories")


async def populate_cache(timetable_api: TimetableAPI, cns_api: CNSAPI) -> None:
    client = timetable_api.cache.client

    if await client.exists(["cache_ready"]):
        CACHE_READY.set()
        logger.info("cache ready")
        return

    got_lock = await client.set(
        "cache_loading",
        "1",
        conditional_set=glide.ConditionalChange.ONLY_IF_DOES_NOT_EXIST,
        expiry=glide.ExpirySet(glide.ExpiryType.SEC, datetime.timedelta(seconds=150)),
    )

    if got_lock:
        try:
            await load_all_categories_to_cache(timetable_api, cns_api)
            await client.set(
                "cache_ready",
                "1",
                expiry=glide.ExpirySet(
                    glide.ExpiryType.SEC, datetime.timedelta(days=1)
                ),
            )

            CACHE_READY.set()

        finally:
            await client.delete(["cache_loading"])

        return

    logger.info("waiting for cache")

    await CACHE_READY.wait()

    logger.info("cache ready")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    valkey_cache = await ValkeyCache.create(
        os.environ["VALKEY_HOST"], int(os.environ["VALKEY_PORT"])
    )
    timetable_api = TimetableAPI(valkey_cache)
    cns_api = CNSAPI(os.environ["CNS_ADDRESS"], valkey_cache)

    await populate_cache(timetable_api, cns_api)

    app.state.timetable_api = timetable_api
    app.state.cns_api = cns_api

    yield

    await timetable_api.session.close()
    await cns_api.session.close()


OPENAPI_TAGS = [
    {"name": "v3", "description": "Latest"},
    {"name": "v2", "description": "Deprecated"},
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
app.include_router(v3_cns_router, prefix="/api/v3", tags=["v3"])
app.include_router(metrics_router, prefix="/api", tags=["metrics"])

ORIGINS = [
    "https://timetable.redbrick.dcu.ie",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/healthcheck")
@metrics.REQUEST_LATENCY.labels(endpoint="healthcheck", used_cache=None).time()
async def healthcheck() -> str:
    return ":3"


@app.middleware("http")
async def log_request_process_times(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    metrics.USER_AGENT_COUNT.labels(user_agent=request.headers["User-Agent"]).inc()
    return response

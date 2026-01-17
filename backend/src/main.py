import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Awaitable, Callable

from fastapi import FastAPI, Request, Response
from timetable import utils
from timetable.models import CategoryType
from fastapi.middleware.cors import CORSMiddleware

from src.dependencies import get_cns_api, get_timetable_api
from src.v2.routes import router as v2_router
from src.v3.routes import cns_router as v3_cns_router
from src.v3.routes import timetable_router as v3_timetable_router

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
            logger.info(f"loading category '{category_type.name}'")
            await utils.get_basic_category_items(timetable_api, category_type)

    logger.info("loaded all categories")

    yield

    async with get_timetable_api_context() as timetable_api:
        await timetable_api.session.close()

    get_cns_api_context = asynccontextmanager(get_cns_api)
    async with get_cns_api_context() as cns_api:
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

# TODO: for testing only, remove before prod
origins = [
    "http://localhost",
    "http://localhost:5173",
    "https://timetable.redbrick.dcu.ie",
    "https://timetable-test.redbrick.dcu.ie",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/healthcheck")
async def healthcheck() -> str:
    return ":3"


@app.middleware("http")
async def log_request_process_times(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start_time = time.perf_counter()
    response = await call_next(request)
    end_time = time.perf_counter()
    execution_time_ms = (end_time - start_time) * 1000

    logger.info(f"request to '{request.url.path}?{request.url.query}' took {execution_time_ms:.4f} ms")

    return response

from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
    multiprocess,
)

router = APIRouter()


REQUEST_LATENCY = Histogram(
    "request_duration_seconds",
    "HTTP request latency",
    labelnames=["endpoint", "used_cache"],
)

USER_AGENT_COUNT = Counter(
    "user_agent_counter",
    "User Agent counter",
    labelnames=["user_agent"],
)

EVENTS_CATEGORY_IDENTITY_COUNT = Counter(
    "events_category_identity_counter",
    "Events category identity counts",
    labelnames=["name", "identity"],
)

EVENTS_COUNT = Histogram(
    "events_per_request",
    "Number of events per request",
    labelnames=["category_type"],
    buckets=[
        1,
        2,
        5,
        10,
        15,
        20,
        25,
        30,
        40,
        50,
        75,
        100,
        125,
        150,
        175,
        200,
        225,
        250,
        275,
        300,
        325,
        350,
        375,
        400,
        450,
        500,
        600,
        700,
        800,
        900,
        1000,
        1100,
        1200,
        1300,
        1400,
        1500,
        1600,
        1700,
        1800,
        1900,
        2000,
    ],
)


@router.get("/metrics")
async def metrics() -> Response:
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

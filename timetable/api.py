import asyncio
import datetime
import difflib
import typing
import orjson

import aiohttp

from timetable import cache as cache_
from timetable import logger, models

BASE_URL = "https://scientia-eu-v4-api-d1-03.azurewebsites.net/api/Public"

INSTITUTION_IDENTITY = "a1fdee6b-68eb-47b8-b2ac-a4c60c8e6177"
MODULES = "525fe79b-73c3-4b5c-8186-83c652b3adcc"
LOCATIONS = "1e042cb1-547d-41d4-ae93-a1f2c3d34538"
PROGRAMMES_OF_STUDY = "241e4d36-60e0-49f8-b27e-99416745d98d"


session: aiohttp.ClientSession | None = None
"""The ClientSession to use for requests. Must be initialised when starting the web server,
and closed when shutting down the web server.
"""


async def get_data(
    path: str,
    params: dict[str, str] | None = None,
    json_data: dict[str, typing.Any] | None = None,
) -> dict[str, typing.Any]:
    """Get data from the api.

    Parameters
    ----------
    path : str
        The API path.
    params : dict[str, str] | None, default None
        Request parameters.
    json_data: dict[str, Any] | None, default None
        Request data.

    Returns
    -------
    dict[str, Any]
        The fetched data.
    """
    # TODO: replace this monstrosity with something more sane
    global session
    if session is None:
        raise RuntimeError("session not initialised")

    retries = 0
    while True:
        async with session.request(
            "POST",
            f"{BASE_URL}/{path}",
            params=params,
            headers={"Authorization": "Anonymous", "Content-type": "application/json"},
            json=json_data,
        ) as res:
            if not res.ok:
                retries += 1
                await asyncio.sleep(5)
                continue

            if retries == 3:
                logger.error(
                    f"API Error: {res.status} {res.content_type} {(await res.read()).decode()}"
                )
                res.raise_for_status()

            data = await res.json(loads=orjson.loads)
            return data


async def fetch_category_results(
    identity: models.CategoryType, query: str | None = None, cache: bool = True
) -> models.Category:
    """Fetch results for a certain category type.

    Parameters
    ----------
    identity : models.CategoryType
        The type of category to get results for
    query : str | None, default None
        A full or partial course code to search for (eg. BUS, COMSCI1)
    cache : bool, default True
        Whether to cache the results.

    Returns
    -------
    models.Category
        The fetched category results. This is not guaranteed to contain any categories.

    Note
    ---
    If query is specified, the results will not be cached.
    """
    results: list[dict[str, typing.Any]] = []

    params: dict[str, str] = {
        "pageNumber": "1",
        "query": query or "",
    }

    data = await get_data(
        f"CategoryTypes/{identity.value}/Categories/FilterWithCache/{INSTITUTION_IDENTITY}",
        params=params,
    )
    total_pages = data["TotalPages"]
    results.extend(data["Results"])
    count = data["Count"]

    if total_pages > 1:
        data = await asyncio.gather(
            *(
                get_data(
                    f"CategoryTypes/{identity.value}/Categories/FilterWithCache/{INSTITUTION_IDENTITY}",
                    params={
                        "pageNumber": str(i),
                        "query": query or "",
                    },
                )
                for i in range(2, total_pages + 1)
            ),
            return_exceptions=True,
        )
        for d in data:
            if isinstance(d, BaseException):
                raise d

            results.extend(d["Results"])

    if not query and cache:
        await cache_.default.set(
            identity.value,
            {
                "TotalPages": total_pages,
                "Results": results,
                "Count": count,
            },
        )

    return models.Category.from_payload({"Results": results, "Count": count})


async def get_category_results(
    identity: models.CategoryType, query: str | None = None
) -> models.Category | None:
    """Get results for a certain category type, if cached.

    Parameters
    ----------
    identity : models.CategoryType
        The type of category to get results for
    query : str | None, default None
        A full or partial course code to search for (eg. BUS, COMSCI1)

    Returns
    -------
    models.Category
        If the category was cached and is not outdated.
    None
        If the category was not cached or is outdated.
    """
    data = await cache_.default.get(identity.value)
    if data is None:
        return None

    results = models.Category.from_payload(data)

    if query:
        return models.Category(
            _filter_categories_for(results, query),
            data["Count"],
        )

    return results


def _filter_categories_for(
    results: models.Category,
    query: str,
) -> list[models.CategoryItem]:
    """Filter cached results for `query`.

    Parameters
    ----------
    results : models.Category
        The category to filter though.
    query : str
        The query to filter for. Checks only against the category's name.

    Returns
    -------
    list[models.CategoryItem]
        The items which matched the search query with a greater then 0.8 match,
        sorted from highest match to lowest.
    """
    ratios: list[tuple[float, models.CategoryItem]] = []

    for cat in results.categories:
        # TODO: this matching algorithm is not what we want, as it only
        # works on courses (whose names are just the course code)
        ratio = difflib.SequenceMatcher(a=cat.name, b=query).ratio()
        ratios.append((ratio, cat))
    filtered = filter(lambda r: r[0] > 0.8, ratios)
    sort = sorted(filtered, key=lambda r: r[0], reverse=True)
    result = [r[1] for r in sort]

    return result


async def fetch_category_timetable(
    category_type: models.CategoryType,
    category_identities: list[str],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    cache: bool = True,
) -> list[models.CategoryItemTimetable]:
    """Fetch the timetable for category_identities belonging to category_type.

    Parameters
    ----------
    category_type : models.CategoryType
        The type of category to get results in.
    category_identities : list[str]
        The identities of the categories to get timetables for.
    start : datetime.datetime | None, default 2023-9-11
        The start date/time of the timetable.
    end : datetime.datetime | None, default 2024-5-5
        The end date/time of the timetable.
    cache : bool, default True
        Whether to cache the results. If start or end is specified, cache is set to False.

    Returns
    -------
    list[models.CategoryItemTimetable]
        The requested timetables.
    """
    if start or end:
        cache = False

    if not start:
        start = datetime.datetime(2023, 9, 11)
    if not end:
        end = datetime.datetime(2024, 4, 14)

    if start > end:
        raise ValueError("Start time cannot be later than end time")

    start = start.astimezone(datetime.UTC).replace(tzinfo=None)
    end = end.astimezone(datetime.UTC).replace(tzinfo=None)

    data = await get_data(
        f"CategoryTypes/Categories/Events/Filter/{INSTITUTION_IDENTITY}",
        params={
            "startRange": f"{start.isoformat()}Z",
            "endRange": f"{end.isoformat()}Z",
        },
        json_data={
            "ViewOptions": {
                "Days": [
                    {"DayOfWeek": 1},
                    {"DayOfWeek": 2},
                    {"DayOfWeek": 3},
                    {"DayOfWeek": 4},
                    {"DayOfWeek": 5},
                ],
            },
            "CategoryTypesWithIdentities": [
                {
                    "CategoryTypeIdentity": category_type.value,
                    "CategoryIdentities": category_identities,
                }
            ],
        },
    )

    timetables: list[models.CategoryItemTimetable] = []
    for timetable in data["CategoryEvents"]:
        timetables.append(models.CategoryItemTimetable.from_payload(timetable))

        if cache:
            await cache_.default.set(
                timetable["Identity"],
                timetable,
                expires_in=datetime.timedelta(seconds=43200),  # 12 hours
            )

    return timetables


async def get_category_timetable(
    category_identity: str,
) -> models.CategoryItemTimetable | None:
    """Get the timetable for category_identity.

    Parameters
    ----------
    category_identity : str
        The identity of the category to get the timetable for.

    Returns
    -------
    models.CategoryItemTimetable
        If the timetable was cached and is not outdated.
    None
        If the timetable was not cached or is outdated.
    """
    data = await cache_.default.get(category_identity)
    if data is None:
        return None

    return models.CategoryItemTimetable.from_payload(data)

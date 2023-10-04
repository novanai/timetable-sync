import datetime
import difflib
import json
import os
import typing

import aiofile
import aiohttp

from timetable import models, utils

BASE_URL = "https://scientia-eu-v4-api-d1-03.azurewebsites.net/api/Public"

INSTITUTION_IDENTITY = "a1fdee6b-68eb-47b8-b2ac-a4c60c8e6177"
MODULES = "525fe79b-73c3-4b5c-8186-83c652b3adcc"
LOCATIONS = "1e042cb1-547d-41d4-ae93-a1f2c3d34538"
PROGRAMMES_OF_STUDY = "241e4d36-60e0-49f8-b27e-99416745d98d"


async def get_data(
    path: str,
    params: dict[str, str] | None = None,
    json_data: dict[str, typing.Any] | None = None,
) -> dict[str, typing.Any]:
    """Get data from the api."""
    async with aiohttp.request(
        "POST",
        f"{BASE_URL}/{path}",
        params=params,
        headers={"Authorization": "Anonymous", "Content-type": "application/json"},
        json=json_data,
    ) as res:
        if not res.ok:
            if res.content_type == "application/json":
                data = await res.json()
                print("Error:", data)

            res.raise_for_status()

        data = await res.json()
        return data


async def fetch_category_results(
    identity: models.CategoryType, query: str | None = None, cache: bool = True
) -> models.CategoryResults:
    """Fetch results for a certain category type.

    Parameters
    ----------
    identity : models.CategoryType
        The type of category to get results for
    query : str | None, default None
        A full or partial course code to search for (eg. BUS, COMSCI1)
    cache : bool, default True
        Whether to cache results.

    !!! NOTE
        If a course code is specified, the results will not be cached.
    """
    total_pages = 0
    current_page = 0
    count = 0
    results: list[dict[str, typing.Any]] = []

    params = {
        "pageNumber": str(current_page + 1),
    }
    if query:
        params["query"] = query

    while current_page < total_pages or current_page == 0:
        data = await get_data(
            f"CategoryTypes/{identity.value}/Categories/FilterWithCache/{INSTITUTION_IDENTITY}",
            params=params,
        )
        total_pages = data["TotalPages"]
        results.extend(data["Results"])
        count = data["Count"]
        current_page += 1

        print(f"Fetched page {current_page}/{total_pages} of category results")

    if not query and cache:
        await utils.cache_data(
            identity.value,
            {
                "TotalPages": total_pages,
                "Results": results,
                "Count": count,
            },
        )

    return models.CategoryResults.from_payload({"Results": results, "Count": count})


async def get_category_results(
    identity: models.CategoryType, query: str | None
) -> models.CategoryResults | None:
    if not os.path.exists(f"./cache/{identity.value}.json"):
        return None

    async with aiofile.async_open(f"./cache/{identity.value}.json", "r") as f:
        data: dict[str, typing.Any] = json.loads(await f.read())

    if (t := data.get("CacheTimestamp")) and t < (
        datetime.datetime.now(datetime.UTC) - datetime.timedelta(weeks=1)
    ).timestamp():
        return None

    results = models.CategoryResults.from_payload(data)

    if query:
        return models.CategoryResults(
            _filter_categories_for(query, results),
            data["Count"],
        )

    return results


def _filter_categories_for(
    query: str, results: models.CategoryResults
) -> list[models.Category]:
    ratios: list[tuple[float, models.Category]] = []

    for cat in results.categories:
        ratio = difflib.SequenceMatcher(a=cat.name, b=query).ratio()
        ratios.append((ratio, cat))
    filtered = filter(lambda r: r[0] > 0.8, ratios)
    sort = sorted(filtered, key=lambda r: r[0], reverse=True)
    result = [r[1] for r in sort]

    return result


async def fetch_category_timetable(
    category_type: models.CategoryType,
    category_identity: str,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    cache: bool = True,
) -> models.CategoryTimetable:
    if start or end:
        cache = False

    if not start:
        start = datetime.datetime(2023, 9, 11)
    if not end:
        end = datetime.datetime(2024, 5, 5)

    if start > end:
        raise ValueError("start time cannot be later than end time")

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
                    "CategoryIdentities": [category_identity],
                }
            ],
        },
    )
    if cache:
        await utils.cache_data(category_identity, data)

    return models.CategoryTimetable.from_payload(data)


async def get_category_timetable(
    category_identity: str,
) -> models.CategoryTimetable | None:
    if not os.path.exists(f"./cache/{category_identity}.json"):
        return None

    async with aiofile.async_open(f"./cache/{category_identity}.json", "r") as f:
        data: dict[str, typing.Any] = json.loads(await f.read())

    if (t := data.get("CacheTimestamp")) and t < (
        datetime.datetime.now(datetime.UTC) - datetime.timedelta(weeks=1)
    ).timestamp():
        return None

    return models.CategoryTimetable.from_payload(data)

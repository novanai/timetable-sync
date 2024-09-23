import asyncio
import datetime
import logging
import typing

import aiohttp
import orjson
from rapidfuzz import fuzz
from rapidfuzz import utils as fuzz_utils

from timetable import __version__, models, utils
from timetable import cache as cache_

logger = logging.getLogger(__name__)

BASE_URL = "https://scientia-eu-v4-api-d1-03.azurewebsites.net/api/Public"

INSTITUTION_IDENTITY = "a1fdee6b-68eb-47b8-b2ac-a4c60c8e6177"
MODULES = "525fe79b-73c3-4b5c-8186-83c652b3adcc"
LOCATIONS = "1e042cb1-547d-41d4-ae93-a1f2c3d34538"
PROGRAMMES_OF_STUDY = "241e4d36-60e0-49f8-b27e-99416745d98d"


class API:
    def __init__(self):
        self._session: aiohttp.ClientSession | None = None
        self.cache = cache_.Cache()

    @property
    def session(self) -> aiohttp.ClientSession:
        """The `aiohttp.ClientSession` to use for API requests."""
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _fetch_data(
        self,
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
        retries = 0
        while True:
            async with self.session.request(
                "POST",
                f"{BASE_URL}/{path}",
                params=params,
                headers={
                    "Authorization": "Anonymous",
                    "Content-type": "application/json",
                    "User-Agent": f"TimetableSync/{__version__} (https://timetable.redbrick.dcu.ie)",
                },
                json=json_data,
            ) as res:
                if not res.ok:
                    if retries == 3:
                        logger.error(
                            f"API Error: {res.status} {res.content_type} {(await res.read()).decode()}"
                        )
                        res.raise_for_status()

                    retries += 1
                    await asyncio.sleep(5)
                    continue

                data = await res.json(loads=orjson.loads)
                return data

    async def fetch_category(
        self,
        category_type: models.CategoryType,
        *,
        query: str | None = None,
        cache: bool | None = None,
    ) -> models.Category:
        # TODO: update example module codes
        """Fetch a category by type.

        Parameters
        ----------
        category_type : models.CategoryType
            The type of category to fetch.
        query : str | None, default None
            A full or partial course, module or location code to search for (eg. BUS, COMSCI1, CA116).
        cache : bool, default True
            Whether to cache the category.

        Returns
        -------
        models.Category
            The fetched category. This is not guaranteed to contain any items.

        Note
        ---
        If query is specified, the category will not be cached.
        """
        if cache is None:
            cache = True

        results: list[dict[str, typing.Any]] = []

        params: dict[str, str] = {
            "pageNumber": "1",
            "query": query.strip() if query else "",
        }

        data = await self._fetch_data(
            f"CategoryTypes/{category_type.value}/Categories/FilterWithCache/{INSTITUTION_IDENTITY}",
            params=params,
        )
        total_pages = data["TotalPages"]
        results.extend(data["Results"])
        count = data["Count"]

        if total_pages > 1:
            data = await asyncio.gather(
                *(
                    self._fetch_data(
                        f"CategoryTypes/{category_type.value}/Categories/FilterWithCache/{INSTITUTION_IDENTITY}",
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

        if (query is None or not query.strip()) and cache:
            await self.cache.set(
                f"category.{category_type.value}",
                {
                    "TotalPages": total_pages,
                    "Results": results,
                    "Count": count,
                },
                expires_in=datetime.timedelta(days=1),
            )

        return models.Category.from_payload({"Results": results, "Count": count})

    async def get_category(
        self,
        category_type: models.CategoryType,
        *,
        query: str | None = None,
        count: int | None = None,
    ) -> models.Category | None:
        """Get a category by type from the cache.

        Parameters
        ----------
        category_type : models.CategoryType
            The type of category to get.
        query : str | None, default None
            A full or partial course, module or location code to search for (eg. BUS, COMSCI1, CA116).
        count : int | None, default None
            The maximum number of category items to include when searching for `query`. If `None` will
            include all matching items. Ignored if no query is provided.

        Returns
        -------
        models.Category
            If the category was cached and is not outdated.
        None
            If the category was not cached or is outdated.
        """
        data = await self.cache.get(f"category.{category_type.value}")
        if data is None:
            return None

        category = models.Category.from_payload(data)

        if query and query.strip():
            filtered = self._filter_category_items_for(category.items, query, count)
            return models.Category(
                filtered,
                len(filtered),
            )

        return category

    def _filter_category_items_for(
        self,
        category_items: list[models.CategoryItem],
        query: str,
        count: int | None,
    ) -> list[models.CategoryItem]:
        """Filter category items for `query`, only returning items with a >80% match.

        Parameters
        ----------
        category_items : list[models.CategoryItem]
            The category items to filter.
        query : str
            The query to filter for. Checks against the category's name and code.
        count : int | None
            The maximum number of category items to include when searching for `query`. If `None` will
            include all matching items.

        Returns
        -------
        list[models.CategoryItem]
            The items which matched the search query with a >80% match,
            sorted from highest match to lowest.
        """
        count = count if count is not None else len(category_items)
        results: typing.Iterable[tuple[models.CategoryItem, float]] = []

        for item in category_items:
            item_ratios = [
                fuzz.partial_ratio(
                    query, item.name, processor=fuzz_utils.default_process
                ),
                fuzz.partial_ratio(
                    query, item.code, processor=fuzz_utils.default_process
                ),
            ]
            results.append((item, max(item_ratios)))

        results = filter(lambda r: r[1] > 80, results)
        results = sorted(results, key=lambda r: r[1], reverse=True)
        return [r[0] for r in results[:count]]

    # TODO: add identical fetch method
    async def get_category_item(
        self,
        category_type: models.CategoryType,
        item_identity: str,
    ) -> models.CategoryItem | None:
        # TODO: add docstring
        category = await self.get_category(category_type)
        if not category:
            return None
        
        try:
            return next(filter(lambda i: i.identity == item_identity, category.items))
        except StopIteration:
            return None

    async def fetch_category_timetables(
        self,
        category_type: models.CategoryType,
        category_identities: list[str],
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
        cache: bool | None = None,
    ) -> list[models.CategoryItemTimetable]:
        """Fetch the timetable for category_identities belonging to category_type.

        Parameters
        ----------
        category_type : models.CategoryType
            The type of category to get timetables in.
        category_identities : list[str]
            The identities of the categories to get timetables for.
        start : datetime.datetime | None, default Sept 1 of the current academic year
            The start date/time of the timetable.
        end : datetime.datetime | None, default May 1 of the current academic year
            The end date/time of the timetable.
        cache : bool, default True
            Whether to cache the timetables. If start or end is specified, cache is set to False.

        Returns
        -------
        list[models.CategoryItemTimetable]
            The requested timetables.
        """
        if cache is None:
            cache = True

        # TODO: move below time conversion and error handling into function to remove duplication
        # TODO: if start is specified, should end default to something else? (e.g. 1 week later)
        start_default, end_default = utils.year_start_end_dates()
        start = (start or start_default).astimezone(datetime.UTC)
        end = (end or end_default).astimezone(datetime.UTC)

        if not (start_default <= start <= end_default) or not (start_default <= end <= end_default):
            raise ValueError("start and end datetimes must be contained within the current academic year range")

        if start > end:
            raise ValueError("Start date/time cannot be later than end date/time")

        data = await self._fetch_data(
            f"CategoryTypes/Categories/Events/Filter/{INSTITUTION_IDENTITY}",
            params={
                "startRange": f"{start_default.isoformat()}Z",
                "endRange": f"{end_default.isoformat()}Z",
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
        for timetable_data in data["CategoryEvents"]:
            timetable = models.CategoryItemTimetable.from_payload(timetable_data)
            timetable.events = list(
                filter(lambda e: start <= e.start <= end, timetable.events)
            )
            timetables.append(timetable)

            if cache:
                # TODO: consider storing data under `{category.identity}.{timetable.identity}`
                await self.cache.set(
                    f"timetable.{timetable.identity}",
                    timetable_data,
                    expires_in=datetime.timedelta(hours=12),
                )

        return timetables

    async def get_category_item_timetable(
        self,
        item_identity: str,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
    ) -> models.CategoryItemTimetable | None:
        """Get the timetable for item_identity.

        Parameters
        ----------
        item_identity : str
            The identity of the category to get the timetable for.
        start : datetime.datetime | None, default Sept 1 of the current academic year
            The start date/time of the timetable.
        end : datetime.datetime | None, default May 1 of the current academic year
            The end date/time of the timetable.

        Returns
        -------
        models.CategoryItemTimetable
            If the timetable was cached and is not outdated.
        None
            If the timetable was not cached or is outdated.
        """
        data = await self.cache.get(f"timetable.{item_identity}")
        if data is None:
            return None

        timetable = models.CategoryItemTimetable.from_payload(data)

        if start or end:
            start_default, end_default = utils.year_start_end_dates()
            start = (start or start_default).astimezone(datetime.UTC)
            end = (end or end_default).astimezone(datetime.UTC)

            if not (start_default <= start <= end_default) or not (start_default <= end <= end_default):
                raise ValueError("start and end datetimes must be contained within the current academic year range")

            if start > end:
                raise ValueError("Start date/time cannot be later than end date/time")

            timetable.events = list(
                filter(lambda e: start <= e.start <= end, timetable.events)
            )

        return timetable

import asyncio
import datetime
import logging
import typing

import aiohttp
import orjson
from rapidfuzz import fuzz
from rapidfuzz import utils as fuzz_utils

from timetable import cache as cache_
from timetable import models, utils

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

    async def fetch_data(
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
                },
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
        self,
        category_type: models.CategoryType,
        query: str | None = None,
        cache: bool | None = None,
    ) -> models.Category:
        # TODO: update example module codes
        """Fetch results for a certain category type.

        Parameters
        ----------
        category_type : models.CategoryType
            The type of category to get results for.
        query : str | None, default None
            A full or partial course or module code to search for (eg. BUS, COMSCI1, CA116).
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
        if cache is None:
            cache = True

        results: list[dict[str, typing.Any]] = []

        params: dict[str, str] = {
            "pageNumber": "1",
            "query": query.strip() if query else "",
        }

        data = await self.fetch_data(
            f"CategoryTypes/{category_type.value}/Categories/FilterWithCache/{INSTITUTION_IDENTITY}",
            params=params,
        )
        total_pages = data["TotalPages"]
        results.extend(data["Results"])
        count = data["Count"]

        if total_pages > 1:
            data = await asyncio.gather(
                *(
                    self.fetch_data(
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
                category_type.value,
                {
                    "TotalPages": total_pages,
                    "Results": results,
                    "Count": count,
                },
                expires_in=datetime.timedelta(days=1),
            )

        return models.Category.from_payload({"Results": results, "Count": count})

    async def get_category_results(
        self,
        category_type: models.CategoryType,
        query: str | None = None,
        count: int | None = None,
    ) -> models.Category | None:
        """Get results for a certain category type, if cached.

        Parameters
        ----------
        category_type : models.CategoryType
            The type of category to get results for.
        query : str | None, default None
            A full or partial course or module code to search for (eg. BUS, COMSCI1, CA116).
        count : int | None, default None
            How many results to return when searching for `query`. Ignored if no query is provided.

        Returns
        -------
        models.Category
            If the category was cached and is not outdated.
        None
            If the category was not cached or is outdated.
        """
        data = await self.cache.get(category_type.value)
        if data is None:
            return None

        results = models.Category.from_payload(data)

        if query:
            return models.Category(
                self._filter_categories_for(results, query, count),
                count if count is not None else len(results.items),
            )

        return results

    def _filter_categories_for(
        self,
        results: models.Category,
        query: str,
        count: int | None,
    ) -> list[models.CategoryItem]:
        """Filter cached results for `query`.

        Parameters
        ----------
        results : models.Category
            The category to filter though.
        query : str
            The query to filter for. Checks against the category's name and description.
        count : int | None
            The number of results to return. If `None` will return all results sorted from
            most similar to least.

        Returns
        -------
        list[models.CategoryItem]
            The items which matched the search query with a greater then 0.8 match,
            sorted from highest match to lowest.
        """
        count = count if count is not None else len(results.items)
        ratios: list[tuple[models.CategoryItem, float]] = []

        for item in results.items:
            item_ratios: list[float] = [
                fuzz.partial_ratio(
                    query, item.name, processor=fuzz_utils.default_process
                ),
                fuzz.partial_ratio(
                    query, item.code, processor=fuzz_utils.default_process
                ),
            ]
            ratios.append((item, max(item_ratios)))

        ratios = sorted(ratios, key=lambda r: r[1], reverse=True)
        return [r[0] for r in ratios[:count]]

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
            The type of category to get results in.
        category_identities : list[str]
            The identities of the categories to get timetables for.
        start : datetime.datetime | None, default Sept 1 of the current academic years
            The start date/time of the timetable.
        end : datetime.datetime | None, default May 1 of the current academic years
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
        elif cache is None:
            cache = True

        # TODO: if start is specified, should end default to something else? (e.g. 1 week later)
        start_default, end_default = utils.year_start_end_dates()
        start = start or start_default
        end = end or end_default

        if start > end:
            raise ValueError("Start date/time cannot be later than end date/time")

        start = start.astimezone(datetime.UTC).replace(tzinfo=None)
        end = end.astimezone(datetime.UTC).replace(tzinfo=None)

        data = await self.fetch_data(
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
                await self.cache.set(
                    timetable["Identity"],
                    timetable,
                    expires_in=datetime.timedelta(hours=12),
                )

        return timetables

    async def get_category_timetable(
        self,
        category_identity: str,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
    ) -> models.CategoryItemTimetable | None:
        """Get the timetable for category_identity.

        Parameters
        ----------
        category_identity : str
            The identity of the category to get the timetable for.
        start : datetime.datetime | None, default Sept 1 of the current academic years
            The start date/time of the timetable.
        end : datetime.datetime | None, default May 1 of the current academic years
            The end date/time of the timetable.

        Returns
        -------
        models.CategoryItemTimetable
            If the timetable was cached and is not outdated.
        None
            If the timetable was not cached or is outdated.
        """
        data = await self.cache.get(category_identity)
        if data is None:
            return None

        timetable = models.CategoryItemTimetable.from_payload(data)

        if start or end:
            start_default, end_default = utils.year_start_end_dates()
            start = start or start_default
            end = end or end_default

            if not start.tzinfo:
                start = start.replace(tzinfo=datetime.UTC)
            if not end.tzinfo:
                end = end.replace(tzinfo=datetime.UTC)

            timetable.events = list(
                filter(lambda e: start <= e.start <= end, timetable.events)
            )

        return timetable

    async def gather_events_for_courses(
        self,
        course_codes: list[str],
        start: datetime.datetime | None,
        end: datetime.datetime | None,
    ) -> list[models.Event]:
        """Fetch timetabled events for multiple courses.

        Parameters
        ----------
        course_codes : str
            The course code(s) to fetch events for.
        start : datetime.datetime | None, default Sept 1 of the current academic year
            The start date/time of the events.
        end : datetime.datetime | None, default May 1 of the current academic year
            The end date/time of the events.

        Returns
        -------
        list[models.Event]
            The events.
        """
        course_identities: list[str] = []

        for code in course_codes:
            course = await self.fetch_category_results(
                models.CategoryType.PROGRAMMES_OF_STUDY,
                code,
            )
            if not course.items:
                raise models.InvalidCodeError(code)

            course_identities.append(course.items[0].identity)

        events: list[models.Event] = []
        to_fetch: list[str] = []

        if start is None and end is None:
            for id_ in course_identities:
                timetable = await self.get_category_timetable(id_, start=start, end=end)
                if timetable:
                    logger.info(
                        f"Using cached events for course {id_} (total {len(timetable.events)})"
                    )
                    events.extend(timetable.events)
                else:
                    to_fetch.append(id_)
        else:
            to_fetch = course_identities

        if to_fetch:
            timetables = await self.fetch_category_timetables(
                models.CategoryType.PROGRAMMES_OF_STUDY,
                to_fetch,
                start=start,
                end=end,
            )
            for timetable in timetables:
                logger.info(
                    f"Fetched events for course {timetable.name} (total {len(timetable.events)})"
                )
                events.extend(timetable.events)

        return events

    async def gather_events_for_modules(
        self,
        module_codes: list[str],
        start: datetime.datetime | None,
        end: datetime.datetime | None,
    ) -> list[models.Event]:
        """Fetch timetabled events for multiple modules.

        Parameters
        ----------
        module_codes : list[str]
            The module code(s) to fetch events for.
        start : datetime.datetime | None, default Sept 1 of the current academic year
            The start date/time of the events.
        end : datetime.datetime | None, default May 1 of the current academic year
            The end date/time of the events.

        Returns
        -------
        list[models.Event]
            The events.
        """
        module_identities: list[str] = []

        for code in module_codes:
            module = await self.fetch_category_results(
                models.CategoryType.MODULES, code, cache=False
            )
            if not module.items:
                raise models.InvalidCodeError(code)

            module_identities.append(module.items[0].identity)

        events: list[models.Event] = []
        to_fetch: list[str] = []

        if start is None and end is None:
            for id_ in module_identities:
                timetable = await self.get_category_timetable(id_, start, end)
                if timetable:
                    logger.info(
                        f"Using cached events for module {id_} (total {len(timetable.events)})"
                    )
                    events.extend(timetable.events)
                else:
                    to_fetch.append(id_)
        else:
            to_fetch = module_identities

        if to_fetch:
            timetables = await self.fetch_category_timetables(
                models.CategoryType.MODULES,
                to_fetch,
                start=start,
                end=end,
                cache=True,
            )
            for timetable in timetables:
                logger.info(
                    f"Fetched events for module {timetable.name} (total {len(timetable.events)})"
                )
                events.extend(timetable.events)

        return events

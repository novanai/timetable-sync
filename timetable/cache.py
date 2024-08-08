import datetime
import os
import typing

import orjson
from redis.asyncio import Redis


class Cache:
    """A simple caching implementation using Redis."""

    def __init__(self):
        self.redis_conn = Redis.from_url(f"redis://{os.environ['REDIS_ADDRESS']}")

    async def set(
        self,
        key: str,
        data: dict[str, typing.Any],
        expires_in: datetime.timedelta | None = None,
    ) -> None:
        """Cache `data` under `key`.

        Parameters
        ----------
        key : str
            A unique identifier of the data being cached.
        data : dict[str, typing.Any]
            The data to cache.
        """
        await self.redis_conn.set(key, orjson.dumps(data))
        if expires_in:
            await self.redis_conn.expire(key, expires_in)

    async def get(self, key: str) -> dict[str, typing.Any] | None:
        """Get data from the cache.

        Parameters
        ----------
        key : str
            The unique key the data is stored under.

        Returns
        -------
        dict[str, typing.Any]
            The data, if found.
        None
            If the data was not found.
        """
        data = await self.redis_conn.get(key)
        if data is None:
            return None

        return orjson.loads(data)

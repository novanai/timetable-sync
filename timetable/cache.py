import json
import os
import typing

from redis.asyncio import Redis


class Cache:
    """A simple caching implementation using Redis."""
    def __init__(self):
        self.redis_conn = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
            f"redis://{os.environ['REDIS_ADDRESS']}"
        )

    async def set(self, key: str, data: dict[str, typing.Any]) -> None:
        """Cache `data` under `key`.
        
        Parameters
        ----------
        key : str
            A unique identifier of the data being cached.
        data : dict[str, Any]
            The data to cache.
        """
        await self.redis_conn.set(  # pyright: ignore[reportUnknownMemberType]
            key, json.dumps(data)
        )

    async def get(self, key: str) -> dict[str, typing.Any] | None:
        """Get data from the cache.
        
        Parameters
        ----------
        key : str
            The unique key the data is stored under.

        Returns
        -------
        dict[str, Any]
            The data, if found.
        None
            If the data was not found.
        """
        data = await self.redis_conn.get(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            key
        )
        if data is None:
            return None

        return json.loads(data)  # pyright: ignore[reportUnknownArgumentType]


default = Cache()
"""Default cache instance."""
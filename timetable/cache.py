import typing
import json
from redis.asyncio import Redis


class Cache:
    def __init__(self):
        self.redis_conn = Redis(host="redis", port=6379, decode_responses=True)

    async def set(self, key: str, data: dict[str, typing.Any]) -> None:
        await self.redis_conn.set(  # pyright: ignore[reportUnknownMemberType]
            key, json.dumps(data)
        )

    async def get(self, key: str) -> dict[str, typing.Any] | None:
        data = await self.redis_conn.get(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            key
        )
        if data is None:
            return None

        return json.loads(data)  # pyright: ignore[reportUnknownArgumentType]


default = Cache()

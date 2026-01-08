from __future__ import annotations

import typing
from contextlib import asynccontextmanager

import asyncpg


class Database:
    def __init__(
        self, host: str, port: str, user: str, password: str, database: str
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database

        self._pool: asyncpg.Pool[asyncpg.Record] | None = None

    @property
    def pool(self) -> asyncpg.Pool[asyncpg.Record]:
        if self._pool is None:
            raise RuntimeError("database was not started")

        return self._pool

    async def start(self) -> None:
        self._pool = await asyncpg.create_pool(
            host=self._host,
            port=self._port,
            user=self._user,
            password=self._password,
            database=self._database,
        )

        async with self.pool.acquire() as conn:
            with open("src/build.sql", "r") as f:
                await conn.execute(f.read())

    @asynccontextmanager
    async def acquire(self) -> typing.AsyncIterator[asyncpg.Connection[asyncpg.Record]]:
        con = await self.pool.acquire()
        try:
            yield con  # pyright: ignore[reportReturnType]
        finally:
            await self.pool.release(con)

    async def stop(self) -> None:
        await self.pool.close()

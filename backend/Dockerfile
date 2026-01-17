FROM python:3.13.3-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN apt-get update && apt-get install -y gcc git

COPY pyproject.toml .
COPY uv.lock .

RUN uv sync --frozen

COPY src src

CMD ["uv", "run", "granian", "--interface", "asgi", "src.main:app", "--loop", "uvloop", "--workers", "4", "--host", "0.0.0.0", "--port", "2000"]

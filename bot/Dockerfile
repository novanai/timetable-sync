FROM python:3.13.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN apt-get update && apt-get install -y python3-icu git

COPY pyproject.toml .
COPY uv.lock .

RUN uv sync --frozen

COPY src src

CMD [ "uv", "run", "-m", "src" ]

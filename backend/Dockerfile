FROM python:3.13.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN apt-get update && apt-get install -y gcc git

COPY pyproject.toml .
COPY uv.lock .

RUN uv sync --frozen

COPY src src

ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]

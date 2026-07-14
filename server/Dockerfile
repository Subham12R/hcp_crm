FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

CMD sh -c 'uv run --no-sync alembic upgrade head && uv run --no-sync python -m app.seed && uv run --no-sync uvicorn main:app --host 0.0.0.0 --port 8000'

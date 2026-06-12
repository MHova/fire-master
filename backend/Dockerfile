FROM python:3.12-slim

# Install system dependencies for asyncpg and psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app/backend

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync

# Copy application code
COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

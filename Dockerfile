# Use the official uv image for dependency management
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-install-project

# Ensure production dependencies are added
RUN uv add gunicorn libsql-client python-dotenv

# --- Final Stage ---
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY . .

# Railway provides the PORT environment variable
EXPOSE 5000

ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# Railway dynamically assigns a port; gunicorn should listen on 0.0.0.0:${PORT:-5000}
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} app:app

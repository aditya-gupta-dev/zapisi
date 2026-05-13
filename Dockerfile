# Use the official uv image for a more robust build
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set the working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies system-wide in the container
# This ensures gunicorn is definitely in the PATH
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy the application code
COPY . .

# Set environment variables
ENV FLASK_APP=app.py

# Railway dynamically assigns a port
EXPOSE 5000

# Use gunicorn with the dynamic Railway port
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} app:app

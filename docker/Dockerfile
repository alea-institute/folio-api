FROM ubuntu:24.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set up non-root user
RUN groupadd -r app && useradd -r -g app app -d /app

# Switch to app user
USER app
WORKDIR /app

# Install uv using the curl install script
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Update path
ENV PATH="/app/.local/bin/:$PATH"

# Install Python tools with uv
RUN uv python install 3.12 \
    && \
    uv tool install pipx \
    && \
    uv tool install poetry \
    && \
    uv tool install pip

# Copy dependency files first for better layer caching
COPY --chown=app:app pyproject.toml ./
COPY --chown=app:app README.md ./

# Install dependencies
RUN bash -l -c "uv sync --upgrade && uv venv && uv run python"

# Copy application code
COPY --chown=app:app folio_api folio_api
COPY --chown=app:app config.json.example ./config.json.example

# Set default port
ENV PORT=8000

# Define healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/info/health || exit 1

# Expose port
EXPOSE ${PORT}

# Run the application
CMD ["/bin/bash", "-c", "/app/.local/bin/uv run uvicorn folio_api.api:app --host 0.0.0.0 --port ${PORT}"]


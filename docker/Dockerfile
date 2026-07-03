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
COPY --chown=app:app pyproject.toml uv.lock ./
COPY --chown=app:app README.md ./

# Install dependencies (without the project itself — code isn't copied yet).
# Use --frozen to honor uv.lock; the previous --upgrade ignored the lockfile and
# pulled latest on every fresh build, which silently broke the API when
# Starlette 1.0 removed the legacy TemplateResponse(name, context) signature.
RUN uv sync --no-install-project --frozen

# Copy application code
COPY --chown=app:app folio_api folio_api
COPY --chown=app:app config.json.example ./config.json.example

# Bake the example config in as the default. Local dev/compose overrides via
# bind-mount; container-only deploys (Railway, Fly, plain `docker run`) get a
# working config out of the box. Placeholder ${OPENAI_API_KEY} is handled
# defensively in api.py:initialize_folio.
RUN cp config.json.example config.json

# Install the project package now that source is available
RUN uv sync --frozen

# Set default port
ENV PORT=8000

# Force Python stdout/stderr to flush immediately so container logs (Docker,
# Railway, Fly, etc.) actually surface uvicorn startup output and tracebacks.
# Without this, output is block-buffered when stdout is a pipe — the worst
# possible default for debugging a deploy that's silently failing.
ENV PYTHONUNBUFFERED=1

# Define healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/info/health || exit 1

# Expose port
EXPOSE ${PORT}

# Run the application
CMD ["/bin/bash", "-c", "/app/.local/bin/uv run uvicorn folio_api.api:app --host 0.0.0.0 --port ${PORT}"]


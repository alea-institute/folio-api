FROM ubuntu:24.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    pipx \
    curl \
    build-essential \
    &&  \
    rm -rf /var/lib/apt/lists/* \
    && \
    pipx install uv \
    && \
    pipx ensurepath

# create /app directory
WORKDIR /app
RUN cd /app

# create /app directory
WORKDIR /app
RUN cd /app

# copy the poetry configuration \
COPY pyproject.toml uv.lock README.md ./

# build the poetry environment
RUN bash -l -c "uv sync --upgrade && uv venv && uv run python"

# copy the python api code
COPY folio_api folio_api

# you could copy the config.json file, but we're using bind mounts by default instead.
# COPY config.json config.json

# run uvicorn: # uvicorn folio_api.api:app --reload
CMD ["bash", "-l", "-c", "PYTHONPATH=. uv run uvicorn folio_api.api:app --host 0.0.0.0 --port 8000"]
EXPOSE 8000

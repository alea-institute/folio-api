# FOLIO API

![FOLIO Logo](https://openlegalstandard.org/assets/images/soli-intro-logo.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This project provides a public API for the [FOLIO](https://openlegalstandard.org) (Federated Open Legal Information Ontology) ontology.

**If you just want to access the API, you don't need to run this project yourself.  The API is freely available to the public,
including open CORS `*` origins, at [https://folio.openlegalstandard.org/](https://folio.openlegalstandard.org/).**

For example, you can view the `Lessor` class:

* [HTML](https://folio.openlegalstandard.org/R8pNPutX0TN6DlEqkyZuxSw/html)
* [JSON-LD](https://folio.openlegalstandard.org/R8pNPutX0TN6DlEqkyZuxSw/jsonld)
* [Markdown](https://folio.openlegalstandard.org/R8pNPutX0TN6DlEqkyZuxSw/markdown)
* [OWL XML](https://folio.openlegalstandard.org/R8pNPutX0TN6DlEqkyZuxSw/xml)
* [JSON](https://folio.openlegalstandard.org/R8pNPutX0TN6DlEqkyZuxSw)



## Overview

The FOLIO API allows users to interact with the FOLIO ontology, providing endpoints for searching, retrieving class information, and exploring the taxonomy.

FOLIO models 18,000+ legal concepts — areas of law, document artifacts, actors and players, legal entities, events, industries, forums and venues, and more — along with the OWL object properties that relate them. The API exposes that ontology over HTTP so it can be queried by prefix, label, or definition; browsed by taxonomy branch or property tree; searched semantically with an LLM; traversed as a graph of subject-property-object connections; and served for any concept in JSON, JSON-LD, Markdown, OWL XML, or HTML.

## Who it's for

The FOLIO API is built for anyone who needs a shared, machine-readable vocabulary for law. A few of the people it serves:

- **Priya, a legal-tech engineer.** She's wiring FOLIO into her firm's matter-intake product and needs stable identifiers and clean payloads. She resolves a concept by IRI to `.../jsonld` for her RDF store and to plain JSON for her app, uses `/search/prefix` to power an autocomplete field, and calls `/connections` to pull the subject-property-object triples that tell her how a `Lessor` relates to a `Lease`. Open CORS and a self-descriptive OpenAPI spec at `/openapi.json` mean she can integrate without standing up any infrastructure of her own.
- **Marcus, a knowledge engineer / taxonomist.** He curates FOLIO itself and needs to see the ontology as it really is. He works from the interactive `/explore/tree` explorer and the `/properties` tree to inspect class and property hierarchies, uses `/taxonomy/{branch}` with `max_depth` to walk a branch node by node, and reads the ancestor-rooted entity graph to check that a concept sits under the right parents before proposing a change.
- **Dana, on a law firm's data & KM team.** Her team classifies incoming documents and matters against a controlled vocabulary. She uses the LLM-backed `/search/llm/document-artifacts` and `/search/llm/area-of-law` endpoints to map free-text descriptions onto FOLIO concepts, then browses `/taxonomy/document_artifact` and `/taxonomy/industry` to validate the results against the canonical taxonomy — so every document lands on a stable IRI the whole firm agrees on.
- **Dr. Alvarez, a legal researcher.** She studies how areas of law overlap and needs interoperable, citable definitions. She queries `/taxonomy/area_of_law` and `/search/definition` to find concepts by their meaning rather than their name, exports them as OWL XML or JSON-LD for use in her own knowledge base, and links to the human-readable HTML rendering of each class in her writing.

## Use cases

- **Autocomplete and lookup** — power type-ahead and concept pickers with `/search/prefix` (label prefix or substring) and resolve any selected concept by IRI.
- **Document and matter classification** — map free text to FOLIO concepts with the LLM-backed `/search/llm/*` endpoints (areas of law, document artifacts, industries, events, legal authorities, and more), then confirm against the canonical `/taxonomy/*` branches.
- **Taxonomy browsing and curation** — explore class and property hierarchies interactively via `/explore/tree` and `/properties`, or programmatically via `/taxonomy/{branch}` with configurable `max_depth`.
- **Semantic graph traversal** — discover how concepts relate through `/connections`, which returns subject-property-object triples between FOLIO concepts.
- **Interoperability and data exchange** — retrieve any concept as JSON, JSON-LD, Markdown, OWL XML, or HTML to feed RDF stores, knowledge graphs, documentation, or downstream applications.
- **Definition-based discovery** — find concepts by the content of their definitions (not just their labels) with `/search/definition`.

## Swagger UI and OpenAPI Specification

The Swagger UI documentation can be found at [https://folio.openlegalstandard.org/docs](https://folio.openlegalstandard.org/docs).

The OpenAPI spec file can be found at [https://folio.openlegalstandard.org/openapi.json](https://folio.openlegalstandard.org/openapi.json).

## Running Locally with Docker and Caddy

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- An API key for your LLM provider (OpenAI, Anthropic, Google, xAI/Grok, or a local VLLM server)

### Quick Start

The easiest way to run the FOLIO API is using our Docker Compose setup:

1. Clone the repository:
   ```bash
   git clone https://github.com/alea-institute/folio-api.git
   cd folio-api
   ```

2. Create your configuration file:
   ```bash
   cp config.json.example config.json
   ```

3. Edit the `config.json` file to update your configuration (especially the OpenAI API key if needed).

4. Start the API in production mode:
   ```bash
   ./run.sh
   ```
   
   This will start the API and a Caddy reverse proxy. The API will be available at http://localhost/docs.

### Development Mode

For development with hot-reloading:

```bash
./run.sh dev
```

This will:
- Mount your local code directory into the container
- Enable hot-reloading (the server restarts when code changes)
- Run in the foreground with visible logs

### Available Commands

The `run.sh` script provides several commands to help manage your FOLIO API deployment:

```bash
./run.sh [command] [options]
```

Available commands:
- `prod` (default) - Run in production mode
- `dev` - Run in development mode with hot reloading
- `stop` - Stop all containers
- `logs` - View logs in real-time
- `restart` - Restart all containers
- `status` - Show container status
- `clean` - Stop and remove containers, networks, volumes

Port configuration options:
- `--api-port=PORT` or `--port=PORT` - Set the API port (default: 8000)
- `--web-port=PORT` - Set the web server port (default: 80)

Examples:
```bash
# Run in production mode with API on port 9000 and web server on port 8080
./run.sh prod --api-port=9000 --web-port=8080

# Run in development mode with custom ports
./run.sh dev --port=3000 --web-port=3080
```

You can also set the ports using environment variables:
```bash
export PORT=9000
export WEB_PORT=8080
./run.sh
```

### Manual Configuration

#### Environment Variables

The following environment variables can be set:

- `OPENAI_API_KEY`: Your OpenAI API key (if using OpenAI models)
- `ANTHROPIC_API_KEY`: Your Anthropic API key (if using Anthropic models)
- `GOOGLE_API_KEY`: Your Google API key (if using Google models)
- `XAI_API_KEY`: Your xAI API key (if using Grok models)
- `PORT`: The port on which the API server runs (default: 8000)
- `WEB_PORT`: The port on which the web server runs (default: 80)

#### Docker Compose Files

- `docker-compose.yml`: Production setup with Caddy for HTTPS
- `docker-compose.dev.yml`: Development setup with code hot-reloading

#### Caddy Configuration

The Caddy reverse proxy is configured in:
- `docker/Caddyfile`: Production configuration with HTTPS and security headers
- `docker/Caddyfile.dev`: Development configuration for localhost

## API Documentation

Once the API is running, you can access the Swagger UI documentation at `https://folio.openlegalstandard.org/docs`.

## Configuration

### API Configuration

The API can be configured using the `config.json` file. The main configuration sections include:

- `folio`: Settings for the FOLIO ontology source (GitHub repository or HTTP URL)
- `llm`: Configuration for the LLM model used for semantic searches
- `api`: API metadata, binding options, and CORS settings

### LLM Configuration

The `llm` section of `config.json` supports:

| Key | Description | Default |
|---|---|---|
| `type` | Provider: `openai`, `anthropic`, `google`, `grok`, `vllm` | `openai` |
| `model` | Model name | `gpt-5.4` |
| `effort` | Reasoning effort: `low`, `medium`, `high` | `low` |
| `tier` | Service tier: `flex`, `standard`, `priority` | `flex` |
| `endpoint` | Custom API endpoint | _(provider default)_ |
| `api_key` | API key (or use env var) | _(from env)_ |

The `effort` and `tier` settings are provider-agnostic — they automatically translate to the correct provider-specific parameters (e.g. `effort: "low"` becomes `reasoning_effort: "none"` for OpenAI, `thinking_level: "minimal"` for Google).

#### Recommended Configurations

Based on benchmarks across 20 model configurations and 5 legal search queries on the FOLIO ontology (see `benchmarks/llm_search_benchmark.py`):

| Config | Avg Latency | Avg Results | Cost/M input | Best For |
|---|---|---|---|---|
| **grok-4-fast (recommended)** | **1.1s** | **4.0** | **$0.20** | Best value — fast, broad, cheap |
| **gpt-5.4 effort=low flex** | **1.8s** | **3.8** | **$2.50** | Best quality on OpenAI |
| gemini-3-flash-preview low | 3.6s | 4.8 | low | Most comprehensive results |
| gpt-4.1-mini | 1.7s | 4.0 | $0.40 | Good OpenAI fallback |

**Option 1 — Best value (Grok):**
```json
{
  "llm": {
    "type": "grok",
    "model": "grok-4-fast-non-reasoning"
  }
}
```

**Option 2 — Best quality (OpenAI):**
```json
{
  "llm": {
    "type": "openai",
    "model": "gpt-5.4",
    "effort": "low",
    "tier": "flex"
  }
}
```

**Avoid** for this workload: `gpt-5-mini`/`nano` (9-14s, surprisingly slow), `effort: "high"` (5x latency, no quality gain), reasoning models like `grok-4-fast-reasoning` or `grok-3-mini` (3-15x slower with fewer results).

#### All Provider Examples

```json
// OpenAI — best quality
{"type": "openai", "model": "gpt-5.4", "effort": "low", "tier": "flex"}

// Grok — best value
{"type": "grok", "model": "grok-4-fast-non-reasoning"}

// Google — most comprehensive
{"type": "google", "model": "gemini-3-flash-preview", "effort": "low"}

// Anthropic
{"type": "anthropic", "model": "claude-sonnet-4-6", "effort": "low"}

// Local VLLM
{"type": "vllm", "model": "your-model-name", "endpoint": "http://your-server:8000/"}
```

### Docker Configuration

The Docker setup includes:

- **Non-root user**: The API runs as a non-privileged user for better security
- **Health checks**: Automatic health monitoring to ensure the API is functioning
- **Layer caching**: Optimized layer caching for faster builds and smaller images
- **Volume mounts**: Configuration and logs are mounted from the host system

### Caddy Configuration

Caddy provides:

- **Automatic HTTPS**: TLS certificates are automatically managed in production
- **Security headers**: HSTS, XSS protection, and other security headers
- **Rate limiting**: Prevents abuse of the API
- **Gzip compression**: Reduces bandwidth usage
- **Structured logging**: JSON logs for better monitoring

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

The FOLIO Python library is released under the MIT License. See the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues or have questions about using the FOLIO API, please [open an issue](https://github.com/alea-institute/folio-api/issues) on GitHub.

## Changelog

For a detailed list of changes between versions, please see the [CHANGELOG.md](CHANGELOG.md) file.

## Learn More

To learn more about FOLIO, its development, and how you can get involved, visit the [FOLIO website](https://openlegalstandard.org/) or join the [FOLIO community forum](https://discourse.openlegalstandard.org/).

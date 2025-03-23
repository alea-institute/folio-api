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

## Swagger UI and OpenAPI Specification

The Swagger UI documentation can be found at [https://folio.openlegalstandard.org/docs](https://folio.openlegalstandard.org/docs).

The OpenAPI spec file can be found at [https://folio.openlegalstandard.org/openapi.json](https://folio.openlegalstandard.org/openapi.json).

## Running Locally with Docker and Caddy

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- An OpenAI API key if you're using the LLM search features

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

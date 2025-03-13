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

To run the FOLIO API locally using Docker and Caddy, follow these steps:

1. Clone the repository:
   ```
   git clone https://github.com/your-repo/folio-api.git
   cd folio-api
   ```

2. Build the Docker image:
   ```
   docker build -t folio-api-ubuntu2404 -f docker/Dockerfile .
   ```

3. Check your configuration

View the `config.json` file to ensure that the configuration is correct for your environment.


3. Run the Docker container:

```
docker run -v $(pwd)/config.json:/app/config.json --publish 8000:8000 folio-api-ubuntu2404:latest
```

If you've changed the port in the `config.json` file, make sure to update the port in the `--publish` flag as well.

4. Reverse proxy with Caddy (optional)

- Ensure you have [Caddy](https://caddyserver.com/) installed on your system.
- Create a `Caddyfile` in the project root with the following content:
  ```
  <your.domain>> {
          encode gzip
          reverse_proxy localhost:8000
  }
  ```

5. Start Caddy:
   ```
   caddy run
   ```

Now you can access the API at `your.domain` (make sure to add this to your hosts file if testing locally).

## API Documentation

Once the API is running, you can access the Swagger UI documentation at `https://folio.openlegalstandard.org/docs`.

## Configuration

The API can be configured using the `config.json` file. Modify this file to change settings such as the FOLIO source, API metadata, and binding options.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

The FOLIO Python library is released under the MIT License. See the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues or have questions about using the FOLIO API, please [open an issue](https://github.com/alea-institute/folio-api/issues) on GitHub.

## Learn More

To learn more about FOLIO, its development, and how you can get involved, visit the [FOLIO website](https://openlegalstandard.org/) or join the [FOLIO community forum](https://discourse.openlegalstandard.org/).

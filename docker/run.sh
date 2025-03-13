# build
docker build -t folio-api-ubuntu2404 -f docker/Dockerfile .

# run with bind mount for config.json into /app/config.json
docker run -v $(pwd)/config.json:/app/config.json --publish 8000:8000 folio-api-ubuntu2404:latest

# see Caddyfile for reverse proxy configuration

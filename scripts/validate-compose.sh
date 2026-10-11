#!/bin/sh
# Syntax/interpolation check only. Never starts containers or prints credentials.
set -eu
cd "$(dirname "$0")/.."
env_file=${1:-.env.example}
if [ -n "${COMPOSE_PROJECT_NAME:-}" ]; then
  echo 'Unset COMPOSE_PROJECT_NAME: it overrides the separate project names.' >&2
  exit 1
fi
for file in core-docker-compose.yml connector-docker-compose.yml enrichment-docker-compose.yml; do
  docker compose --env-file "$env_file" -f "$file" --profile '*' config --quiet
  echo "Valid: $file"
done
docker compose --env-file "$env_file" -f core-docker-compose.yml -f xtm-one-docker-compose.yml --profile '*' config --quiet
echo 'Valid: core + optional XTM One overlay'
docker compose --env-file "$env_file" -f core-docker-compose.yml -f nginx-docker-compose.yml --profile '*' config --quiet
echo 'Valid: core + optional Nginx HTTPS overlay'
docker compose --env-file "$env_file" -f core-docker-compose.yml -f xtm-one-docker-compose.yml -f nginx-docker-compose.yml --profile '*' config --quiet
echo 'Valid: core + XTM One + Nginx overlays'

# OpenCTI Docker Deployment

OpenCTI is a tricky platform, this repo splits the deployment into three categories: the core platform, the connectors, and the enrichment connectors.

This repository provides Docker Compose files for [OpenCTI](https://github.com/OpenCTI-Platform/opencti), the Open Cyber Threat Intelligence Platform.

## Deployment Files

| File | Category | Purpose |
|---|---|---|
| `core-docker-compose.yml` | Core platform | OpenCTI, workers, XTM Composer, Redis, Elasticsearch, MinIO, RabbitMQ, and built-in OpenCTI connectors |
| `connector-docker-compose.yml` | Connectors | Optional third-party feed and import connectors |
| `enrichment-docker-compose.yml` | Enrichment connectors | Optional enrichment connectors such as YARA, Shodan, Hygiene, and Google DNS |
| `.env.example` | Configuration template | Placeholder values for local `.env` configuration |

## Architecture

### Core Platform

| Service | Image | Purpose |
|---|---|---|
| **OpenCTI** | `opencti/platform:latest` | Core platform web UI and API |
| **Worker** | `opencti/worker:latest` | Background task processor |
| **XTM Composer** | `filigran/xtm-composer:latest` | Connector lifecycle manager |
| **Redis** | `redis:8.6.1` | Cache and queue backend |
| **Elasticsearch** | `elasticsearch:8.19.12` | Search and indexing |
| **MinIO** | `minio/minio:latest` | S3-compatible object storage |
| **RabbitMQ** | `rabbitmq:4.2-management` | Message queue for connector communication |
| **RSA Key Generator** | `alpine/openssl:latest` | Generates the XTM Composer private key in a Docker volume |

### Built-In Connectors

| Connector | Type | Description |
|---|---|---|
| Export File STIX | `INTERNAL_EXPORT_FILE` | Export data as STIX2 JSON bundles |
| Export File CSV | `INTERNAL_EXPORT_FILE` | Export data as CSV files |
| Export File TXT | `INTERNAL_EXPORT_FILE` | Export data as plain text files |
| Import File STIX | `INTERNAL_IMPORT_FILE` | Import STIX2 JSON/XML bundles |
| Import Document | `INTERNAL_IMPORT_FILE` | Import PDF, TXT, and HTML documents |
| Import File YARA | `INTERNAL_IMPORT_FILE` | Import YARA rules |
| Import External Reference | - | Import external references |
| Analysis | `INTERNAL_ANALYSIS` | Analyze imported PDF, TXT, and HTML documents |
| OpenCTI Datasets | - | Marking definitions, identities, and locations |
| MITRE ATT&CK | - | MITRE ATT&CK framework data |

## Prerequisites

- Docker Engine 20.10+
- Docker Compose v2+
- Minimum 16 GB RAM
- `vm.max_map_count` set to at least `262144` on the host for Elasticsearch:

```bash
sudo sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
```

## Quick Start

1. Clone the repository:

```bash
git clone <repo-url>
cd OpenCTI
```

2. Create the environment file:

```bash
cp .env.example .env
```

3. Edit `.env` and replace every `CHANGE_ME` value. Generate UUIDs and the OpenCTI encryption key with:

```bash
uuidgen
openssl rand -base64 32
```

4. Start the core platform:

```bash
docker compose --env-file .env -f core-docker-compose.yml up -d
```

5. Wait for the containers and OpenCTI API to become healthy before starting the secondary compose files:

```bash
docker compose --env-file .env -f core-docker-compose.yml ps
curl -sf "http://<your-host>:<OPENCTI_PORT>/health?health_access_key=<OPENCTI_HEALTHCHECK_ACCESS_KEY>"
```

6. Start the connector and enrichment compose files:

```bash
docker compose --env-file .env \
  -f core-docker-compose.yml \
  -f connector-docker-compose.yml \
  -f enrichment-docker-compose.yml \
  up -d
```

7. Access OpenCTI at `http://<your-host>:<OPENCTI_PORT>` and log in with the admin credentials from `.env`.

## Configuration

Copy `.env.example` to `.env` and configure the required values before starting the stack.

### OpenCTI Platform

| Variable | Description | Example |
|---|---|---|
| `OPENCTI_EXTERNAL_SCHEME` | External URL scheme | `http` or `https` |
| `OPENCTI_HOST` | External hostname | `localhost` |
| `OPENCTI_PORT` | Exposed web UI/API port | `8080` |
| `OPENCTI_BASE_URL` | Internal URL used by connectors/workers | `http://opencti:8080` |
| `OPENCTI_ADMIN_EMAIL` | Initial admin account email | `admin@example.com` |
| `OPENCTI_ADMIN_PASSWORD` | Initial admin account password | Strong password |
| `OPENCTI_ADMIN_TOKEN` | Initial admin API token | UUIDv4 |
| `OPENCTI_HEALTHCHECK_ACCESS_KEY` | Health endpoint access key | UUIDv4 |
| `OPENCTI_ENCRYPTION_KEY` | OpenCTI encryption key | `openssl rand -base64 32` |

### Infrastructure Credentials

| Variable | Description | Example |
|---|---|---|
| `ELASTIC_MEMORY_SIZE` | Elasticsearch JVM heap size | `4G` |
| `MINIO_ROOT_USER` | MinIO admin username | `opencti` |
| `MINIO_ROOT_PASSWORD` | MinIO admin password | Strong password |
| `RABBITMQ_DEFAULT_USER` | RabbitMQ username | `opencti` |
| `RABBITMQ_DEFAULT_PASS` | RabbitMQ password | Strong password |
| `SMTP_HOSTNAME` | SMTP server for email notifications | `smtp.example.com` |

### Connector IDs

All connector ID variables should be UUIDv4 values generated per deployment.

| Variable Group | Used By |
|---|---|
| `CONNECTOR_*_ID` | Built-in OpenCTI connectors in `core-docker-compose.yml` |
| `UUID_29` through `UUID_50` | Optional connectors in `connector-docker-compose.yml` |
| `ENRICHMENT_CONNECTOR_*_ID` | Enrichment connectors in `enrichment-docker-compose.yml` |

### External API Keys

Leave optional API keys blank when you do not use the corresponding connector.

| Variable | Service |
|---|---|
| `ABUSEIP_API` | AbuseIPDB |
| `URLHS_API` | URLhaus |
| `SHODAN_API` | Shodan |
| `ALIENVAULT_API_KEY` | AlienVault OTX |
| `ALIENVAULT_PULSE_START_TIMESTAMP` | AlienVault import start timestamp |
| `CROWDSEC_KEY` | CrowdSec |
| `MALPEDIA_AUTH_KEY` | Malpedia |
| `MALWAREBAZAAR_API_KEY` | MalwareBazaar |
| `PROMPTINTEL_API_KEY` | PromptIntel |
| `CYBER_MONITOR_GITHUB_TOKEN` | Cyber Campaign Collection GitHub access |
| `PHISHUNT_API_KEY` | Phishunt |

## Operations

Use the same compose file list for lifecycle commands that you used to start the stack.

```bash
docker compose --env-file .env -f core-docker-compose.yml ps
docker compose --env-file .env -f core-docker-compose.yml logs -f opencti
docker compose --env-file .env -f core-docker-compose.yml up -d --scale worker=5
docker compose --env-file .env -f core-docker-compose.yml down
docker compose --env-file .env -f core-docker-compose.yml down -v
```

## Security Notes

- `.env` is ignored by git. Do not commit real API keys, admin tokens, passwords, or generated private keys.
- Set `ALIENVAULT_PULSE_START_TIMESTAMP` to a recent timestamp before enabling AlienVault. A date too far in the past can overload OpenCTI with pulses.
- `APP__ENCRYPTION_KEY` is loaded from `OPENCTI_ENCRYPTION_KEY`; generate a unique value per deployment.
- The Docker socket is mounted into the `xtm-composer` container for managing connector containers. This grants significant host access, so restrict it in multi-tenant environments.
- Elasticsearch security (`xpack.security.enabled`) is disabled for this single-node compose setup. Enable authentication before exposing Elasticsearch outside the Docker network.
- MinIO port `9000` is exposed to the host. Restrict access with firewall rules if it does not need to be externally reachable.
- The RSA private key is generated into a Docker volume and mounted read-only into `xtm-composer`.

## License

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE) for details.

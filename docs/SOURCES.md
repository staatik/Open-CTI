# Source baseline and validation

Checked on 2026-10-08 for a fresh deployment.

| Source | Revision | Use |
|---|---|---|
| [staatik/Open-CTI](https://github.com/staatik/Open-CTI/tree/faaff4a09f497cc52b124e43d5fad6c670d09f89) | `faaff4a09f497cc52b124e43d5fad6c670d09f89` | Original three groups and connector settings; all three remote Compose files matched the original local checkout byte-for-byte |
| [Filigran Docker helpers](https://github.com/OpenCTI-Platform/docker/tree/10b23d4da56cafcd1b1d20904bb048011fc1ffcf) | `10b23d4da56cafcd1b1d20904bb048011fc1ffcf` (2026-09-29) | Latest default Compose, environment template and RabbitMQ configuration at review time |
| [OpenCTI release](https://github.com/OpenCTI-Platform/opencti/releases/tag/7.261002.0) | `7.261002.0` (2026-10-02) | Platform and worker pin |
| [Connector release](https://github.com/OpenCTI-Platform/connectors/tree/7.261002.0) | `7.261002.0` | Connector image pins, per-connector Compose examples, sample settings and relevant implementation checks |
| [XTM Composer release](https://github.com/FiligranHQ/xtm-composer/releases/tag/3.260825.0) | `3.260825.0` | Optional integration-manager pin |
| [Docker profiles](https://docs.docker.com/compose/how-tos/profiles/) | Current documentation | Individual-service activation and group controls |

## Upstream infrastructure changes adopted

- Redis `8.6.1` → `8.10.1`.
- Elasticsearch `8.19.12` → `8.19.21`.
- RabbitMQ `4.2-management` → `4.3-management`.
- Object storage `minio/minio:latest` → `pgsty/silo:latest`, retaining the internal service name `minio` and upstream S3-compatible settings.
- RabbitMQ `max_message_size=536870912` and `consumer_timeout=86400000`.
- Optional XTM One with pgvector/PostgreSQL, public identity URLs on both platform and worker, internal OpenCTI API URL, and accepted internal XTM One audience.

## Intentional local differences

- Independent core/feed/enrichment Compose projects with an explicitly named shared network; connector projects reference it as external.
- Fresh project/volume namespace, descriptive connector IDs and a non-overwriting credential generator.
- Every existing connector retained; Attribution Tools classified with enrichment. Two optional additional services: CVE and the formerly commented SPARTA.
- OpenCTI release pins replace `latest`; other moving upstream tags are identified in `.env.example` and README.
- XTM Composer and its key generator are opt-in. XTM One is an optional core overlay.
- Dependency ports are internal; UI host binding is configurable.
- Log rotation and `unless-stopped` restart policies throughout.
- Authenticated ThreatFox/URLhaus exports, explicit Ransomware.live endpoint/key, current-year Cyber Campaign Collection bootstrap, seven-day OTX bootstrap.
- Shodan starts in manual mode, attribution automatic relationships start disabled, and Hygiene starts with 10 workers. All are configurable.

## Verification

Validated with Docker Compose v5.1.3. All standalone models and the core/XTM One overlay pass `docker compose config` with every profile enabled. Template references have corresponding variables, all 35 original connectors are retained, project names are distinct, and each standalone model resolves to the same network name.

Additional checks passed for generated UUID uniqueness, 32-byte encryption-key format, private file permissions and refusal to overwrite existing credentials. Profile selection was checked with generated credentials: nine public feeds, three basic enrichments, no default external connectors, and optional Composer/XTM One. Changing the stack name propagated correctly to every project, shared network and Composer network setting. Dependency references, internal-only infrastructure ports, worker replica count and XTM One registration/public-identity settings were also checked.

Registry manifest checks succeeded for 40 of the 44 distinct images in the three main files, including the platform, every connector and XTM Composer. Docker Hub's unauthenticated rate limit prevented verification of `opencti/worker:7.261002.0`, `pgsty/silo:latest`, `rabbitmq:4.3-management` and `redis:8.10.1`; their tags follow the release/upstream baseline. The optional XTM One/pgvector image manifests were not checked. No container images were downloaded and no deployment or live ingestion was started.

Run the documented `pull` commands on the destination host (authenticate with `docker login` if needed), then check core health and each enabled connector. Compose validation is not proof that external APIs, credentials, feed availability or ingest behavior work end to end.

## Optional HTTPS addition

The Nginx overlay pins `nginx:1.30.5-alpine`, listed in the [official image definitions](https://github.com/docker-library/official-images/blob/master/library/nginx) when checked on 2026-10-08. It uses [Compose's `!override` behavior](https://docs.docker.com/reference/compose-file/merge/) to remove OpenCTI's host port, and follows [OpenCTI's reverse-proxy guidance](https://docs.opencti.io/latest/deployment/installation/#deploy-behind-a-reverse-proxy) with [WebSocket forwarding](https://nginx.org/en/docs/http/websocket.html). Secure session cookies use the documented `APP__HTTPS_CERT__COOKIE_SECURE` setting.

Checks passed for core + Nginx and core + XTM One + Nginx, including removal of host port 8080, public URL propagation, secure cookies, read-only certificate mounts and Nginx's published ports. OpenSSL verified the generated certificate against its requested IP, rejected a different IP, and confirmed the certificate matches its private key. The generator was also checked for DNS/IPv6 SANs, invalid-name rejection, permissions and overwrite protection. The generated files are ignored by Git.

The local Docker daemon was unavailable, so the Nginx container, its `nginx -t` check and end-to-end HTTPS were not run locally. Follow [the HTTPS guide](HTTPS.md) to perform those checks on the deployment host before use.

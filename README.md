# OpenCTI: core, feeds and enrichment

Fresh deployment configuration based on [Filigran's Docker helpers](https://github.com/OpenCTI-Platform/docker/tree/10b23d4da56cafcd1b1d20904bb048011fc1ffcf), retaining the connector choices from [staatik/Open-CTI](https://github.com/staatik/Open-CTI). OpenCTI, workers and connectors are pinned to **7.261002.0**, the latest published release checked on **2026-10-08**. See [sources and changes](docs/SOURCES.md).

The three main files are **independent Compose projects** on one shared Docker network. Start the core first, then selected feeds and enrichments. Stopping a feed project does not stop the platform. All 35 previously active connectors are retained; Attribution Tools moves to the enrichment file. CVE and SPARTA are additional opt-in connectors.

| File | Default project | Contents |
|---|---|---|
| [core-docker-compose.yml](core-docker-compose.yml) | `opencti-fresh-core` | OpenCTI, 3 workers, Redis, Elasticsearch, Silo, RabbitMQ, 10 built-in/dataset connectors; optional XTM Composer |
| [connector-docker-compose.yml](connector-docker-compose.yml) | `opencti-fresh-feeds` | 20 retained feeds plus optional CVE and SPARTA |
| [enrichment-docker-compose.yml](enrichment-docker-compose.yml) | `opencti-fresh-enrichment` | YARA, Shodan, Hygiene, Google DNS, Attribution Tools |
| [xtm-one-docker-compose.yml](xtm-one-docker-compose.yml) | Core overlay | Optional XTM One platform, worker and dedicated PostgreSQL/pgvector |
| [nginx-docker-compose.yml](nginx-docker-compose.yml) | Core overlay | Optional HTTPS proxy on ports 80/443; removes direct OpenCTI host-port exposure |
| [.env.example](.env.example) | Shared settings | Version pins, local credentials, connector IDs and blank provider keys |

**Use each main file separately.** Do not combine the three main files with `-f`, set `COMPOSE_PROJECT_NAME`, or pass `-p`: those override their independent project names. Set `OPENCTI_STACK_NAME` once in `.env` to change all names together. The optional XTM One and Nginx files are overlays merged with core.

## Prepare a fresh installation

Use a current Docker Engine and Docker Compose plugin supporting profiles, top-level `name`, and `up --wait` (Compose v2.20+ for the base stack; **v2.24.4+ for the Nginx overlay and full validation script**). Python 3.9+ is needed for the optional credential/certificate generators; certificate generation also needs OpenSSL. Linux amd64 is the primary deployment target; XTM Composer explicitly uses amd64 as upstream does. Verify image architecture support before using ARM.

Plan for at least 16 GB RAM for a small deployment and preferably 32 GB or more with many feeds. This is a sizing starting point: Elasticsearch has a 4 GB heap and OpenCTI an approximately 8 GB JavaScript heap, with additional process/container overhead. XTM One and attribution training need more capacity. Adjust `ELASTIC_MEMORY_SIZE`, `OPENCTI_NODE_MEMORY_MB`, `OPENCTI_WORKERS` and enabled connectors to fit the host.

On the Linux Docker host, set Elasticsearch's kernel prerequisite:

```bash
sudo sysctl -w vm.max_map_count=1048575
```

Persist `vm.max_map_count=1048575` in the host's sysctl configuration. See [Filigran's installation guide](https://docs.opencti.io/latest/deployment/installation/).

For this fresh start, use a new directory and the default `OPENCTI_STACK_NAME=opencti-fresh` (or another unused name). Stop the old deployment using its original configuration before reusing port 8080. The new project names create empty volumes; no old volumes need to be deleted. Do not reuse the old `.env`, which used `COMPOSE_PROJECT_NAME=xtm` and numbered connector IDs.

Generate new local credentials and stable, unique connector UUIDs:

```bash
python3 scripts/init-env.py
```

The generator creates `.env` with mode `0600`, refuses to overwrite an existing file, and leaves all provider API keys blank. It also limits the initial AlienVault lookback to seven days and Cyber Campaign Collection to the current year. Alternatively, copy `.env.example` to `.env` and fill the credential/UUID placeholders yourself.

Edit `.env`:

- Set `OPENCTI_PUBLIC_URL` to the URL you will open in your browser, such as `https://cti.example.org` or `http://server-ip:8080`.
- Set `OPENCTI_ADMIN_EMAIL`. The generated admin password is in `OPENCTI_ADMIN_PASSWORD`.
- Keep `OPENCTI_ENCRYPTION_KEY`, connector IDs and infrastructure credentials stable once the installation is in use.
- Add provider keys later, before enabling the corresponding connectors.

`OPENCTI_PUBLIC_URL` is independent of the host port. Containers always reach OpenCTI at `http://opencti:8080`. For a reverse proxy, configure WebSocket support and set `OPENCTI_BIND_ADDRESS=127.0.0.1` if the proxy runs on the host. By default the UI binds on all host interfaces; dependency ports are internal only. `SMTP_HOSTNAME=localhost` is an upstream placeholder: configure a real SMTP host if you want email delivery.

## Optional HTTPS with Nginx

For HTTPS on your server, follow the [HTTPS setup guide](docs/HTTPS.md) to generate a self-signed certificate on the server, update `OPENCTI_PUBLIC_URL`, and enable `nginx-docker-compose.yml`. The proxy supports WebSockets and removes OpenCTI's direct host-port mapping. Trust the generated public certificate on your browser/client devices.

Once enabled, include `-f nginx-docker-compose.yml` after the core file in the core commands below. Include the XTM One overlay too if you use it. Feed and enrichment commands remain separate.

## Start in sequence

Run commands from this repository directory. Validate configuration without starting anything:

```bash
sh scripts/validate-compose.sh .env
```

Start core and wait for its health checks:

```bash
docker compose --env-file .env -f core-docker-compose.yml pull
docker compose --env-file .env -f core-docker-compose.yml up -d --wait --wait-timeout 600
docker compose --env-file .env -f core-docker-compose.yml ps
```

For platform-only troubleshooting, target just OpenCTI and workers first; Compose brings up their infrastructure dependencies. A later unqualified core `up` starts the built-in connectors too:

```bash
docker compose --env-file .env -f core-docker-compose.yml up -d --wait --wait-timeout 600 opencti worker
```

Open your `OPENCTI_PUBLIC_URL`, verify login and the Data → Ingestion connector status. `--wait` checks container health/running state, not completion of dataset ingestion; allow the OpenCTI datasets and MITRE ATT&CK imports to settle.

Start a few public feeds first, then basic enrichment:

```bash
docker compose --env-file .env -f connector-docker-compose.yml up -d \
  connector-cisa-known-exploited-vulnerabilities connector-wiz connector-mitre-atlas

docker compose --env-file .env -f enrichment-docker-compose.yml \
  --profile enrichment-basic up -d
```

Or start the nine feeds grouped under `feeds-public`:

```bash
docker compose --env-file .env -f connector-docker-compose.yml --profile feeds-public up -d
```

All feed/enrichment services have profiles. With no profile or explicit service, those files start nothing. Explicitly targeting a service activates it without starting other members of its profiles. See the [connector catalog](docs/CONNECTORS.md) for exact names, credentials and caveats. External projects cannot use Compose `depends_on` for core; start them only after core is healthy. They attach to the core-created network, so a missing network means core has not been started with the same stack name.

## Operate individual connectors

After adding `ALIENVAULT_API_KEY` to `.env`:

```bash
docker compose --env-file .env -f connector-docker-compose.yml up -d connector-alienvault
docker compose --env-file .env -f connector-docker-compose.yml logs -f --tail=100 connector-alienvault
```

Stop, start or recreate one connector without changing core:

```bash
docker compose --env-file .env -f connector-docker-compose.yml stop connector-alienvault
docker compose --env-file .env -f connector-docker-compose.yml up -d connector-alienvault

# After editing that connector's settings or image version:
docker compose --env-file .env -f connector-docker-compose.yml pull connector-alienvault
docker compose --env-file .env -f connector-docker-compose.yml up -d --no-deps connector-alienvault
```

Use `stop` for routine shutdown; `kill connector-alienvault` is available for an unresponsive container. `restart` does not apply changes to environment variables or images; use `up -d` to recreate it. `unless-stopped` preserves deliberate stops across Docker restarts. Logs rotate at 10 MB × 3 files per container.

Inspect and stop entire groups independently, including every optional profile:

```bash
docker compose --env-file .env -f connector-docker-compose.yml --profile '*' ps
docker compose --env-file .env -f connector-docker-compose.yml --profile '*' stop
docker compose --env-file .env -f enrichment-docker-compose.yml --profile '*' stop
```

For complete teardown, remove external groups before the core-owned network:

```bash
docker compose --env-file .env -f connector-docker-compose.yml --profile '*' down
docker compose --env-file .env -f enrichment-docker-compose.yml --profile '*' down
docker compose --env-file .env -f core-docker-compose.yml --profile '*' down
```

These commands preserve volumes. `down -v` deletes that project's data and is unnecessary for a fresh deployment under a new stack name. If XTM One is enabled, include its overlay in core lifecycle commands. Stop Composer-managed integrations through the Integration Manager before removing the core network; those dynamically created containers are not owned by the feed Compose project.

## Optional XTM Composer

The default workflow manages connectors directly through Compose. To also use Filigran's Integration Manager:

```bash
docker compose --env-file .env -f core-docker-compose.yml --profile composer up -d --wait --wait-timeout 600
```

This enables RSA key generation and XTM Composer, with the Docker socket and the correct shared network. The socket grants Composer control over the Docker host. Avoid enabling the same integration in both Composer and these Compose files, which would ingest duplicate data under separate connector identities.

## Optional XTM One

Filigran now bundles XTM One in its default stack. It is provided here as an optional overlay so the core remains independently usable. It includes the upstream public-URL, internal-URL and JWT audience settings.

Set `XTM_ONE_PUBLIC_URL` and review its generated credentials. Its admin email automatically matches `OPENCTI_ADMIN_EMAIL`. Keep the generated URL-safe PostgreSQL password, or URL-encode special characters appropriately before embedding a replacement in `DATABASE_URL`.

```bash
docker compose --env-file .env -f core-docker-compose.yml -f xtm-one-docker-compose.yml pull
docker compose --env-file .env -f core-docker-compose.yml -f xtm-one-docker-compose.yml \
  up -d --wait --wait-timeout 600
```

Use **both** files for subsequent core `up`, `pull`, `stop` and `down` commands while XTM One is enabled. Add `--profile composer` if you also use the Integration Manager. XTM One's default browser port is 8090; model-provider configuration and any feature licensing are configured separately in that product.

## Docker Hub pull errors: 429 Too Many Requests

An `unexpected status from HEAD ... 429 Too Many Requests` error means Docker Hub is rate-limiting registry requests. Compose may cancel the other pulls and label them `Interrupted`; that does not establish a problem with those image tags.

On the deployment host, authenticate as the same operating-system user that runs Docker Compose, then pull serially and retry startup:

```bash
docker login
docker compose --env-file .env -f core-docker-compose.yml --parallel 1 pull
docker compose --env-file .env -f core-docker-compose.yml up -d --wait --wait-timeout 600
```

Authenticate locally using Docker's login flow; do not put Docker Hub credentials in this repository's `.env`. If you use `sudo docker compose`, authenticate with `sudo docker login` instead so the commands use the same Docker credentials. If XTM One is enabled, include its overlay in the pull/start commands.

Serial pulls reduce concurrent registry requests but do not reset a used-up quota. If an authenticated pull still returns 429, stop retrying and wait for the limit to clear, or check your Docker Hub account's allowance. Changing Redis/OpenCTI tags will not resolve rate limiting. See [Docker Hub's troubleshooting guide](https://docs.docker.com/docker-hub/troubleshoot/).

## Later updates

OpenCTI and all its connectors share `OPENCTI_VERSION` to avoid accidental `latest` version skew. When moving to another release, read its release notes, stop external ingestion, update the version, pull and bring up core first, then pull/recreate the selected feed and enrichment services. Review infrastructure upgrades separately. This configuration is for the requested fresh deployment; it is not an in-place migration plan for unknown older data.

Silo, XTM One, pgvector and the RSA helper retain upstream moving tags. Resolve them to digests or published release tags if you require every dependency to be reproducible. Only OpenCTI, workers, connectors and Composer are release-pinned here; Redis/Elasticsearch use exact upstream versions and RabbitMQ an upstream minor tag.

## Validation scope

`sh scripts/validate-compose.sh` checks all three standalone models and the optional XTM One/Nginx overlay combinations with Docker Compose, including disabled profiles. This validates YAML, interpolation and dependency references. It does not authenticate provider keys, confirm feed availability, check Nginx syntax/certificate files, or test ingestion. The HTTPS guide includes the separate `nginx -t` check. Validate on the deployment host after startup and inspect the workers' queues and connector logs before adding more sources.

## Publication checks

Keep `.env`, generated certificate directories and private keys outside Git. `.env.example` must contain placeholders and empty provider-key values only. The [publication review](docs/PUBLICATION_REVIEW.md) records the current checks and the historical-credential blocker in the original private checkout.

With [Gitleaks](https://github.com/gitleaks/gitleaks) installed, scan a clean public checkout before pushing:

```bash
gitleaks git . --log-opts='--all --full-history' --redact=100
sh scripts/validate-compose.sh
```

The repository's `.gitleaks.toml` extends the standard secret rules with OpenCTI credential names, including UUID-based admin/health tokens. If updating the existing public repository, copy only the reviewed source files into a fresh clone of that repository; preserve its clean history. Copying or pushing the original private checkout's `.git` history would publish historical credentials. Follow [GitHub's sensitive-data guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) if credentials have already been published.

## License

This repository remains under [GPL-3.0](LICENSE).

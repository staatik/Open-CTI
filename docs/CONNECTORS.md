# Connector catalog

All OpenCTI connector images use `OPENCTI_VERSION=7.261002.0`. Every connector from the original deployment is retained. IDs now have descriptive variable names in `.env.example`; this is a fresh deployment, so the generator creates new UUIDs instead of reusing `UUID_29`–`UUID_49`.

Start one feed after core is healthy:

```bash
docker compose --env-file .env -f connector-docker-compose.yml up -d connector-wiz
```

Each optional service has a profile matching its name after `connector-`. For example, `--profile alienvault up -d` starts AlienVault. Directly naming the service works too and is convenient when troubleshooting. API keys can remain blank for services you do not start.

## Retained external feeds

The **public** column identifies the nine services included in `--profile feeds-public`. Other services remain individually opt-in, including high-volume feeds and providers with account requirements. Public means no provider credential is configured for that connector; remote feed availability is still subject to the provider.

| Service | Public group | Credentials / setup | Purpose |
|---|---|---|---|
| `connector-redflag-domains` | Yes | None | Suspicious domain registrations from Red Flag Domains |
| `connector-wiz` | Yes | None | Wiz's public cloud threat landscape |
| `connector-alienvault` | No | `ALIENVAULT_API_KEY`; review `ALIENVAULT_PULSE_START_TIMESTAMP` | OTX pulses, reports and indicators |
| `connector-cisa-known-exploited-vulnerabilities` | Yes | None | CISA KEV exploitation context |
| `connector-crowdsec-import` | No | `CROWDSEC_KEY`; check API access for your account | IP reputation; retains your SSH-bruteforce query |
| `connector-cyber-campaign-collection` | No | `CYBER_MONITOR_GITHUB_TOKEN` recommended; `CYBER_MONITOR_FROM_YEAR` | Public APT and cybercrime reports; GitHub rate limits apply |
| `connector-disarm-framework` | Yes | None | DISARM influence-operation techniques |
| `connector-dshield` | Yes | None | SANS ISC/DShield blocklist |
| `connector-mitre-atlas` | Yes | None | Adversarial threats to AI systems |
| `connector-promptintel` | No | `PROMPTINTEL_API_KEY` | Prompt/AI threat intelligence |
| `connector-malpedia` | No | `MALPEDIA_AUTH_KEY` optional for public data; authenticated access expands coverage | Malware knowledge, intrusion sets and YARA |
| `connector-malwarebazaar` | No | `MALWAREBAZAAR_API_KEY` | MalwareBazaar metadata using your retained file-tag filter |
| `connector-ransomwarelive` | No | `RANSOMWARELIVE_API_KEY` for the selected API-PRO endpoint | Ransomware victims and intrusion sets; history disabled |
| `connector-abuse-ssl` | Yes | None in the upstream SSL IP blacklist configuration | Abuse.ch SSL blacklist |
| `connector-abuseipdb-ipblacklist` | No | `ABUSEIP_API`; account access controls blacklist limits | Retains your score threshold 50 and 5,000-IP limit |
| `connector-urlhaus-recent-payloads` | No | `URLHS_API` | URLhaus payload metadata; retains your file-type/signature filters |
| `connector-threatfox` | No | `THREATFOX_API_KEY` | ThreatFox IOCs via authenticated CSV export |
| `connector-urlhaus` | No | `URLHS_API` | URLhaus recent malware URLs via authenticated CSV export |
| `connector-vxvault` | Yes | None; TLS verification stays enabled | VX Vault malicious URL list |
| `connector-phishunt` | Yes | `PHISHUNT_API_KEY` optional | Public feed without a key; optional expanded access |

### Settings that changed

**ThreatFox / URLhaus:** the provider documentation now requires an Auth-Key in export URLs, while some upstream connector examples still show old public endpoints. The configuration builds the current export URLs from your keys:

- ThreatFox: `/v2/files/exports/<key>/full.csv.zip` on `threatfox-api.abuse.ch`. The selected connector release supports extracting `full.csv` from this ZIP.
- URLhaus: `/v2/files/exports/<key>/recent.csv` on `urlhaus-api.abuse.ch`. Its connector consumes plain CSV, so do not substitute a ZIP URL.

See [ThreatFox export documentation](https://threatfox.abuse.ch/export/) and [URLhaus export documentation](https://urlhaus.abuse.ch/api/). Treat rendered Compose output and connector logs as sensitive: URLs contain the key, and URLhaus logs the request URL. The payload connector uses its own API-key setting, populated from the same `URLHS_API` variable. These authenticated requests need a live check after you add keys.

**Cyber Campaign Collection:** removed `CYBER_CAMPAIGN_COLLECTION_IMPORT_HISTORY`, which the selected release does not read. On first run the connector imports from `CYBER_MONITOR_FROM_YEAR` and also imports the current year. The generator sets that value to the current year to avoid a multi-year backfill. It can still import all reports for that year. The upstream scope is now `report`.

**Ransomware.live:** retains the connector and exposes its current API endpoint selector. The default here is `https://api-pro.ransomware.live`, which requires a provider key. The release also documents a legacy unauthenticated v2 client; this configuration does not assume that legacy service remains available. Pull-history is off. See the [release-matched connector README](https://github.com/OpenCTI-Platform/connectors/blob/7.261002.0/external-import/ransomwarelive/README.md).

**AlienVault:** the generator sets an initial lookback of seven days. Starting from an old timestamp can produce a substantial backlog. The release's timestamp parser only accepts `YYYY-MM-DDTHH:MM:SS` (optionally with fractional seconds); use UTC with **no trailing `Z` or `+00:00`**. For example, `2026-10-01T00:00:00` works, while `2026-10-01T00:00:00Z` raises `unconverted data remains: Z`. Your enrichment/relationship choices are preserved.

If you generated `.env` with the earlier template, remove the suffix from its `ALIENVAULT_PULSE_START_TIMESTAMP` value, then apply it to this connector:

```bash
docker compose --env-file .env -f connector-docker-compose.yml \
  up -d --force-recreate --no-deps connector-alienvault
```

If the same bad timestamp persists in saved connector state, reset **only AlienVault's state** from its entry under Data → Ingestion → Connectors, then rerun it. Resetting state can reimport pulses from the configured start timestamp. The parser and saved-state fallback were verified against the [release source](https://github.com/OpenCTI-Platform/connectors/blob/7.261002.0/external-import/alienvault/src/alienvault/utils/__init__.py).

## Which connectors populate actor groups?

OpenCTI's **Threat Actor Groups** and **Intrusion Sets** are separate entity types. With the current settings most actor-oriented connectors in this deployment populate Intrusion Sets:

| Connector | Current destination | How to populate Threat Actor Groups |
|---|---|---|
| MITRE ATT&CK (`connector-mitre`, core file) | Intrusion Sets, including ATT&CK groups | Imports MITRE's `intrusion-set` objects as provided |
| Wiz (`connector-wiz`) | Intrusion Sets (`WIZ_THREAT_ACTOR_AS_INTRUSION_SET=true`) | Set that existing environment value to `'false'` in the connector Compose file |
| Malpedia (`connector-malpedia`) | Intrusion Sets (`MALPEDIA_IMPORT_INTRUSION_SETS=true`) | Actor associations are modeled as Intrusion Sets |
| AlienVault (`connector-alienvault`) | Intrusion Sets from pulse adversaries | Adversaries are modeled as Intrusion Sets |
| Ransomware.live (`connector-ransomwarelive`) | Intrusion Sets; Threat Actor creation currently disabled | Set `RANSOMWARELIVE_CREATE_THREAT_ACTOR` to `'true'`; its selected API-PRO endpoint needs a key |

Wiz is the simplest existing public source for the Threat Actor Groups category: change its setting above, then run:

```bash
docker compose --env-file .env -f connector-docker-compose.yml \
  up -d --force-recreate --no-deps connector-wiz
```

If it already imported the feed, reset that connector's state in OpenCTI to resync it with the changed mapping. Existing Intrusion Sets are retained; the setting does not convert previously imported entities in place. Source mappings: [MITRE](https://github.com/OpenCTI-Platform/connectors/blob/7.261002.0/external-import/mitre/README.md), [Wiz](https://github.com/OpenCTI-Platform/connectors/blob/7.261002.0/external-import/wiz/README.md), [Malpedia](https://github.com/OpenCTI-Platform/connectors/blob/7.261002.0/external-import/malpedia/README.md), [AlienVault](https://github.com/OpenCTI-Platform/connectors/blob/7.261002.0/external-import/alienvault/README.md), [Ransomware.live](https://github.com/OpenCTI-Platform/connectors/blob/7.261002.0/external-import/ransomwarelive/src/ransomwarelive/converter_to_stix.py).

## Retained enrichment connectors

These use `enrichment-docker-compose.yml`, their own project and the shared network.

| Service | Profile(s) | Setup / behavior |
|---|---|---|
| `connector-yara` | `yara`, `enrichment-basic` | Automatic artifact matching against YARA indicators already in OpenCTI; no provider key |
| `connector-hygiene` | `hygiene`, `enrichment-basic` | No provider key; `HYGIENE_MAX_WORKERS=10` initially, adjustable |
| `connector-google-dns` | `google-dns`, `enrichment-basic` | No provider key; DNS queries go to Google's external resolver |
| `connector-shodan` | `shodan` | Set `SHODAN_API`; starts in manual enrichment mode (`SHODAN_AUTO=false`) |
| `connector-attribution-tools` | `attribution-tools` | Moved from the feed file to match its upstream INTERNAL_ENRICHMENT type; needs training data and an existing creator identity |

Before enabling Attribution Tools, create/select an Organization in OpenCTI and put its **STIX standard ID** (`identity--...`) into `ATTRIBUTIONTOOLS_CREATOR_ORG_IDENTITY_ID`. A newly generated arbitrary UUID is not a substitute for that existing identity. Training data persists in the enrichment project's `attribution_tools_data` volume. On a new empty platform, first ingest enough intrusion-set relationships to train a useful model. Automatic relationship creation defaults to false; set `ATTRIBUTIONTOOLS_AUTOMATIC_RELATION_CREATION=true` to restore your previous automatic behavior.

```bash
docker compose --env-file .env -f enrichment-docker-compose.yml up -d connector-shodan
docker compose --env-file .env -f enrichment-docker-compose.yml logs -f --tail=100 connector-shodan
```

## Built-in and reference-data connectors

The core file retains these ten services and their dependencies on a healthy OpenCTI API:

- `connector-export-file-stix`, `connector-export-file-csv`, `connector-export-file-txt`
- `connector-import-file-stix`, `connector-import-document`, `connector-import-file-yara`
- `connector-import-external-reference`, `connector-analysis`
- `connector-opencti` (markings, identities and locations), `connector-mitre` (ATT&CK)

They require no third-party API keys. The analysis service intentionally uses the import-document image with `INTERNAL_ANALYSIS`, matching upstream. Start/stop them individually using the core file just as you would a feed.

## Optional additions and recommendations

**CVE/NVD is the most useful general addition** to this set: it gives vulnerabilities broader descriptions and scoring context alongside your CISA KEV feed. The connector is open source and uses an NVD API key (`CVE_API_KEY`). It starts with historical backfill and CPE/software expansion disabled to limit initial ingest. See the [CVE connector configuration](https://github.com/OpenCTI-Platform/connectors/blob/7.261002.0/external-import/cve/README.md) and [NVD key registration](https://nvd.nist.gov/developers/request-an-api-key).

```bash
docker compose --env-file .env -f connector-docker-compose.yml up -d connector-cve
```

**SPARTA is useful if aerospace or space systems are in scope.** It was already commented out in your original file; it is now a valid, disabled-by-default service using its own UUID. It imports the public spacecraft threat framework without a provider key. See the [SPARTA connector](https://github.com/OpenCTI-Platform/connectors/blob/7.261002.0/external-import/sparta/README.md).

```bash
docker compose --env-file .env -f connector-docker-compose.yml up -d connector-sparta
```

All listed connector implementations are in Filigran's open-source connectors repository; provider data, API quotas and account plans are separate. Enable feeds gradually, inspect their logs and watch worker backlog before enabling larger sources.

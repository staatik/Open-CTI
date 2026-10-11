# HTTPS with Nginx and a self-signed certificate

The examples use **https://192.0.2.23**, a documentation-only address. Replace `192.0.2.23` with your server's actual IP in every command and setting below. The Nginx overlay joins the core project, listens on host ports **80/443**, redirects HTTP to the configured HTTPS URL, and forwards requests to `http://opencti:8080`. Workers and connectors continue using their existing internal URLs.

Requires **Docker Compose 2.24.4+**, Python 3.9+ and OpenSSL. The overlay uses `!override []` to remove OpenCTI's original published port entirely; an ordinary empty list would not remove it under Compose merge rules. See [Docker's merge documentation](https://docs.docker.com/reference/compose-file/merge/).

## Enable on the deployment server

Run these commands in your OpenCTI repository directory on `192.0.2.23`, after copying/pulling the updated configuration files. Keep your existing `.env` and credentials.

Generate a certificate **on that server**, so its private key stays there:

```bash
python3 scripts/generate-cert.py 192.0.2.23
```

This creates `nginx/certs/opencti.crt` and `nginx/certs/opencti.key`, valid for 365 days. The IP is recorded as an IP subject alternative name (SAN). The key has mode `0600`; the certificate directory has mode `0700`. Both certificate and key extensions are already ignored by Git. The script refuses to overwrite an existing directory.

Edit the existing `OPENCTI_PUBLIC_URL` entry in `.env` to:

```dotenv
OPENCTI_PUBLIC_URL=https://192.0.2.23
```

The overlay has defaults for these optional settings, so older generated `.env` files work without adding them:

```dotenv
NGINX_VERSION=1.30.5-alpine
NGINX_BIND_ADDRESS=0.0.0.0
NGINX_CERT_DIR=./nginx/certs
```

Do not change `OPENCTI_PORT` to 443; OpenCTI keeps listening on 8080 inside Docker. Nginx handles HTTPS. `OPENCTI_PUBLIC_URL` must use `https://` with no trailing slash, path, or credentials for this configuration. Ports 80 and 443 must be free on the host and reachable through any host/network firewall.

Validate the combined Compose model, then pull only the new image:

```bash
docker compose --env-file .env -f core-docker-compose.yml -f nginx-docker-compose.yml config --quiet
docker compose --env-file .env -f core-docker-compose.yml -f nginx-docker-compose.yml --parallel 1 pull nginx
```

Check the rendered Nginx configuration and certificates without starting its dependencies or publishing ports:

```bash
docker compose --env-file .env -f core-docker-compose.yml -f nginx-docker-compose.yml run --rm --no-deps nginx nginx -t
```

Apply the overlay. Targeting both services recreates OpenCTI with its HTTPS public URL, secure session cookies and no published HTTP port, then starts Nginx:

```bash
docker compose --env-file .env -f core-docker-compose.yml -f nginx-docker-compose.yml \
  up -d --wait --wait-timeout 600 opencti nginx
```

This briefly restarts OpenCTI if it is already running. Its persistent data remains in the existing core volumes. Existing workers/connectors reconnect over the same internal network. For a new installation, omit `opencti nginx` from the command to bring up the full core, including workers and built-in connectors.

Use **both files for later core lifecycle commands**. Omitting the Nginx overlay from a later core `up` would restore the base file's HTTP port mapping and cookie settings. If XTM One is enabled, use all three files:

```bash
docker compose --env-file .env -f core-docker-compose.yml \
  -f xtm-one-docker-compose.yml -f nginx-docker-compose.yml \
  up -d --wait --wait-timeout 600
```

This proxy covers **OpenCTI only**. XTM One retains its own port/public URL and needs a separate TLS configuration if you want HTTPS for that product too.

## Verify and trust the certificate

On the server, verify the IP match and test HTTPS while explicitly trusting this certificate:

```bash
openssl verify -CAfile nginx/certs/opencti.crt -verify_ip 192.0.2.23 nginx/certs/opencti.crt
curl --cacert nginx/certs/opencti.crt -I https://192.0.2.23/
curl -I http://192.0.2.23/
```

The HTTP request should return `308` with a `Location` beginning `https://192.0.2.23/`. An HTTPS response from OpenCTI confirms traffic reaches the application. Nginx's container health check only verifies its local listener; OpenCTI has its own dependency-aware health check.

Open **https://192.0.2.23** in the browser. A self-signed certificate encrypts traffic but is not automatically trusted. Import **only `opencti.crt`** into the trusted certificate store used by each client/browser, according to that client's certificate policy. Keep `opencti.key` on the server. A browser with a separate certificate store may need its own import. Verify the certificate fingerprint against the server before trusting a copied certificate:

```bash
openssl x509 -in nginx/certs/opencti.crt -noout -fingerprint -sha256
```

If the host IP changes, generate a replacement containing the new IP and update `OPENCTI_PUBLIC_URL`. To support a hostname and an IP together, provide both when generating the certificate, for example `python3 scripts/generate-cert.py cti.example.internal 192.0.2.23`. Configure DNS or the client's hosts file separately for the hostname.

## Maintenance

Inspect logs or reload after editing the proxy template:

```bash
docker compose --env-file .env -f core-docker-compose.yml -f nginx-docker-compose.yml logs -f --tail=100 nginx
docker compose --env-file .env -f core-docker-compose.yml -f nginx-docker-compose.yml restart nginx
```

Restart reruns the official image's template rendering. Use `up -d --no-deps nginx` instead after changing Nginx environment settings, mounts or its image. The template preserves WebSocket upgrade headers, disables buffering for streaming responses, allows uploads up to 100 MB, and refreshes the backend address through Docker DNS after OpenCTI is recreated. OpenCTI may enforce additional upload limits. These choices follow [OpenCTI's proxy guidance](https://docs.opencti.io/latest/deployment/installation/#deploy-behind-a-reverse-proxy) and [Nginx's WebSocket documentation](https://nginx.org/en/docs/http/websocket.html).

To renew, create a new directory (choose an unused name each time):

```bash
python3 scripts/generate-cert.py 192.0.2.23 --output nginx/certs-renewed
```

Set `NGINX_CERT_DIR=./nginx/certs-renewed` in `.env`, run the `nginx -t` command above, then recreate Nginx with `up -d --no-deps nginx` using both Compose files. Distribute/trust the new public certificate on clients. The previous certificate/key pair is kept for recovery.

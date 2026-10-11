#!/usr/bin/env python3
"""Generate a self-signed OpenCTI server certificate with DNS/IP subjectAltNames."""

import argparse
import ipaddress
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def san_name(value):
    """Validate names before embedding them in the OpenSSL configuration."""
    try:
        return "IP", str(ipaddress.ip_address(value))
    except ValueError:
        pass
    try:
        name = value.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise argparse.ArgumentTypeError("Invalid hostname") from exc
    labels = name.split(".")
    if len(name) > 253 or not all(
        re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in labels
    ) or re.fullmatch(r"[0-9.]+", name):
        raise argparse.ArgumentTypeError("Use a DNS hostname or IP, without https://, a port or a path")
    return "DNS", name


def main():
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="+", type=san_name, help="Browser hostname/IP, plus any aliases")
    parser.add_argument("--output", type=Path, default=root / "nginx" / "certs",
                        help="New certificate directory (must not already exist)")
    parser.add_argument("--days", type=int, default=365)
    args = parser.parse_args()
    if not 1 <= args.days <= 365:
        parser.error("--days must be between 1 and 365")
    if args.output.exists() or args.output.is_symlink():
        parser.error(f"Refusing to overwrite {args.output}; use a new --output directory")
    if shutil.which("openssl") is None:
        parser.error("openssl must be installed on this host")
    names = list(dict.fromkeys(args.names))
    # Browsers verify the SANs. A fixed CN avoids OpenSSL's short CN length limit.
    config = """[req]
prompt = no
distinguished_name = dn
x509_extensions = server_cert
[dn]
CN = OpenCTI
[server_cert]
basicConstraints = critical,CA:FALSE
keyUsage = critical,digitalSignature,keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
"""
    config += "\n".join(f"{kind}.{i} = {name}" for i, (kind, name) in enumerate(names, 1)) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".opencti-cert-", dir=args.output.parent) as tmp:
        staging = Path(tmp)
        config_file = staging / "openssl.cnf"
        config_file.write_text(config)
        cert, key = staging / "opencti.crt", staging / "opencti.key"
        command = ["openssl", "req", "-x509", "-newkey", "rsa:3072", "-sha256",
                   "-nodes", "-days", str(args.days), "-config", str(config_file),
                   "-keyout", str(key), "-out", str(cert)]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            parser.exit(1, f"OpenSSL failed: {result.stderr}\n")
        key.chmod(0o600)
        cert.chmod(0o644)
        # mkdir is exclusive, so even a concurrent run cannot replace an existing pair.
        try:
            args.output.mkdir(mode=0o700)
        except FileExistsError:
            parser.exit(1, f"Refusing to overwrite {args.output}\n")
        os.replace(key, args.output / key.name)
        os.replace(cert, args.output / cert.name)
    print(f"Created {args.output / 'opencti.crt'} and its private key (valid {args.days} days).")
    print("Certificate names: " + ", ".join(f"{kind}:{name}" for kind, name in names))
    host = names[0][1]
    if names[0][0] == "IP" and ":" in host:
        host = f"[{host}]"
    print(f"Set OPENCTI_PUBLIC_URL=https://{host} in .env, then start the Nginx overlay.")
    print("Trust the public .crt on client devices; keep the .key on the server.")


if __name__ == "__main__":
    main()

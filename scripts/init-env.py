#!/usr/bin/env python3
"""Create fresh deployment credentials without reading or overwriting an existing .env."""

import argparse
import base64
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import secrets
import uuid


def main():
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=root / ".env")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    generators = {
        "CHANGE_ME_UUID": lambda: str(uuid.uuid4()),
        "CHANGE_ME_PASSWORD": lambda: secrets.token_hex(24),
        "CHANGE_ME_HEX_32_BYTE_KEY": lambda: secrets.token_hex(32),
        "CHANGE_ME_BASE64_32_BYTE_KEY": lambda: base64.b64encode(secrets.token_bytes(32)).decode(),
    }
    lines = []
    for line in (root / ".env.example").read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            if value in generators:
                value = generators[value]()
            elif key == "ALIENVAULT_PULSE_START_TIMESTAMP":
                # This release's AlienVault parser accepts UTC without a timezone suffix.
                value = (now - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")
            elif key == "CYBER_MONITOR_FROM_YEAR":
                value = str(now.year)
            line = f"{key}={value}"
        lines.append(line)
    try:
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        parser.exit(1, f"Refusing to overwrite {args.output}. Choose a new --output path.\n")
    with os.fdopen(fd, "w") as output:
        output.write("\n".join(lines) + "\n")
    print(f"Created {args.output} with unique credentials and connector IDs (mode 0600).")
    print("Set OPENCTI_PUBLIC_URL and OPENCTI_ADMIN_EMAIL; add provider keys as needed.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate per-platform rule files from the block hosts sources.

Reads ``rules.json`` at the repository root, downloads every URL in the
``block`` map (each is assumed to be a hosts file), parses the domain names,
and writes one converted file per (rule, platform) pair under ``rules/block/``.

Output naming: ``rules/block/<rule-name>-<service>.<ext>``, where ``<rule-name>``
is the key of the ``block`` entry and ``<service>`` is derived from the platform.

Supported platforms (see ``PLATFORM_OUTPUT``):
  - ``sing-box`` -> ``<rule>-singbox.json``
        ``{"version": 3, "rules": [{"domain": [...]}]}`` (sing-box rule-set source format)
  - ``hosts``    -> ``<rule>-hosts.txt``
        one ``0.0.0.0 <domain>`` line per domain

Only the platform types present in ``rules.json["platforms"]`` are generated.
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

# platform name (as listed in rules.json) -> (filename service suffix, extension)
PLATFORM_OUTPUT = {
    "sing-box": ("singbox", ".json"),
    "hosts": ("hosts", ".txt"),
}

IPV4_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")

# Standard hosts-file entries that are never ad domains.
IGNORED_DOMAINS = {
    "localhost",
    "localhost.localdomain",
    "local",
    "broadcasthost",
    "ip6-localhost",
    "ip6-loopback",
    "ip6-localnet",
    "ip6-mcastprefix",
    "ip6-allnodes",
    "ip6-allrouters",
    "ip6-allhosts",
}


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": "sing-box-hosts-updater"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8-sig", errors="replace")


def parse_domains(text: str) -> list[str]:
    """Extract a sorted, de-duplicated list of domains from hosts-file text."""
    domains = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "!")):
            continue
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        for token in line.split():
            token = token.strip().rstrip(".")
            if not token:
                continue
            # Skip IPv4 / IPv6 addresses.
            if IPV4_RE.match(token) or ":" in token:
                continue
            # Domains in these lists always contain a dot.
            if "." not in token:
                continue
            token = token.lower()
            if token in IGNORED_DOMAINS:
                continue
            domains.add(token)
    return sorted(domains)


def to_singbox(domains: list[str]) -> dict:
    return {"version": 3, "rules": [{"domain": domains}]}


def to_hosts(domains: list[str]) -> str:
    return "".join(f"0.0.0.0 {d}\n" for d in domains)


CONVERTERS = {
    "sing-box": to_singbox,
    "hosts": to_hosts,
}


def main() -> int:
    rules_path = REPO_ROOT / "rules.json"
    rules = json.loads(rules_path.read_text(encoding="utf-8"))
    block = rules.get("block", {})
    platforms = rules.get("platforms", [])

    out_dir = REPO_ROOT / "rules" / "block"
    out_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for name, url in block.items():
        print(f"[{name}] fetching {url}")
        try:
            content = fetch(url)
        except Exception as exc:  # noqa: BLE001 - keep going on a bad source
            print(f"[{name}] FAILED: {exc}", file=sys.stderr)
            failures += 1
            continue

        domains = parse_domains(content)
        print(f"[{name}] {len(domains)} domains")

        for platform in platforms:
            if platform not in CONVERTERS:
                print(f"[{name}] skip unsupported platform: {platform}")
                continue
            service, ext = PLATFORM_OUTPUT[platform]
            payload = CONVERTERS[platform](domains)
            if isinstance(payload, dict):
                payload = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
            out_path = out_dir / f"{name}-{service}{ext}"
            out_path.write_text(payload, encoding="utf-8")
            print(f"[{name}] wrote {out_path.relative_to(REPO_ROOT)}")

    return 1 if failures == len(block) else 0


if __name__ == "__main__":
    sys.exit(main())

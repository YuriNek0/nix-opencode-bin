#!/usr/bin/env python3
"""
Update OpenCode version and release asset hashes.
Modified from llm-agents.nix by Numtide (https://github.com/numtide/llm-agents.nix).
"""

import json
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

HASHES_FILE = Path(__file__).parent / "hashes.json"
RELEASES_API = "https://api.github.com/repos/anomalyco/opencode/releases/latest"
ASSETS = {
    "x86_64-linux": "opencode-linux-x64.tar.gz",
    "aarch64-linux": "opencode-linux-arm64.tar.gz",
    "x86_64-darwin": "opencode-darwin-x64.zip",
    "aarch64-darwin": "opencode-darwin-arm64.zip",
}


def version_key(version: str) -> tuple[int | str, ...]:
    """Return a simple comparable version key."""
    return tuple(
        int(part) if part.isdigit() else part
        for part in re.split(r"[.+_-]", version.removeprefix("v"))
        if part
    )


def load_hashes() -> dict[str, Any]:
    """Load current version/hash data."""
    return json.loads(HASHES_FILE.read_text())


def latest_version() -> str:
    """Fetch the latest OpenCode GitHub release version."""
    request = urllib.request.Request(
        RELEASES_API,
        headers={"Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        release = json.loads(response.read().decode())
    return str(release["tag_name"]).removeprefix("v")


def prefetch_hash(url: str) -> str:
    """Return the Nix SRI hash for a release asset."""
    result = subprocess.run(
        ["nix", "store", "prefetch-file", "--hash-type", "sha256", "--json", url],
        check=True,
        capture_output=True,
        text=True,
    )
    return str(json.loads(result.stdout)["hash"])


def calculate_hashes(version: str) -> dict[str, str]:
    """Calculate all platform hashes for a version."""
    hashes: dict[str, str] = {}
    for system, asset in ASSETS.items():
        url = f"https://github.com/anomalyco/opencode/releases/download/v{version}/{asset}"
        print(f"Prefetching {system}: {asset}")
        hashes[system] = prefetch_hash(url)
    return hashes


def main() -> None:
    """Update hashes.json when a newer OpenCode release exists."""
    current = str(load_hashes()["version"])
    latest = latest_version()
    print(f"Current: {current}, Latest: {latest}")

    if version_key(latest) <= version_key(current):
        print("Already up to date")
        return

    data = {"version": latest, "hashes": calculate_hashes(latest)}
    HASHES_FILE.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"Updated to {latest}")


if __name__ == "__main__":
    main()

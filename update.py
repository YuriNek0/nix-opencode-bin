#!/usr/bin/env python3
"""Update OpenCode v1 and v2 release binaries.

Modified from llm-agents.nix by Numtide (https://github.com/numtide/llm-agents.nix).
"""

import base64
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent
RELEASES_API = "https://api.github.com/repos/anomalyco/opencode/releases"
V2_API = "https://opencode.ai/update/api/latest/cli/opencode"
ASSETS = {
    "x86_64-linux": "opencode-linux-x64.tar.gz",
    "aarch64-linux": "opencode-linux-arm64.tar.gz",
    "x86_64-darwin": "opencode-darwin-x64.zip",
    "aarch64-darwin": "opencode-darwin-arm64.zip",
}


def fetch_json(url: str) -> Any:
    """Use curl, which is also compatible with the upstream CDN."""
    result = subprocess.run(
        ["curl", "--fail", "--silent", "--show-error", "--location",
         "--retry", "3", "--max-time", "60", url],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def version_key(version: str) -> tuple[int, ...]:
    """Accept stable numeric releases only."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError(f"Not a stable version: {version}")
    return tuple(map(int, version.split(".")))


def latest_v1() -> str:
    """Find the newest stable 1.x release, including across API pages."""
    versions = []
    page = 1
    while True:
        releases = fetch_json(f"{RELEASES_API}?per_page=100&page={page}")
        for release in releases:
            version = release["tag_name"].removeprefix("v")
            if (not release["draft"] and not release["prerelease"]
                    and re.fullmatch(r"1\.\d+\.\d+", version)):
                versions.append(version)
        if len(releases) < 100:
            break
        page += 1
    if not versions:
        raise ValueError("No stable OpenCode v1 releases found")
    return max(versions, key=version_key)


def prefetch_hash(url: str) -> str:
    """Return the Nix SRI hash of the downloaded archive."""
    result = subprocess.run(
        ["nix", "store", "prefetch-file", "--hash-type", "sha256", "--json", url],
        check=True, capture_output=True, text=True,
    )
    return str(json.loads(result.stdout)["hash"])


def prepare_update(path: Path, version: str, urls: dict[str, str],
                   expected: dict[str, str] | None = None) -> dict[str, Any] | None:
    """Prepare all platform hashes before modifying release metadata."""
    current = json.loads(path.read_text())["version"] if path.exists() else "0.0.0"
    print(f"{path.name}: current {current}, latest {version}")
    if version_key(version) <= version_key(current):
        return None
    hashes = {}
    for system, url in urls.items():
        print(f"Prefetching {version} / {system}: {url}", flush=True)
        hashes[system] = prefetch_hash(url)
        if expected is not None and hashes[system] != expected[system]:
            raise ValueError(f"SHA-256 mismatch for {version} / {system}")
    data = {"version": version, "hashes": hashes}
    if expected is not None:
        data["urls"] = urls
    return data


def v2_metadata(release: dict[str, Any]) -> tuple[str, dict[str, str], dict[str, str]]:
    """Validate the v2 release and collect pinned assets and SRI hashes."""
    version = release["version"]
    if (release["name"] != "cli" or release["distribution"] != "opencode"
            or release["channel"] != "latest" or not release["active"]
            or version_key(version)[0] != 2):
        raise ValueError("Unexpected OpenCode v2 release metadata")
    urls, hashes = {}, {}
    for system, asset in ASSETS.items():
        item = release["metadata"]["files"][asset]
        url = item["url"]
        if not url.startswith("https://") or f"/{version}/" not in url:
            raise ValueError(f"Unpinned asset URL: {url}")
        digest = bytes.fromhex(item["sha256"])
        if len(digest) != 32:
            raise ValueError(f"Invalid SHA-256 for {asset}")
        urls[system] = url
        hashes[system] = "sha256-" + base64.b64encode(digest).decode()
    return version, urls, hashes


def main() -> None:
    """Fetch and verify both release lines before writing either file."""
    v1 = latest_v1()
    v2, urls, expected = v2_metadata(fetch_json(V2_API))
    updates = {
        ROOT / "hashes-v1.json": prepare_update(
            ROOT / "hashes-v1.json", v1,
            {system: f"https://github.com/anomalyco/opencode/releases/download/v{v1}/{asset}"
             for system, asset in ASSETS.items()},
        ),
        ROOT / "hashes.json": prepare_update(ROOT / "hashes.json", v2, urls, expected),
    }
    for path, data in updates.items():
        if data is not None:
            temporary = path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
            temporary.replace(path)
            print(f"Updated {path.name} to {data['version']}")


if __name__ == "__main__":
    main()

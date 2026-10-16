# nix-opencode-bin

Minimal Nix flake for OpenCode v1 and v2 release binaries, with one update script and
one scheduled GitHub Action.

| Package / app | Release line | Executable |
| --- | --- | --- |
| `opencode` (default) | Latest stable 2.x | `opencode` |
| `opencode-v1` | Latest stable 1.x | `opencode-v1` |

Both support x86_64 and aarch64 Linux, plus aarch64 macOS, using the systems
provided by the pinned `nix-systems/default` input. Intel macOS asset hashes are
also tracked, but the pinned nixpkgs no longer supports that system.
The executables have distinct
names so both packages can be installed together. Existing users who want to
stay on v1 should change their package attribute to `opencode-v1` and invoke
`opencode-v1`.

## Usage

```nix
{
  inputs = {
    opencode-bin.url = "github:YuriNek0/nix-opencode-bin";
  };

  environment.systemPackages = [
    inputs.opencode-bin.packages.${pkgs.stdenv.hostPlatform.system}.opencode
  ];
}
```

```bash
nix run github:YuriNek0/nix-opencode-bin#opencode -- --help
nix run github:YuriNek0/nix-opencode-bin#opencode-v1 -- --help
```

### Overlay

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    opencode-bin.url = "github:YuriNek0/nix-opencode-bin";
  };

  outputs = { nixpkgs, opencode-bin, ... }: {
    nixosConfigurations.myhost = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [{
        nixpkgs.overlays = [
          (final: _prev: {
            opencode = opencode-bin.packages.${final.stdenv.hostPlatform.system}.opencode;
          })
        ];

        environment.systemPackages = [ pkgs.opencode ];
      }];
    };
  };
}
```

## Development

```bash
nix develop
nix fmt
nix flake check --no-build
nix build .#opencode
nix build .#opencode-v1
python3 -m unittest discover -s tests
```

Update both release lines to their latest stable releases:

```bash
nix develop -c python3 update.py
```

## Update Automation

`.github/workflows/update.yml` runs periodically, executes `update.py`, validates
the flake, builds and smoke-tests both packages on Linux x86_64, and pushes
directly to `main` when `flake.lock`, `hashes.json`, or `hashes-v1.json` changes.
It also runs `nix flake update` before checking for new releases.

V1 releases are discovered through GitHub and pinned in `hashes-v1.json`.
V2 releases are discovered through OpenCode's CLI update API and pinned with
versioned asset URLs in `hashes.json`. The updater verifies every v2 archive
against the SHA-256 published by upstream before writing metadata. Package
evaluation uses only the committed metadata.

## Attribution

This package is based on the OpenCode packaging in
[`numtide/llm-agents.nix`](https://github.com/numtide/llm-agents.nix), simplified
for release binary packaging.

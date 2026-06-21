# nix-opencode-bin

Minimal Nix flake for the OpenCode release binary, with one update script and
one scheduled GitHub Action.

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
```

Update to the latest OpenCode release:

```bash
nix develop -c python3 update.py
```

## Update Automation

`.github/workflows/update.yml` runs periodically, executes `update.py`, validates
the flake, and pushes directly to `main` when `flake.lock` or `hashes.json`
changes. It also runs `nix flake update` before checking for a new OpenCode
release.

## Attribution

This package is based on the OpenCode packaging in
[`numtide/llm-agents.nix`](https://github.com/numtide/llm-agents.nix), simplified
for a single package.

{
  description = "Nix package for OpenCode release binaries";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    systems.url = "github:nix-systems/default";
  };

  outputs =
    {
      self,
      nixpkgs,
      systems,
    }:
    let
      eachSystem = nixpkgs.lib.genAttrs (import systems);

      mkOpencode =
        pkgs: pname: data:
        let
          inherit (pkgs) lib stdenv;
          inherit (data) version hashes;
          platform = stdenv.hostPlatform.system;
          assets = {
            x86_64-linux = {
              name = "opencode-linux-x64.tar.gz";
              zip = false;
            };
            aarch64-linux = {
              name = "opencode-linux-arm64.tar.gz";
              zip = false;
            };
            x86_64-darwin = {
              name = "opencode-darwin-x64.zip";
              zip = true;
            };
            aarch64-darwin = {
              name = "opencode-darwin-arm64.zip";
              zip = true;
            };
          };
          asset = assets.${platform} or (throw "Unsupported system: ${platform}");
        in
        stdenv.mkDerivation {
          inherit pname;
          inherit version;

          src = pkgs.fetchurl {
            url =
              data.urls.${platform}
                or "https://github.com/anomalyco/opencode/releases/download/v${version}/${asset.name}";
            hash = hashes.${platform};
          };

          nativeBuildInputs = [
            pkgs.makeWrapper
          ]
          ++ lib.optionals asset.zip [ pkgs.unzip ]
          ++ lib.optionals stdenv.hostPlatform.isLinux [ pkgs.autoPatchelfHook ];

          buildInputs = lib.optionals stdenv.hostPlatform.isLinux [
            stdenv.cc.cc.lib
          ];

          dontConfigure = true;
          dontBuild = true;
          dontStrip = true;

          unpackPhase = ''
            runHook preUnpack
            ${if asset.zip then "unzip $src" else "tar -xzf $src"}
            runHook postUnpack
          '';

          installPhase = ''
            runHook preInstall
            install -Dm755 opencode $out/bin/${pname}
            wrapProgram $out/bin/${pname} \
              --prefix PATH : ${
                lib.makeBinPath [
                  pkgs.fzf
                  pkgs.ripgrep
                ]
              }
            runHook postInstall
          '';

          meta = {
            description = "AI coding agent built for the terminal";
            homepage =
              if pname == "opencode-v1" then "https://opencode.ai/docs" else "https://opencode.ai/v2/docs";
            license = lib.licenses.mit;
            sourceProvenance = with lib.sourceTypes; [ binaryNativeCode ];
            platforms = builtins.attrNames assets;
            mainProgram = pname;
          };
        };
    in
    {
      packages = eachSystem (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
          opencode = mkOpencode pkgs "opencode" (builtins.fromJSON (builtins.readFile ./hashes.json));
          opencode-v1 = mkOpencode pkgs "opencode-v1" (
            builtins.fromJSON (builtins.readFile ./hashes-v1.json)
          );
        in
        {
          inherit opencode opencode-v1;
          default = opencode;
        }
      );

      apps = eachSystem (system: {
        opencode-v1 = {
          type = "app";
          program = "${self.packages.${system}.opencode-v1}/bin/opencode-v1";
        };
        opencode = {
          type = "app";
          program = "${self.packages.${system}.opencode}/bin/opencode";
        };
        default = self.apps.${system}.opencode;
      });

      devShells = eachSystem (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.mkShellNoCC {
            packages = [
              pkgs.curl
              pkgs.gh
              pkgs.jq
              pkgs.nixfmt-rfc-style
              pkgs.python3
            ];
          };
        }
      );

      formatter = eachSystem (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        pkgs.writeShellApplication {
          name = "fmt";
          runtimeInputs = [ pkgs.nixfmt ];
          text = ''
            if [ "$#" -eq 0 ]; then
              nixfmt flake.nix
            else
              nixfmt "$@"
            fi
          '';
        }
      );
    };
}

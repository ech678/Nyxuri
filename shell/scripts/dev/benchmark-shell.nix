let
  nixpkgsSrc = builtins.fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/6dadaf4375be35033e1c84395adbd53ff5fded96.tar.gz";
    sha256 = "sha256-D5H7H+qMoTGI/jJtxKP4u7BdjkFnUyhOovTrf3pTOr0=";
  };
  pkgs = import nixpkgsSrc { config.allowUnfree = false; };
  # This revision contains the package file but does not expose a top-level
  # `quickshell` attribute in every evaluator. Call the pinned package file
  # directly so the runtime version is independent of generated attrsets.
  quickshell = pkgs.callPackage
    (nixpkgsSrc + "/pkgs/by-name/qu/quickshell/package.nix") {};
in

pkgs.stdenv.mkDerivation {
  pname = "nyxuri-shell-benchmark-env";
  version = "1";
  dontUnpack = true;
  installPhase = "touch $out";
  buildInputs = [
    quickshell
    pkgs.weston
    pkgs.dbus
    pkgs.qt6Packages.qt5compat
    pkgs.python3
    pkgs.git
  ];
}

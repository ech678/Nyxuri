{ quickshellChannel ? "new" }:
let
  nixpkgsSrc = builtins.fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/6dadaf4375be35033e1c84395adbd53ff5fded96.tar.gz";
    sha256 = "sha256-D5H7H+qMoTGI/jJtxKP4u7BdjkFnUyhOovTrf3pTOr0=";
  };
  # Quickshell 0.2.1 predates the Qt 6.12 API changes in the current
  # benchmark channel. Keep its toolchain isolated to a Qt 6.8 evaluator;
  # only the protocol/GBM inputs are overridden from the current channel to
  # satisfy the old source's newer Wayland protocol floor.
  oldNixpkgsSrc = builtins.fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/50ab793786d9de88ee30ec4e4c24fb4236fc2674.tar.gz";
    sha256 = "sha256-/bVBlRpECLVzjV19t5KMdMFWSwKLtb5RyXdjz3LJT+g=";
  };
  pkgs = import nixpkgsSrc { config.allowUnfree = false; };
  oldPkgs = import oldNixpkgsSrc { config.allowUnfree = false; };
  # This revision contains the package file but does not expose a top-level
  # `quickshell` attribute in every evaluator. Call the pinned package file
  # directly so the runtime version is independent of generated attrsets.
  quickshell = pkgs.callPackage
    (nixpkgsSrc + "/pkgs/by-name/qu/quickshell/package.nix") {};
  # Keep the historical 0.2.1 package in the same pinned evaluator.  This is
  # only used for the compatibility matrix; the benchmark default remains the
  # newer locked package above.
  quickshellOld = oldPkgs.callPackage ({ lib, stdenv, fetchFromGitea,
    pkg-config, cmake, ninja, spirv-tools, qt6, breakpad, jemalloc, cli11,
    wayland, wayland-protocols, wayland-scanner, xorg, libdrm, libgbm, pipewire, pam,
  }:
    stdenv.mkDerivation {
      pname = "quickshell-old";
      version = "0.2.1";
      src = fetchFromGitea {
        domain = "git.outfoxxed.me";
        owner = "quickshell";
        repo = "quickshell";
        tag = "v0.2.1";
        hash = "sha256-e++Ogy91Sv7gGLMdAqZaBzbH/UmPWZ4GAt7VDCA66aU=";
      };
      nativeBuildInputs = [ cmake ninja qt6.qtshadertools spirv-tools wayland-scanner
        qt6.wrapQtAppsHook pkg-config ];
      buildInputs = [ qt6.qtbase qt6.qtdeclarative qt6.qtwayland qt6.qtsvg cli11
        wayland wayland-protocols libdrm libgbm breakpad jemalloc xorg.libxcb pam pipewire ];
      cmakeFlags = [ (lib.cmakeFeature "DISTRIBUTOR" "Nixpkgs")
        (lib.cmakeBool "DISTRIBUTOR_DEBUGINFO_AVAILABLE" true)
        (lib.cmakeFeature "INSTALL_QML_PREFIX" qt6.qtbase.qtQmlPrefix)
        (lib.cmakeFeature "GIT_REVISION" "tag-v0.2.1") ];
      cmakeBuildType = "RelWithDebInfo";
      separateDebugInfo = true;
      dontStrip = false;
    }
  ) {
    wayland-protocols = pkgs.wayland-protocols;
    libgbm = pkgs.libgbm;
  };
in

pkgs.stdenv.mkDerivation {
  pname = "nyxuri-shell-benchmark-env";
  version = "1";
  dontUnpack = true;
  installPhase = "touch $out";
  buildInputs = [
    (if quickshellChannel == "old" then quickshellOld else quickshell)
    pkgs.weston
    pkgs.sway
    pkgs.wtype
    pkgs.dbus
    pkgs.qt6Packages.qt5compat
    pkgs.python3
    pkgs.git
  ];
}

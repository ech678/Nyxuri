{ pkgs ? import (builtins.fetchGit {
    url = "https://github.com/NixOS/nixpkgs.git";
    rev = "ac62194c3917d5f474c1a844b6fd6da2db95077d";
  }) { config.allowUnfree = false; } }:

pkgs.mkShell {
  packages = with pkgs; [
    quickshell
    weston
    dbus
    qt6Packages.qt5compat
    python3
    git
  ];
}

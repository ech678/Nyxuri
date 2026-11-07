#!/usr/bin/env python3
"""Unified Config Migration Helper for Nyxuri Shell (P3).

Detects, absorbs, and consolidates the 7 legacy JSON configuration files
into a unified dictionary for config.toml generation, then cleans up legacy
files to enforce zero-residue hygiene.
"""

import argparse
import json
import os
import sys
from pathlib import Path

LEGACY_FILES = (
    "config.json",
    "dock.json",
    "tray.json",
    "quick-toggles.json",
    "display-color.json",
    "idle-policy.json",
    "ui-preferences.json",
)


def load_json_safely(path: Path) -> dict | list | None:
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().strip()
            if not text:
                return None
            return json.loads(text)
    except Exception as e:
        sys.stderr.write(f"[migrate_config] Warning reading {path.name}: {e}\n")
        return None


def merge_legacy_configs(config_dir: Path) -> dict:
    merged: dict = {}

    # 1. config.json (theme, wallpaper, effects, keystone, bar, sidebar, desktopCards, hotCorners)
    main_cfg = load_json_safely(config_dir / "config.json")
    if isinstance(main_cfg, dict):
        merged.update(main_cfg)

    # Ensure container tables exist
    bar = merged.setdefault("bar", {})
    if not isinstance(bar, dict):
        bar = merged["bar"] = {}

    # 2. dock.json
    dock_data = load_json_safely(config_dir / "dock.json")
    if isinstance(dock_data, dict):
        options = dock_data.get("options", {}) if isinstance(dock_data.get("options"), dict) else {}
        pinned = dock_data.get("pinned", []) if isinstance(dock_data.get("pinned"), list) else []
        dock_merged = {
            "schemaVersion": 1,
            "options": {
                "position": options.get("position", "bottom"),
                "iconSize": options.get("iconSize", 48),
                "magnification": options.get("magnification", True),
                "magnificationScale": options.get("magnificationScale", 1.5),
                "autoHide": options.get("autoHide", False),
                "launchBounce": options.get("launchBounce", True),
                "showIndicators": options.get("showIndicators", True),
                "showRecent": options.get("showRecent", True),
                "showThumbnails": options.get("showThumbnails", True),
                "previewSize": options.get("previewSize", 160),
                "contextPinning": options.get("contextPinning", True),
                "surfaceStyle": options.get("surfaceStyle", "default"),
            },
            "pinned": pinned,
        }
        merged["dock"] = dock_merged

    # 3. tray.json -> bar.tray
    tray_data = load_json_safely(config_dir / "tray.json")
    if isinstance(tray_data, dict):
        bar["tray"] = {
            "showItemId": bool(tray_data.get("showItemId", False)),
            "invertPinnedItems": bool(tray_data.get("invertPinnedItems", True)),
            "filterPassive": bool(tray_data.get("filterPassive", True)),
            "pinnedItems": tray_data.get("pinnedItems") if isinstance(tray_data.get("pinnedItems"), list) else ["Fcitx"],
        }

    # 4. quick-toggles.json -> bar.quickToggles
    qt_data = load_json_safely(config_dir / "quick-toggles.json")
    if isinstance(qt_data, dict) and isinstance(qt_data.get("toggles"), list):
        bar["quickToggles"] = qt_data["toggles"]

    # 5. display-color.json -> display
    dc_data = load_json_safely(config_dir / "display-color.json")
    if isinstance(dc_data, dict):
        merged["display"] = {
            "gamma": float(dc_data.get("gamma", 1.0)),
            "contrast": float(dc_data.get("contrast", 1.0)),
            "dimming": float(dc_data.get("dimming", 1.0)),
            "nightEnabled": bool(dc_data.get("nightEnabled", False)),
            "nightTemperature": int(dc_data.get("nightTemperature", 5500)),
            "dayTemperature": int(dc_data.get("dayTemperature", 6500)),
            "useIP": bool(dc_data.get("useIP", False)),
            "mode": str(dc_data.get("mode", "fixed")),
            "start": int(dc_data.get("start", 1200)),
            "end": int(dc_data.get("end", 420)),
            "transition": int(dc_data.get("transition", 30)),
            "latitude": dc_data.get("latitude"),
            "longitude": dc_data.get("longitude"),
        }

    # 6. idle-policy.json -> idle
    idle_data = load_json_safely(config_dir / "idle-policy.json")
    if isinstance(idle_data, dict):
        merged["idle"] = {
            "policyEnabled": bool(idle_data.get("policyEnabled", True)),
            "dimEnabled": bool(idle_data.get("dimEnabled", False)),
            "dimTimeout": float(idle_data.get("dimTimeout", 300)),
            "dimFraction": float(idle_data.get("dimFraction", 0.35)),
            "dimRespectInhibitors": bool(idle_data.get("dimRespectInhibitors", True)),
            "lockEnabled": bool(idle_data.get("lockEnabled", True)),
            "lockTimeout": float(idle_data.get("lockTimeout", 600)),
            "lockRespectInhibitors": bool(idle_data.get("lockRespectInhibitors", True)),
            "displayOffEnabled": bool(idle_data.get("displayOffEnabled", True)),
            "displayOffTimeout": float(idle_data.get("displayOffTimeout", 900)),
            "displayOffRespectInhibitors": bool(idle_data.get("displayOffRespectInhibitors", True)),
            "suspendEnabled": bool(idle_data.get("suspendEnabled", False)),
            "suspendTimeout": float(idle_data.get("suspendTimeout", 1800)),
            "suspendRespectInhibitors": bool(idle_data.get("suspendRespectInhibitors", True)),
        }

    # 7. ui-preferences.json -> preferences
    uip_data = load_json_safely(config_dir / "ui-preferences.json")
    if isinstance(uip_data, dict):
        pref_keys = (
            "language", "dndEnabled", "weatherTemperatureUnit", "systemTemperatureUnit",
            "spotlightSearchEngine", "spotlightAppStyle", "spotlightAppOrder",
            "spotlightClipboardStyle", "systemMonitorGpuId", "systemMonitorDiskDevice",
            "systemMonitorNetworkInterface", "storageCapacityDiskDevice",
            "systemMonitorIntervalMs", "controlPlaneResourceSampling", "useTwelveHourClock",
            "sidebarClockStyle", "drawerGridLayout", "systemCards", "recordingVideoDirectory",
            "recordingGifDirectory", "recordingMicrophoneDirectory", "recordingSystemAudioDirectory"
        )
        merged["preferences"] = {k: uip_data[k] for k in pref_keys if k in uip_data}

    return merged


def cleanup_legacy_files(config_dir: Path) -> list[str]:
    removed = []
    for filename in LEGACY_FILES:
        target = config_dir / filename
        if target.is_file():
            try:
                target.unlink()
                removed.append(filename)
            except Exception as e:
                sys.stderr.write(f"[migrate_config] Failed to remove {filename}: {e}\n")
    return removed


def main():
    parser = argparse.ArgumentParser(description="Absorb legacy JSON config into unified structure")
    parser.add_argument("--config-dir", required=True, help="Nyxuri config directory")
    parser.add_argument("--cleanup", action="store_true", help="Delete legacy JSON files")
    parser.add_argument("--check", action="store_true", help="Check if legacy files exist")
    args = parser.parse_args()

    config_dir = Path(args.config_dir).expanduser().resolve()
    if not config_dir.is_dir():
        sys.exit(0)

    legacy_exist = any((config_dir / f).is_file() for f in LEGACY_FILES)

    if args.check:
        sys.exit(0 if legacy_exist else 1)

    merged = merge_legacy_configs(config_dir)
    print(json.dumps(merged))

    if args.cleanup:
        cleaned = cleanup_legacy_files(config_dir)
        if cleaned:
            sys.stderr.write(f"[migrate_config] Cleaned up legacy files: {', '.join(cleaned)}\n")


if __name__ == "__main__":
    main()

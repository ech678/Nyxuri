"""将单元与包目录清单映射为当前系统能处理的外部依赖。"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PackageRequirements:
    """一个声明在指定平台上的安装来源与尚待手工提供的资源。"""

    packages_repo: list[str]
    packages_aur: list[str]
    packages_flatpak: list[str]
    manual: list[str]
    supported: bool = True
    reason: str = ""


def _names(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [item for item in value if isinstance(item, str) and item]
    return []


def _empty(reason: str = "") -> PackageRequirements:
    return PackageRequirements([], [], [], [], not bool(reason), reason)


def resolve_requirements(item: Any, platform: str | None = None) -> PackageRequirements:
    """按目标平台读取统一的包声明；Ubuntu 不会误用 Arch/AUR 包名。

    `item` 可为 ModuleManifest、CatalogEntry 或具有相同字段的简单对象。
    Arch 字段继续作为 AUR 打包的原始真值；Ubuntu 必须显式提供
    `platforms.ubuntu` 覆盖，只有跨发行版 Flatpak 声明可以直接沿用。
    """
    if platform is None:
        from nyxuri.pkg.platform import current_platform

        platform = current_platform()

    repo = _names(getattr(item, "packages_repo", []))
    aur = _names(getattr(item, "packages_aur", []))
    flatpak = _names(getattr(item, "packages_flatpak", []))
    platforms = getattr(item, "platforms", {})
    if not isinstance(platforms, dict):
        platforms = {}

    # Flatpak 应用 ID 不依赖发行版；没有原生包与 AUR 依赖的条目可以沿用 Flathub 来源。
    if platform == "arch":
        return PackageRequirements(repo, aur, flatpak, [])

    if platform == "ubuntu":
        override = platforms.get("ubuntu")
        if isinstance(override, dict):
            name = str(getattr(item, "name", "dependency"))
            # 空表或仅有说明文字不是「无需依赖」的声明。只有显式包/资源字段
            # 才能覆盖 Arch 依赖；真正无需依赖时写 packages = []。
            if override.get("supported") is False:
                return _empty(str(override.get("reason") or f"{name}: Ubuntu support is not declared"))
            if "supported" in override and not isinstance(override["supported"], bool):
                return _empty(f"{name}: invalid Ubuntu support flag")
            fields = ("packages", "packages_flatpak", "manual")
            if not any(key in override for key in fields):
                return _empty(f"{name}: Ubuntu dependencies must be explicitly declared")
            for key in fields:
                value = override.get(key, [])
                if not isinstance(value, (str, list, tuple)) or value == "" or (
                    not isinstance(value, str) and any(not isinstance(entry, str) or not entry for entry in value)
                ):
                    return _empty(f"{name}: invalid Ubuntu dependency field {key}")
            native = _names(override.get("packages"))
            portable = _names(override.get("packages_flatpak")) if "packages_flatpak" in override else flatpak
            manual = _names(override.get("manual"))
            reason = str(override.get("reason", ""))
            return PackageRequirements(
                native,
                [],
                portable,
                manual,
                True,
                reason,
            )

        if not repo and not aur:
            return PackageRequirements([], [], flatpak, [])

        name = str(getattr(item, "name", "dependency"))
        return _empty(f"{name}: no Ubuntu package mapping is declared")

    if not repo and not aur:
        return PackageRequirements([], [], flatpak, [])

    name = str(getattr(item, "name", "dependency"))
    return _empty(f"{name}: package installation is unsupported on {platform}")

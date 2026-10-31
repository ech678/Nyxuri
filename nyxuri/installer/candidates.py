"""发现安装入口可选择的配置单元，与底层独占目录原子批次分开。"""

from nyxuri.deploy.manifest import discover_manifest_apps


def discover_install_config_items() -> list[str]:
    """返回有配置载荷的目录、单文件和共享目录单元，供首次安装两种入口共用。

    runtime 单元没有待安装配置；壁纸继续由独立资源选项选择。这里只决定候选，
    窗口管理器选择、平台支持和可选供给筛选仍由各入口按既有规则处理。
    """
    return [uid for uid, manifest in discover_manifest_apps()
            if manifest.is_deployable and not manifest.runtime and uid != "wallpapers"]

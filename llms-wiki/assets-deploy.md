# Assets Deploy — 壁纸与静态资产部署流水线

> NyxNiri 的壁纸资产管理遵循“离线优先、无破坏覆盖 (no-clobber)”原则。
> 源码：`nyxniri/deploy/assets.py`，静态包：`assets/wallpapers/`。

## 核心设计

1. **零强制下载**：默认随仓库提供离线最小壁纸包（`assets/wallpapers/`），离线环境或网络受限时依然具备完整桌面视觉体验。
2. **No-Clobber 同步**：同步到用户目录（`~/Pictures/Wallpapers` 或 XDG 目录）时，仅补齐缺失文件，**永不覆盖**用户已有同名壁纸或自定义文件。
3. **外部大包按需拉取**：支持从多镜像源（GitHub、国内加速源）拉取高清动态/视频壁纸包，自带超时熔断保护。
4. **状态可观测契约**：由不可变数据类 `WallpaperDeployResult` 记录下载与部署结果，供安装完成界面展示 8 种精确状态（成功、增量更新、离线降级、网络失败等）。

## WallpaperDeployResult 契约

```python
@dataclass(frozen=True)
class WallpaperDeployResult:
    download_attempted: bool
    downloaded: bool
    pack_present: bool
    fallback_synced: bool
```

通过 `status_line(pack_present_now)` 方法为部署总结面板提供严格类型保护的 `(i18n_key, color, icon)` 三元组，杜绝散落在 UI 中的条件分支。

## 离线包与外部包判定

- **Pack 判定依据**：`_wallpaper_pack_present_at()` 检查目录下是否存在有效视频壁纸（`video/` 目录下含有至少一个 `.mp4` 或 `.webm`）。
- **软链接/拷贝隔离**：资产文件从仓库或临时下载目录部署到目标路径，严格遵循权限与路径安全校验。

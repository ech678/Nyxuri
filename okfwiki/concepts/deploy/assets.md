---
type: Playbook
title: 壁纸部署
description: 离线 fallback sync、多镜像外部 pack 下载、no-clobber 策略。
resource: nyxniri/deploy/assets.py
tags: [wallpaper, assets, download, fallback]
timestamp: "2026-09-12T14:00:00Z"
atelier:
  weight: 0.55
  tier: short
  verdict: verified
  use_count: 1
---

# 壁纸部署

## WallpaperDeployResult

| 字段 | 含义 |
|---|---|
| `download_attempted` | 是否尝试了外部 pack 下载 |
| `downloaded` | 外部 pack 是否成功部署 |
| `pack_present` | 磁盘上是否已有 wallpaper pack（检测 video 目录） |
| `fallback_synced` | 离线 fallback 是否执行 |

## 部署顺序

1. **no-clobber sync**：`assets/wallpapers/` 内文件只补缺不覆盖用户已有文件
2. **可选下载**（`do_download=True`）：遍历 `WALLPAPER_MIRRORS`，clone 成功后复制到 `~/Pictures/Wallpapers/`
3. 任一镜像失败 → 降级为仅 fallback sync

## wallpapers_pack_present()

检测 `~/Pictures/Wallpapers/video/` 下是否有文件，作为"已有完整 pack"的判断依据。

# Runtime Topology — 进程树、IPC 管道与信号链路

> NyxNiri 桌面运行时的动态全景：合成器会话启动、常驻守护进程、快捷键脚本层与跨应用 IPC 信号流。
> 源码：`configs/niri/config.kdl`、`configs/niri/scripts/`、`configs/noctalia/`。

---

## 1. 运行时架构全景

```
[ Niri Compositor 会话 (Wayland) ]
  │
  ├── 1. 启动阶段 (spawn-at-startup)
  │     ├── start-noctalia.sh  ───────► Noctalia V5 Shell (顶栏 / Dock / 通知 / 调色中枢)
  │     ├── fcitx5 -d          ───────► Fcitx5 输入法守护进程
  │     ├── toggle-eyecare.sh --sync ─► 同步护眼模式状态与色温
  │     └── (8s 延迟任务)      ───────► noctalia msg config-reload && templates-apply (M3 GTK 冷启动保底)
  │
  ├── 2. 交互脚本层 (Keybindings 触发)
  │     ├── Super + A / MouseForward ─► orbit-launcher.py (极坐标星环启动器)
  │     ├── Super + W          ───────► wallpaper-picker.py (壁纸选择器)
  │     ├── Super + ~          ───────► niri-scratch-toggle.sh (Kitty 浮动终端切换)
  │     ├── Super + N          ───────► toggle-eyecare.sh (护眼色温与着色器切换)
  │     └── 亮度快捷键         ───────► niri-brightness.sh (内屏背光 / 外接 DDC 分流)
  │
  └── 3. 主题与色彩调度层
        ├── nyxniri theme toggle / dark / light
        │     ▼
        │   theme-sync.sh (排他 flock 保护)
        │     ├── gsettings color-scheme ──► xdg-desktop-portal ──► GTK4/libadwaita & Brave
        │     ├── gtk-{3,4}.0/settings.ini 写入 ─────────────────► Chromium 启动读
        │     └── pkill -SIGUSR1 kitty ──────────────────────────► Kitty 终端秒跟
        │
        └── 壁纸切换事件 (wallpaper_changed hook)
              ▼
            wallpaper-hook.sh (若为视频，ffmpeg 抽取首帧缩略图)
              ▼
            Noctalia Material You 调色算法
              ▼ (~6s 自动触发)
            渲染 ~/.config/gtk-{3,4}.0/gtk.css (双 @media 块)
```

---

## 2. 核心守护进程与生命周期

| 进程 | 职责 | 拉起方式 | 存活策略 |
|---|---|---|---|
| **`niri`** | Wayland 合成器内核 | 登录管理器 (greetd / tty) | 根进程；退出即结束会话 |
| **`noctalia`** | 状态栏、桌面部件、调色引擎、OSD | `start-noctalia.sh` | 会话期常驻；注销时由清理钩子回收避免孤儿 |
| **`fcitx5`** | 中文与多语言输入法框架 | `spawn-at-startup "fcitx5 -d"` | 守护进程常驻 |
| **`xdg-desktop-portal`** | 桌面 Portal（文件、截图、色彩外观） | D-Bus 按需激活 / session 激活 | 由 `configs/xdg-desktop-portal/portals.conf` 分流路由 |
| **`mpvpaper`** | 动态视频壁纸渲染器 | 壁纸选择器按需拉起 | 仅在选中动态壁纸时启动，换静态壁纸时终止 |

---

## 3. IPC 通讯总线与协议

应用之间不通过轮询通讯，全部基于轻量 IPC 或信号广播：

| 通讯通道 | 协议 / 载体 | 典型调用示例 | 接收方响应 |
|---|---|---|---|
| **Niri IPC** | Unix Domain Socket | `niri msg action close-window` | Niri 执行窗口管理动作 |
| **Noctalia IPC** | Unix Domain Socket | `noctalia msg theme-mode-toggle` | 触发明暗模式反转、重算色板 |
| **Portal 外观信号** | D-Bus `org.freedesktop.appearance` | `gsettings set ... color-scheme` | GTK4 `AdwStyleManager`、Brave 即时重求值 |
| **进程信号 (Signal)** | POSIX `SIGUSR1` | `pkill -SIGUSR1 kitty` | Kitty 进程内存中重新加载配置与色彩 |
| **着色器动态热插拔** | KDL 文件软链接 | `effects.kdl` -> `effects_eyecare.kdl` | Niri inotify 监听并在下一帧应用着色器 |

---

## 4. 故障隔离与退化保护

1. **亮度调节降级 (`niri-brightness.sh`)**：
   - 内置屏幕优先调用 Noctalia D-Bus 背光服务（毫秒级、无卡顿）；
   - 外接显示器使用 `ddcutil`，且带超时拦截，防止 I2C 总线挂起冻结 UI。
2. **主题同步防抖竞态 (`theme-sync.sh`)**：
   - 使用 `flock -n /tmp/nyxniri-theme-sync.lock` 保证瞬时多次快速按下快捷键时排队或安全丢弃，不发生状态竞争。
3. **Orbit 启动器单实例锁 (`orbit/physics.py` / `/proc` 检测)**：
   - 防止重复唤起创建多个重叠悬浮窗，再次触发时优雅收起。

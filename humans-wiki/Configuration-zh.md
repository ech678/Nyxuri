```text
Nyxuri
├── install.sh                  # 极简引导入口
├── nyxuri/                     # Python 核心引擎（零 pip 依赖）
├── assets/                     # 静态资产（壁纸、fcitx5 皮肤模板）
└── configs/
    ├── niri/                   # 窗口管理器（.kdl、.toml）
    │   └── scripts/            # Orbit 启动器、壁纸选择器、Scratchpad 脚本
    ├── noctalia/               # 桌面 Shell 与主题同步
    ├── xdg-desktop-portal/     # Portal 路由（主题与录屏分流）
    ├── kitty/                  # 终端
    ├── fish/                   # 别名与函数
    ├── fastfetch/              # 系统信息
    ├── zed/                    # 编辑器
    └── starship.toml           # 提示符
```

配置采用原子部署。个人改动通过 Dunder 协议保留：
- 任何含 `__custom__` 的文件（如 `__custom__.kdl`、`__custom__.conf`）与目录在更新时自动保留。
- `~/.config/niri/monitor.kdl` 在部署时保留。

---

## 如何自定义你的配置 (Dunder 协议速查)

任何文件名或目录名只要包含 `__custom__`，跨版本更新或切换预设都不会被覆盖：

- **各应用按各自方式加载**：主配置末尾通常预置了挂载入口（例如 Niri 的 `__custom__.kdl`、Kitty 的 `__custom__.conf`），Fish 则自动扫描加载 `conf.d/` 下的脚本。
- **自由拆分与引入**：想要拆分配置，直接在主自定义文件中二次引入即可（例如在 `__custom__.kdl` 中写 `include "my_rules__custom__.kdl"`，所有带 `__custom__` 的子文件同样受到完整保护）。
- **专属保留文件**：像 `~/.config/niri/monitor.kdl` 这类按名引用的文件由系统自动守护，直接编辑即可。

---

## 部署后钩子

把自己的收尾脚本放进 `~/.config/nyxuri/hooks/`，每次正常部署完成后会按文件名字典序执行其中的 `.sh`。单个脚本最多运行 30 秒；失败或超时会提示，但不会阻塞后续脚本。`nyxuri test` 不会执行这些钩子，普通卸载也会保留它们。

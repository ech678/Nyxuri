```text
Nyxuri
├── install.sh                  # 极简引导入口
├── nyxuri/                     # Python 核心引擎（零 pip 依赖）
├── shell/                      # Nyxuri Shell（自研 QML/Qt6 桌面外壳，实验性）
└── plugins/                    # 一切皆插件：桌面能力 × 供给声明
    ├── fastfetch/              # 系统信息展示
    ├── fcitx5-rime/            # 动态 Material You 输入法皮肤与配置
    ├── fish/                   # Shell 别名与实用函数
    ├── greeter/                # Noctalia Greeter 登录界面集成
    ├── kitty/                  # 终端模拟器与透明度形态
    ├── mango/                  # MangoWM 窗口管理器与动作调度脚本
    ├── niri/                   # 窗口管理器与动作调度脚本
    ├── noctalia/               # 桌面外壳、主题同步、Orbit 星环与壁纸选择器
    ├── starship/               # 终端提示符
    ├── theme/                  # 共享 matugen 主题模板池
    ├── wallpapers/             # 配套壁纸与动态视频包下载钩子
    ├── xdg-desktop-portal/     # Portal 路由（主题与录屏分流）
    ├── zed/                    # 代码编辑器配置
    └── …                       # nautilus qq steam 等 18 款仅包声明插件
```

配置采用原子部署。你的私有改动跨更新与形态切换永久保留：各应用主配置里预置了
个人挂载文件（Niri、Kitty 均有），直接编辑即可，不会被部署覆盖；按名引用的文件
（如 `~/.config/niri/monitor.kdl`）同样自动守护。

---

## 钩子机制与分层

Nyxuri 将自动化收尾严格区分为两个物理层级：

### 1. 用户部署后钩子 (`~/.config/nyxuri/hooks/`)
把个人的收尾脚本放进 `~/.config/nyxuri/hooks/`。每次正常部署（`nyxuri install` 或更新）完成后，会按文件名字典序执行其中的 `.sh` 脚本。单个脚本执行限时 30 秒；失败或超时仅记录警告，不阻塞后续流程。`nyxuri test` 会跳过用户钩子，常规卸载也会保留它们。

### 2. 插件生命周期钩子 (`plugins/<plugin>/hooks/`)
插件通过自身的 `plugins/<plugin>/manifest.toml` 声明受控副作用（如 `post_install = "setup-rime"` 或壁纸大包下载 `install-pack`）。这些钩子由插件自身持有，仅由内核事务引擎在插件启用（`nyxuri on`）、停用（`nyxuri off`）或更新重放（`replay_enabled_hooks()`）时调度执行。用户无需向此处放置文件。

# Orbit Translate — 划词翻译浮窗与渠道设置

> 一次性（one-shot）划词翻译工具：读取 Wayland PRIMARY 选区，在指针下方弹出 Material 3 色调浮窗，
> 并行展示多个翻译渠道的结果。入口：`configs/noctalia/tools/orbit-translate.py`；实现：
> `configs/noctalia/tools/orbit_translate/`（`ui.py` 浮窗、`widgets.py` 自适应滚动与语言菜单、
> `geometry.py` 定位、`engine.py` 并发调度、`providers.py` 渠道协议、`tui.py` 设置界面、`theme.py` 调色）。
> 调色与 Orbit 启动器共用 `~/.cache/nyxuri/palette.toml`。

## 入口与动作

| 触发 | 链路 | 结果 |
|---|---|---|
| `Alt + E` | `binds.kdl` → `shell-action.sh translate` → `orbit-translate.py` | 捕获选区并弹出翻译浮窗 |
| Orbit › System Tools › Translate（`4`） | `cmd = "translate"` → `niri-scratch-toggle.sh` → `kitty --app-id scratchpad --title Translate -e orbit-translate.py --settings` | 在浮动 Scratchpad Kitty 中打开渠道设置 TUI |
| 终端 | `orbit-translate.py --settings [--config PATH]` | 同上，`--config` 只用于检查独立文件 |
| 终端 | `orbit-translate.py --check-deps` | 不开窗口，只检查 `wl-paste` / `niri` / GTK3 / GtkLayerShell |

`cmd = "translate"` 是数据而非 shell 命令（与 `clean` 相同的别名约定，见
[orbit-launcher](orbit-launcher.md)）；`shell-action.sh` 在自研 Shell 模式下照常把 `translate`
转交 `--action`，与 `wallpaper-picker` 一致。

## 生命周期（零常驻）

```
Alt+E ─► orbit-translate.py
          ├─ wl-paste --primary --no-newline（capture_timeout_ms 有界）
          ├─ 读取配置 → ProviderEngine 先于 GTK import 启动（ResultRelay 缓冲早到结果）
          ├─ import GTK3 + GtkLayerShell → 全屏 OVERLAY 层 surface（键盘 EXCLUSIVE）
          ├─ 指针 enter 事件到达 → 定位面板 → ResultRelay 回放结果、增量追加卡片
          └─ 全部完成后开始闲置倒计时（dismiss_after_ms）→ 退出
```

- 每次快捷键一个短生命周期进程：无 daemon、托盘、翻译缓存或历史。
- 渠道请求在线程池中并行（`max_parallel`，默认 8，上限 16），共享一个懒加载 TLS context。
- 鼠标停留、选择文字、滚动、语言菜单展开或拖动期间暂停闲置倒计时。
- 只展示成功卡片，按渠道顺序稳定排列；全部失败时显示一条“无可用译文”提示。

## 定位与布局

- **定位**：niri 下 GDK 全局指针查询返回 (0,0)，因此以 map 后约 25ms 到达的 `enter` 事件坐标为准。
  `geometry.place_panel` 让面板左缘落在指针左侧 20px、顶部在指针下方 16px；下方空间不足且上方更宽时，
  改为以 `valign=END` 向上生长，不遮挡选中文本。收不到指针事件时延迟居中（`center_panel`）。
- **尺寸**：面板宽 340px；结果区默认 340px、最高 520px，并随所在侧的剩余空间封顶。
  `FitScrolledWindow` 按宽度计算自然高度（GTK3 `ScrolledWindow` 默认忽略宽度），内容少时收缩、过长时内部滚动。
- **语言菜单**：源 / 目标语言为胶囊按钮，`LanguageMenu` 在按钮下方展开（仅下方无空间时翻到上方），
  约束在面板范围内；菜单打开时，面板外的点击只关闭菜单，`Esc` 先关菜单再关浮窗。
- **操作**：`Super + 左键拖动`移动面板，`Super + 右键拖动`调整大小（宽 300–560，高 240–860）。
  复制按钮在卡片标题行，复制后短暂显示“已复制”。

## 调色

`theme.load_palette()` 依次读取 `nyxuri/palette.toml` → `nyxniri/palette.toml` →
`noctalia/starship-palette.toml`，损坏或缺失时使用内置色。浮窗使用 M3 色调角色
（`surface_container*`、`*_container`、`outline_variant`、`secondary`、`tertiary`、`error`），
缺失角色由 `mix()` 从基础色推导。标题图标固定为琥珀色（`#ffb74d`），不随壁纸变化。
TUI 使用同一加载器，终端保留默认（透明）背景，`NO_COLOR=1` 时只用文字与边框表达层级。

## 配置

- 路径：`${XDG_CONFIG_HOME:-~/.config}/noctalia/tools/orbit-translate__custom__.toml`。
- 仓库附带同名模板（免费预设：仅启用 MyMemory，`en → zh-CN`）。Dunder 规则：首次部署后冻结，
  后续 update / preset 切换保留用户版本（见 [file-preservation](file-preservation.md)）。
- 根级键：`source` / `target` / `capture_timeout_ms` / `request_timeout_ms` / `max_chars` /
  `max_parallel` / `dismiss_after_ms` / `capture_primary` / `max_cards` / `show_source` / `auto_copy`；
  渠道为 `[[providers]]` 数组（`id` / `name` / `type` / `enabled` + 类型专属字段）。
- 渠道类型：免费 / 公共接口 `mymemory` `google` `deepl` `bing` `bing_dict` `cambridge_dict` `lingva`
  `yandex` `ecdict` `transmart` `tatoeba`；自建 `libretranslate`；AI `openai_compatible`
  `openai_responses` `anthropic` `gemini` `ollama`；本地 `command`（参数数组，不经 shell）。
  公共接口的请求参数与解析对齐 Pot，默认关闭，可能限流或下线。
- 词典 / 例句类渠道（`bing_dict` `ecdict` `tatoeba`）只接受短词组（≤4 词、≤48 字符、无句内断句），
  长句直接跳过，不浪费请求。
- Lingva 把 `zh-TW/HK/MO/Hant` 映射为 `zh_HANT`；回显原文且 `detectedSource` 不等于目标语言时判为空结果
  （部分公共实例对所有语言对回显输入）。

## 凭据

TOML 拒绝明文 `api_key`。可用 `api_key_env` 指向环境变量，或在 TUI 中按 `K` 把 Key 写入
KWallet（`kwallet-query`）/ Secret Service（`secret-tool`），TOML 只保存 `api_key_secret` 引用。
Key 经 stdin 传递，不进 argv 或日志；钱包不可用时安全失败，不降级为明文文件。
携带凭据的请求拒绝跨源重定向。两个钱包工具都是可选依赖。

## 设置 TUI

标准库 `curses`，沿用 [tui-switcher](tui-switcher.md) 的视觉语言（`❯` 指针、`[✓]`/`[ ]` 启停、
`── 标题 ──` 分区、`[键] 操作` 提示、圆角对话框）。`空格`开关、`a` 添加 AI 渠道、`m` 从 models.dev
搜索提供商与模型、`e` 编辑、`K` 存 Key、`t` 示例测试、`d` 删除、`s` 显式保存、`?` 帮助。
保存前与运行时同一套校验，创建 `0600` 备份后原子替换；外部修改冲突时拒绝覆盖。

## 缓存（仅公共元数据）

| 路径 | 内容 | 时效 |
|---|---|---|
| `~/.cache/orbit-translate/models-dev-v1.json.gz` | models.dev 精简目录（仅 TUI 按 `m` 时加载） | 24h，过期可后台刷新 |

不缓存译文、选区、Key 或健康报告。结果卡片不带品牌图标，只显示渠道名文本。

## 依赖

`configs/noctalia/.module.toml` 声明 `python-gobject`、`gtk-layer-shell`、`wl-clipboard`（`wl-paste`），
PKGBUILD 由 `gen-deps.py --update` 汇聚（见 [packaging](packaging.md)）。`kwallet-query` /
`secret-tool` / Ollama 为可选。

## 测试

`tests/test_translate_*.py`（194 项）经 `tests/translate_support.py` 把 `configs/noctalia/tools`
放入 `sys.path`，并让每个模块运行在 `TempEnv` 内。涵盖配置校验、渠道协议与解析、定位几何、
ResultRelay、凭据脱敏、models.dev 目录、TUI（含 PTY 实测）与浮窗交互。真实 GTK surface 测试需
显式开启：`ORBIT_GTK_ACCEPTANCE=1 python3 -m unittest tests.test_translate_popup_native`。
`Alt+E` 绑定、Orbit 菜单项、`shell-action.sh translate` 与 `niri-scratch-toggle.sh translate`
的契约分别在 `test_translate_integration.py` 与 `test_config_scripts.py` 中固定。

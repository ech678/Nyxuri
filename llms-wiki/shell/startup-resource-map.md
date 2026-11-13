# Shell 启动与资源归属

> 本页说明当前启动路径和资源 owner；运行状态以容器日志、`shell metrics` 和消费者生命周期测试为准，静态声明不代表已实例化。

## 启动路径

1. `nyxuri-shell` 配置导入路径，计算 QML/JS/qmldir/manifest.toml 内容及 qs 可执行文件身份，选择独立编译缓存。版本身份以可执行文件内容、路径和 stat 为准，不再为版本号额外启动 Qt 进程。
2. `shell.qml` 注册展示池和服务池。import 只做类型注册，不等于实例化插件窗口；设置诊断经 ActionGateway.settingsHost 的窄接口读取，不额外导入整套设置 UI。
3. `PluginRegistry` 扫描插件 manifest；`StateProjection.primed` 之后，宿主 Repeater/Loader 按账本装配五类插槽。未启用插件保持 Loader inactive。
4. `IPC_READY` 是 IPC 就绪标记；真实首帧由窗口 `frameSwapped` 报告。两者分别计时，不将 callLater 标记当作实际呈现。
5. `ShellStartupService` 在真实首帧后逐个执行后台队列。FontService 的字体角色同步可用，设置用选项列表排在首帧后构建。

## 资源归属

| 资源 | Owner | 创建或运行条件 | 回收条件 |
| --- | --- | --- | --- |
| 插件入口 Loader | shell.qml | 账本启用且满足插槽仲裁 | 单元关闭；锁屏持有例外 |
| 天气 backend、预测模型、请求和刷新 Timer | WeatherService / WeatherBackend | 至少一个消费者租约 | 最后一个租约释放，Loader 销毁 backend |
| CPU、内存、磁盘 stream | SystemMonitorService | 消费者请求模块 | 最后一个相应模块消费者离开 |
| Bar 资源订阅 | ResourceUsageMonitor | 目标和所属窗口可见 | 隐藏或销毁；多屏实例使用独立 owner |
| 字体选项列表 | FontService | 首帧后后台任务，或早期显式选字体 | 单例生命周期；不重复枚举初始字体 |
| Spotlight 结果树 | LauncherWindow.resultsLoader | 开窗或关闭动画尚未结束 | 关闭动画结束后卸载；重开重新创建 |
| 媒体位置 Timer | MediaService | 有位置消费者、支持位置且播放中 | 暂停或最后位置消费者离开 |
| 歌词 tick / 校准 | LyricsService | 页面 active、媒体播放；tick 另需歌词存在 | 页面退出、暂停或销毁 |
| Cava | 域内媒体 backend | 可见消费者需要音频谱 | 无消费者或停播 |
| 日志目录与轮转 | LogService | 首次 flush | 短进程退出，不在构造时单独 mkdir |
| 应用使用历史目录 | SpotlightAppUsage | 首次保存 | mkdir 完成后写入；读取不要求预建目录 |
| 配置迁移 Python | ConfigService | 缺 schema 戳或存在旧 keystone 配置 | 迁移完成；当前配置直接读取 |
| Niri IPC / 版本探测 | NiriDriver | 原版 Niri 能力存在 | 断连、超时或服务销毁 |

## 观察方式

`ShellStartupService.qmlCensus()` 记录宿主 Loader 当前 active、loaded、status，以及显式登记的 Timer/Process/FileView/Connections。Canvas、纹理和 layer 没有统一的运行时枚举接口，缺失值保留为 null，不写成零。

静态清单可以在宿主生成，不启动图形环境：

```bash
python3 shell/scripts/dev/resource_inventory.py --root shell --format json --output /tmp/resources.json
python3 shell/scripts/dev/singleton_inventory.py --root shell --format json --output /tmp/singletons.json
python3 shell/scripts/dev/model_cache_inventory.py --root shell --format json --output /tmp/models.json
```

真实内存、CPU、首帧与回收必须走 [容器基准](development.md)。完整验收条件见 [性能计划](performance-plan.md)；不根据对象声明数量推断收益。

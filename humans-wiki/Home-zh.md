Nyxuri 是 Arch Linux / CachyOS 上的 Material You 桌面套件与管理工具。
安装方法见根目录 README；本 Wiki 介绍配置、形态、快捷键、CLI 命令和故障排查。

### 从 AUR 安装（Arch / CachyOS 推荐）

```bash
paru -S nyxuri-git        # 管理引擎 + 配置插件 + Nyxuri Shell，一包全量
nyxuri install full       # 或按插件自由组装桌面：nyxuri on <插件>
```
> 安装即进入系统包模式：更新交给 pacman。桌面软件不捆绑——启用哪个插件才装它需要的软件。

---

## 文档索引

| 主题 | 内容 | 文档 |
| :--- | :--- | :--- |
| 插件架构与自定义 | 目录架构、私有改动保留机制、两层钩子分层 | [查看文档](Configuration-zh) |
| 形态与槽位轴 | Kitty / Niri 官方形态、槽位轴、私有形态制作 | [查看文档](Forms-zh) |
| 快捷键全景图 | 窗口与列导航、桌面外壳网关、nyxhelp 速查 | [查看文档](Keybindings-zh) |
| CLI 命令参考手册 | 插件管理、安装更新、快照回退与卸载全表 | [查看文档](CLI-Reference-zh) |
| 常见故障排除指南 | DDC 冲突、双显卡渲染黑块、样式白屏排查 | [查看文档](Troubleshooting-zh) |

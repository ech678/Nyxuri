遇到问题优先运行 `./install.sh doctor`。

---

## Noctalia 启动卡死
多为 `ddcutil` 扫描 I2C 总线超时（NVIDIA 常见）。

在 `~/.config/noctalia/noctalia-config.toml` 里禁用 `ddcutil`：

```toml
[brightness]
enable_ddcutil = false
```

亮度键仍然可用：笔记本内屏走 Noctalia 背光，外接显示器继续用 `ddcutil`。除非你希望由 Noctalia 自己管 DDC，否则保持关闭。

---

## 浏览器视频叠画、黑块或整窗变透明
核显 + NVIDIA 独显的机器曾被强制走 NVIDIA 视频驱动。

旧版只要 `lspci` 里出现 NVIDIA，就会打开 `GBM_BACKEND=nvidia-drm` 和 `LIBVA_DRIVER_NAME=nvidia`。混合显卡笔记本的桌面仍在核显上合成，Chromium/Brave 却可能在独显硬解，再交回核显显示——少数视频就会把窗口画花。

更新并重新部署 Nyxuri。默认配置不再指定 GPU 驱动，部署也不再根据 PCI 设备改写环境变量；PCI 列表不能确认实际负责渲染的 GPU。有特殊驱动需求时，在 `~/.config/niri/__custom__.kdl` 中自行配置。

默认配置同时移除了旧的 `ELECTRON_OZONE_PLATFORM_HINT "auto"`，部分旧 Electron 应用可能改用 XWayland。正常部署会更新主配置，但不会清理个人覆盖、个人预设或历史快照，也不会改变现有会话环境；重新登录后再检查效果。

---

## 插件仓库损坏
Noctalia 拉取插件卡住。

重置插件仓库：

```bash
git -C ~/.local/state/noctalia/plugins/sources/community/repo reset --hard HEAD
git -C ~/.local/state/noctalia/plugins/sources/official/repo reset --hard HEAD
```

---

## Greeter 同步要密码
加一条 Polkit 免密规则（`nyxuri greeter install` 会自动写入）。

手动添加 Polkit 规则：

```bash
sudo bash -c 'cat > /etc/polkit-1/rules.d/50-noctalia-greeter.rules << EOF
polkit.addRule(function(action, subject) {
    if (action.id == "org.noctalia.greeter.sync-appearance" &&
        subject.isInGroup("wheel")) {
        return polkit.Result.YES;
    }
});
EOF'
```

---

## Nautilus 或 Libadwaita 应用白屏 / 深色模式失效
旧 CSS 覆盖了系统主题。

如果之前用过 Noctalia 自带 GTK 模板或其他美化工具，会在 `~/.config/gtk-4.0/` 生成 `noctalia.css` 或 `gtk.css`，GTK4 会优先加载并写死白色背景。

运行主题同步，或手动删掉残留文件：

```bash
nyxuri theme sync
# 或手动删除：
rm -f ~/.config/gtk-4.0/gtk.css ~/.config/gtk-4.0/noctalia.css ~/.config/gtk-3.0/gtk.css ~/.config/gtk-3.0/noctalia.css
```

---

## Brave 切换主题后不变色
Brave 冷启动 bug（非 Nyxuri 问题）。

Brave 在非 GNOME Wayland 上冷启动时，portal 主题信号订阅未正确初始化，`nyxuri theme toggle` 后不变色。去 `brave://settings/appearance` 手动切一次主题模式（如"经典"→"GTK"→"经典"）即可唤醒，此后实时跟随，无需重启 Brave；重启 Brave 后需再次唤醒。

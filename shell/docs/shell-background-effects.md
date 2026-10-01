# Shell 背景透明与模糊

控制中心的“通用 → 透明与模糊”只调整 Clavis 窗口的外层背景。
文字、图标、图片、按钮和内部卡片不会继承额外透明度。背景模糊由
niri 的 `ext-background-effect` 实现，需要 niri 26.04 或更新版本。

Clavis 管理 `~/.config/niri/clavis/effects.kdl`。niri 默认对客户端
请求的效果使用 X-Ray，因此“仅模糊壁纸”开启时片段不生成任何
`background-effect` override。关闭该选项时，片段只为
`^clavis-shell-` layer namespace 以及 Clavis 设置/文件选择窗口配置
`xray false`。片段不会写入 `blur true`，也不会匹配壁纸、overview、
锁屏、截图选区或输入捕获 surface。

主配置必须包含：

```kdl
include optional=true "clavis/effects.kdl"
```

若缺少该 include，设置页面会显示“Niri 集成”。只有点击“配置”后，
Clavis 才会先创建 `config.kdl.clavis-backup`，验证候选配置，再以原子
替换方式更新主配置。include 已存在时不会重复追加。

niri 的全局 `blur` 块仍由用户管理。若其中配置了：

```kdl
blur {
    off
}
```

Clavis 提交的 Region 不会产生可见模糊；Clavis 不会修改或删除该设置。

# dux bar 机制基线（B0 整抄，inert）

B 卷（Bar & Island 统一）机制源整抄件，物理 `cp` 自本地参考树
`references/dux-shell/`（DMS/DankMaterialShell 系；MIT，verbatim 许可证
文本见 shell/LICENSE 附录 `DankMaterialShell-MIT.txt`）。

- 承载能力：widget 注册表（WidgetModel 的 componentNames 映射 +
  SurfaceWidgetFactory 的组件映射与 getWidgetComponent/getWidgetVisible +
  SurfaceWidgetHost 的注册表消费端）、每部件默认值模式
  （BarWidgetDefaults，含 island 条目）、密度预设（DensityPresets，
  4 级 + transition() 语义）。
- 状态：inert 基线——无任何消费者、不进装载闭包、不影响运行。B4（高度
  与自由度）起按四类裁剪清单定向剪裁上岗，见
  llms-wiki/shell/bar-island.md。
- 与源逐字节一致，零偏离。
- 「每文件有真实消费者」门禁豁免至 B5 结账清算（shell/ROADMAP.md §B0
  显式豁免）：届时未晋升文件处决，晋升文件脱离 vendor/ 恢复全部门禁。

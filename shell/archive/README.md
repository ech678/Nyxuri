# archive/ 封存登记

> 2026-10-31 定向瘦身（`45361df`）：物理删除侧边栏抽屉，封存三族设置页至此并
> 下架对应路由——displays（排布画布/配置页/服务）、autostart、default-apps；
> GammaControlPage（夜光）不随封存，归位 `plugins/sidebars/quicksettings/`。
> 2026-11-01 作者裁决**保留本目录**（S0-4 收窄版清算拍板），不处决。

## 引用关系（动这里必须先动测试）

- 无运行时消费者；但 `tests/shell/test_shell_architecture.py` 的迁移落位契约
  钉住 `archive/settings/autostart/AutostartService.qml` 与
  `archive/settings/displays/DisplayConfigService.qml` 的存在性，且后者作为
  NiriService 单例引用样本被点名——删除或搬动需同步改契约。
- 复活或处决一律从 live 树外操作：迁回 `plugins/`（随 S0-3 去中心化落位）或
  整目录删除，禁止就地解封（archive 内文件不得被 live 树 import）。

## 复活条件

- **displays**：niri 提供输出排布 IPC 面或出现真实使用诉求时整族迁回，按
  S0-3 归属域插件（画布/事务流随页走）。
- **autostart / default-apps**：无重新启用计划；若供给面复活，归引擎 manifest
  声明（packages / hooks），不回植 Shell 页面。

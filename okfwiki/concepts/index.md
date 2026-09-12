# NyxNiri OKF Wiki 索引

> 本文件由引擎维护，人工只读。每次 commit 后 log.md 更新，索引按需刷新。

## 总纲

- [[nyx]] — 项目完整蒸馏（架构、合约、扩展路径）

## 基础设施域 infra

- [[infra/constants]] — 项目常量、色阶、依赖列表、仓库 URL
- [[infra/core]] — Environment 解析、锁、日志、path 原语、超时包装
- [[infra/i18n]] — 双语引擎、msg() 协议、translations.toml 结构
- [[infra/network]] — 多镜像 git pull/clone、超时降级、curl 容错

## 部署域 deploy

- [[deploy/atomic]] — atomic_replace_item 合约、Dunder walk、preserve 快照
- [[deploy/manifest]] — .module.toml 解析、两轴发现（配置 vs 可选）
- [[deploy/preset]] — active 文件读写、src 四分支、切换时序
- [[deploy/templates]] — /home/user 占位符替换、仅影响目标 app
- [[deploy/assets]] — 壁纸部署（离线 fallback + 外部 pack 下载）
- [[deploy/deploy]] — 部署编排器、前置检查、完成界面

## 状态域 state

- [[state/backup]] — 快照生命周期、prune 上限 30、回滚合约
- [[state/uninstall]] — 勾选式卸载、执行顺序铁律

## 模块域 module

- [[module/fcitx]] — NyxMellow 皮肤、主题注册、状态标记
- [[module/greeter]] — Noctalia greetd 登录界面、系统级写入
- [[module/fisher]] — fisher 插件管理器、版本固定
- [[module/gtktheme]] — GTK Material You 主题渲染
- [[module/lifecycle]] — 模块失败中断上抛合约

## UI 域 ui

- [[ui/cli]] — COMMANDS 分发、命令契约、exit code 传播
- [[ui/menus]] — 菜单导航树、组件选择编排
- [[ui/tui]] — TUI 组件、TerminalGuard、ANSI 输出协议
- [[ui/doctor]] — 诊断检查项体系、bug report 导出

## 包管理域 pkg

- [[pkg/backend]] — pacman/paru/yay/shelly 命令构造
- [[pkg/detection]] — 依赖探测、独立缓存策略
- [[package/abuild]] — PKGBUILD 生成、gen-deps.py 脚本

## 测试域 test

- [[test/strategy]] — TempEnv 隔离、mock 层级、契约测试

## 参考

- [[llms-wiki/llms]] — LLM wiki 索引（陈述参考，非生成）
- [[AGENTS.md]] — 祈使规则（铁律、必跑命令、工作流）

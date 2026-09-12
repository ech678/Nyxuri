# GPU 设备诊断与兼容边界

默认 Niri 配置不再包含 `GBM_BACKEND`、`__GLX_VENDOR_LIBRARY_NAME`、
`LIBVA_DRIVER_NAME`，部署不探测硬件或改写驱动变量。旧的
`ELECTRON_OZONE_PLATFORM_HINT "auto"` 也已移除。

## 诊断报告

`nyxniri/deploy/hardware.py` 仅保留纯文本函数 `classify_gpu_devices(text)`。
`doctor.py` 的报告复用已采集的 `lspci` 输出，按 VGA / Display / 3D controller
设备行分为 NVIDIA、其他 GPU、两者共存或未知；音频设备不算 GPU。
探测失败、空输出或未识别到 GPU 设备时显示 `Unknown`。

PCI 设备分类不代表合成器、视频解码或应用实际使用的 GPU。报告明确标注这一限制。
没有额外探测、进程缓存或配置写入，常规 doctor 不增加输出。
现有报告命令使用 `LC_ALL=C`，默认超时 15 秒。

## 部署与兼容

主配置通过正常 `atomic_replace_item` 部署更新，重复部署结果稳定。
`__custom__` 文件、个人预设和历史快照不清洗，已有会话环境不变；
重新登录后再检查效果。有特殊驱动需求时由用户在个人覆盖中配置。

部分旧 Electron 应用移除旧设置后可能改用 XWayland。

路径占位符和截图目录适配保留。`deploy_selected_configs` 只渲染所选应用的模板，
仅部署其他应用不会修改 Niri 配置。预设切换仍只部署该应用，不运行部署后服务。

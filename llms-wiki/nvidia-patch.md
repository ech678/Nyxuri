# NVIDIA Patch — 硬件自适应层（为何不塞进 preset）

> NVIDIA env 解注释是**硬件自适应**（自动检测、用户不可见），不是**预设**（显式切换、用户可见）。
> 强塞进同一机制是 category error。源码：`nyxniri/deploy/hardware.py`。

## 现状

`configs/niri/config.kdl` 三行注释掉的 env（非 NVIDIA 机器必须保持注释，强开会报错或
行为异常）：

```kdl
// GBM_BACKEND "nvidia-drm"
// __GLX_VENDOR_LIBRARY_NAME "nvidia"
// LIBVA_DRIVER_NAME "nvidia"
```

`_phase_hardware_patches`（`hardware.py`）：
- `_nvidia_role()`：跑 `lspci`（`LC_ALL=C`），缓存角色到 `_NVIDIA_ROLE`（进程内）。
- `_classify_nvidia_role(text)` 纯解析，不跑命令：
  - **primary**：NVIDIA 是 VGA/Display 设备，或机器上只有 NVIDIA GPU → 解注释三行。
  - **hybrid**：NVIDIA 只作为 3D controller 出现，旁边还有 AMD/Intel 的 VGA/Display
    → **保持注释**（若旧部署已解开则重新注释回去）。
  - **none**：没有 NVIDIA GPU → 保持注释（同样会把旧部署解开的行注释回去）。
- 判定不能简化成 stdout 含 `"nvidia"`。混合显卡笔记本的桌面通常跑在核显上；强开
  `nvidia-drm` / `LIBVA_DRIVER_NAME=nvidia` 会让 Chromium 在独显硬解、在核显合成，
  部分视频出现叠画、黑块或窗口变透明。
- 想把 NVIDIA 当合成器 GPU 的用户，仍可在 `__custom__.kdl` 里自己解开这三行。

由全部署流水线 `deploy_selected_configs` / `test_deploy` 调用；apply_preset 的窄路径**不调**
（切预设不该顺带改硬件 patch）。

## 三个选项，选 A（保持现状硬编码）

| 选项 | 机制 | 代价 |
|---|---|---|
| **A. 保持现状** | `_phase_hardware_patches` 硬编码 | 一处特殊 case 代码 |
| B. overlay 预设 | preset 只含差异文件，deploy 先默认再覆盖 | 引入 overlay 概念，deploy 逻辑复杂 |
| C. full 预设 | `configs/niri/presets/nvidia/` 完整 copy | 配置重复，更新要双写，易漂移 |

选 A。NVIDIA 是硬件自适应（自动检测、用户不可见），预设是用户选择（显式切换、用户可见）——
两者是不同概念，强塞进同一机制是 category error。这正是用户感到"麻烦"的直觉来源。
hybrid 只是同一层里更精确的检测，不是第二种硬件 patch，不构成 overlay 预设的触发。

## 延迟决策

硬件适配累积到 **>3 处**（AMD、多显示器、低性能模式…）时，overlay 预设才有规模回报：
overlay 是新的 manifest 字段 `overlay = true`，deploy 先默认再 overlay 差异文件。当前 ≤1 处，
保持 `_phase_hardware_patches` 硬编码作为**独立的硬件自适应层**，不塞进 preset 系统。

> 预设接受全树复制（风味受人工策展约束、个位数、drift 管得住）；硬件 patch 否决全树（选项 C）
> 因适配可能膨胀到十几处、drift 是另一个数量级。同涉"复制"但规模量级不同，处理方式不同不是矛盾。

# Packaging — AUR 打包与自动依赖汇聚

> NyxNiri 支持通过 Arch Linux AUR（`nyxniri-git`）进行系统级安装。
> 源码：`nyxniri/packaging/`，核心依赖汇聚工具：`gen-deps.py`。

## 单真值依赖原则 (§5.7)

为了避免在多个地方维护重复的软件包列表，依赖关系遵循**单一真值**：
- 桌面组件的具体包依赖写在各自的 `configs/<app>/.module.toml` 中。
- 可选软件的包依赖写在 `configs/.optional-apps.toml` 中。
- 基础系统核心包写在 `nyxniri/constants.py` 的 `CORE_DEPS` / `AUR_DEPS` 中。

PKGBUILD **绝不手工硬编码维护依赖数组**，而是由生成脚本统一计算。

## gen-deps.py 汇聚算法

通过 `compute_depends()` 扫描全仓库 manifest 进行两轴分类：

1. **`depends`（强制依赖）**：
   - 所有可部署配置应用（`is_deployable=True`）所声明的 `packages_repo` 与 `packages_aur`
   - ∪ 系统核心依赖 `CORE_DEPS`（如 Python 3.11+、git、rsync、fish 等）
   - ∪ 必需 AUR 依赖 `AUR_DEPS`（如 niri、noctalia 等）
2. **`optdepends`（可选依赖）**：
   - 所有声明为可选安装应用（`is_optional=True`，来自 `.optional-apps.toml`）的包，附带其中文/英文 label 说明（如 `fcitx5-rime: 中文输入法 Rime 引擎`）。

## 自动更新契约

在提交版本或修改应用依赖后运行：

```bash
python3 nyxniri/packaging/gen-deps.py --update
```

该命令会自动寻找 `PKGBUILD` 中的特征标记注释块（`# >>> depends ...` 与 `# >>> optdepends ...`）并就地重写。测试套件 `tests/test_packaging.py` 会验证生成的依赖块与当前源码的一致性。

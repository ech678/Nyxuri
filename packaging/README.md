# packaging — AUR 上架手册

`nyxuri-git` 包含引擎、`plugins/` 和 `shell/`。安装后的 `.system-install` 标记
启用系统包模式：由 pacman 更新，引擎不运行 git pull。

## 文件

| 文件 | 职责 |
| --- | --- |
| `PKGBUILD` | 包配方。`depends` 只有引擎运行时（`python`）；每个插件的包都在 `optdepends`——`nyxuri on <plugin>` 披露并代装，pacman 不强塞桌面 |
| `gen-deps.py` | 依赖数组自动汇聚：加插件只动 `plugins/*/manifest.toml`，跑 `python3 packaging/gen-deps.py --update` 重写生成块。`ENGINE_OPTDEPENDS` 准入标准：仓库代码直接 spawn 它 |
| `nyxuri-git.install` | libalpm 提示钩子：升级只换 `/usr/share/nyxuri` 蓝图，永不自动重部署用户配置 |

## 发布流程（nyxuri-git 已上架；以下为更新推送流程）

1. **账号**：aur.archlinux.org 注册（arch 论坛账号不通用；注册关闭期可在
   aur-general 邮件列表请求管理员手动建号）。账号设置页 SSH Public Key 挂
   `~/.ssh/id_ed25519.pub`，验证：`ssh aur@aur.archlinux.org` → `HI <user>!`
2. **干净构建复验**：`cd packaging && extra-x86_64-build`（devtools），随后
   `namcap nyxuri-git-*.pkg.tar.zst` 对照下方假阳性清单，E 级应只剩已定性条目
3. **三步上架**（AUR 仓库只收三件套）：

   ```bash
   git clone ssh://aur@aur.archlinux.org/nyxuri-git.git    # 空仓库警告=正常，克隆即创包
   cp PKGBUILD nyxuri-git.install /path/to/nyxuri-git/ && cd /path/to/nyxuri-git
   makepkg -od --nodeps && makepkg --printsrcinfo > .SRCINFO
   git add PKGBUILD .SRCINFO nyxuri-git.install && git commit -m "initial import" && git push
   ```

4. **安装文档核对**（本地面板内容，双语各一份；README 已回填，
   humans-wiki Home 顶部待补）：

   ````markdown
   ### 从 AUR 安装（Arch / CachyOS 推荐）
   ```bash
   paru -S nyxuri-git        # 管理引擎 + 插件蓝图 + Nyxuri Shell，一包全量
   nyxuri install full       # 或按插件自由组装桌面：nyxuri on <插件>
   ```
   > 安装即进入系统包模式：更新交给 pacman。桌面软件不捆绑——启用哪个插件才装它需要的软件。
   ````

   回填位置：`README.md` / `README.zh-CN.md` 的 Install 段置顶（Git 仓库段降级为
   「开发」），`humans-wiki/Home.md` / `Home-zh.md` 顶部补 Install 块。

5. **日常更新**：GitHub push main 即新版，AUR 侧零操作；只有依赖数组变化时
   重跑 `gen-deps.py --update` 再推一次。

## namcap 已定性假阳性（勿"修复"）

| 报错 | 定性 |
| --- | --- |
| `glib2 detected and not included` | `gi.repository` 经 `python-gobject` 传递（noctalia 单元声明链覆盖）；namcap 不解析依赖树 |
| `python-typing_extensions detected` | vendor kdl 的 `if TYPE_CHECKING:` 块内兼容 fallback，运行时不触达（引擎要求 3.11+） |
| `QML module 'qs.plugins.*' is an uninstalled dependency` | quickshell root-relative import 语义，不是 QML 包 |
| `Dependency bash detected and implicitly satisfied` | bash 由 base 保证 |

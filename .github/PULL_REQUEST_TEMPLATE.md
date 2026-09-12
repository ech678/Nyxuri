## 改动说明

<!-- 一句话说清改了什么、为什么 -->

## 验证

- [ ] `python3 -m compileall nyxniri` + `shellcheck install.sh`
- [ ] `python3 -m unittest discover -s tests -q`
- [ ] 涉及部署流程:`HOME=$(mktemp -d) ./install.sh test`

## 注意

- **禁止添加 `Co-authored-by: Claude` 署名**。GitHub 会把 Claude 计入仓库 Contributors 列表。用 Claude 辅助没问题,但提交归你本人——不要让它在贡献者里露脸。
- `configs/` 模板里的 `/home/user` 是占位符,由部署引擎替换,勿硬编码。
- 默认不指定 GPU 驱动，部署不按 PCI 设备改写环境变量。
- 涉及 `atomic_replace_item` 签名 / manifest schema / CLI 命令 / 子包结构变动时,同步更新 `llms-wiki/` 对应页。

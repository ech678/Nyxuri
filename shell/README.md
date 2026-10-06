
# Nyxuri Shell

> Nyxuri 自研桌面 Shell，基于 Quickshell、QML 与 Qt 6 构建，采用 100% 纯 QML/JS 架构。
> 上游母体为 [StatIndet/quickshell](https://github.com/StatIndet/quickshell)（Clavis，commit `91cdecb`）。

---

## 核心导航与真值体系

- **开发契约与红线**：[AGENTS.md](AGENTS.md)
- **阶段台账与当前阶段**：[ROADMAP.md](ROADMAP.md)
- **知识库索引**（全项目唯一）：[../llms-wiki/llms.txt](../llms-wiki/llms.txt)
  - 架构矩阵：[../llms-wiki/shell/architecture-matrix.md](../llms-wiki/shell/architecture-matrix.md)
  - 开发调试指南：[../llms-wiki/shell/development.md](../llms-wiki/shell/development.md)
  - 上游参考与重现：[../llms-wiki/shell/references.md](../llms-wiki/shell/references.md)

---

## 上游母体视觉基准 (Clavis Reference)


<table>
  <tr>
    <td width="25%"><a href="https://raw.githubusercontent.com/StatIndet/picture/main/clavis-shell/Screenshot%20from%202026-09-12%2015-20-21.png"><img src="https://raw.githubusercontent.com/StatIndet/picture/main/clavis-shell/Screenshot%20from%202026-09-12%2015-20-21.png" alt="Clavis Shell screenshot 1" width="100%" /></a></td>
    <td width="25%"><a href="https://raw.githubusercontent.com/StatIndet/picture/main/clavis-shell/Screenshot%20from%202026-09-12%2015-23-30.png"><img src="https://raw.githubusercontent.com/StatIndet/picture/main/clavis-shell/Screenshot%20from%202026-09-12%2015-23-30.png" alt="Clavis Shell screenshot 2" width="100%" /></a></td>
    <td width="25%"><a href="https://raw.githubusercontent.com/StatIndet/picture/main/clavis-shell/Screenshot%20from%202026-09-12%2015-32-08.png"><img src="https://raw.githubusercontent.com/StatIndet/picture/main/clavis-shell/Screenshot%20from%202026-09-12%2015-32-08.png" alt="Clavis Shell screenshot 3" width="100%" /></a></td>
    <td width="25%"><a href="https://raw.githubusercontent.com/StatIndet/picture/main/clavis-shell/Screenshot%20from%202026-09-12%2015-33-40.png"><img src="https://raw.githubusercontent.com/StatIndet/picture/main/clavis-shell/Screenshot%20from%202026-09-12%2015-33-40.png" alt="Clavis Shell screenshot 4" width="100%" /></a></td>
  </tr>
  <tr>
    <td width="25%"><a href="https://raw.githubusercontent.com/StatIndet/picture/main/clavis-shell/Screenshot%20from%202026-09-12%2015-43-18.png"><img src="https://raw.githubusercontent.com/StatIndet/picture/main/clavis-shell/Screenshot%20from%202026-09-12%2015-43-18.png" alt="Clavis Shell screenshot 5" width="100%" /></a></td>
    <td width="25%"><a href="https://raw.githubusercontent.com/StatIndet/picture/main/clavis-shell/Screenshot%20from%202026-09-12%2021-42-49.png"><img src="https://raw.githubusercontent.com/StatIndet/picture/main/clavis-shell/Screenshot%20from%202026-09-12%2021-42-49.png" alt="Clavis Shell screenshot 6" width="100%" /></a></td>
    <td width="25%"><a href="https://raw.githubusercontent.com/StatIndet/picture/main/clavis-shell/recording_20260912_15-36-29_194021.gif"><img src="https://raw.githubusercontent.com/StatIndet/picture/main/clavis-shell/recording_20260912_15-36-29_194021.gif" alt="Clavis Shell animation 1" width="100%" /></a></td>
    <td width="25%"><a href="https://raw.githubusercontent.com/StatIndet/picture/main/clavis-shell/recording_20260912_22-20-48_544529.gif"><img src="https://raw.githubusercontent.com/StatIndet/picture/main/clavis-shell/recording_20260912_22-20-48_544529.gif" alt="Clavis Shell animation 2" width="100%" /></a></td>
  </tr>
</table>

## Acknowledgements

Nyxuri Shell takes inspiration from and integrates ideas or components from projects including:

- [end-4/dots-hyprland](https://github.com/end-4/dots-hyprland)
- [Zen Browser](https://github.com/zen-browser/desktop) — palette algorithms and editor; see [source and license mapping](assets/licenses/README.md).
- [DankMaterialShell](https://github.com/AvengeMedia/DankMaterialShell)
- [Caelestia Shell](https://github.com/caelestia-dots/shell)
- [qml-niri](https://github.com/imiric/qml-niri)
- [Breezy Weather](https://github.com/breezy-weather/breezy-weather)
- [Animated Weather Cards](https://codepen.io/ste-vg/pen/GqaZbo) by Steve Gardner — the current-weather animation at the top of the sidebar weather view is a Qt/QML recreation of this web project. The original is licensed under MIT; see the [full license and copyright notice](assets/licenses/AnimatedWeatherCards-MIT.txt).
- [m3shapes](https://github.com/soramanew/m3shapes)

Third-party license notices are kept in [`assets/licenses/`](assets/licenses/).
# License

See [LICENSE](LICENSE).

# 1.4.6 构建与验证记录

- 构建环境：macOS 27.2 arm64，Python 3.13.16，Xcode/Apple 命令行构建工具。
- 上游来源：`Transformer(1.4.6)`；随后同步主线 `ba18e712d315676981a6dd5b040f040575844432`。
- 产物：`TongguiMac-1.4.6-macOS27-arm64.dmg`，约 81 MB。
- 最低系统：Info.plist 的 `LSMinimumSystemVersion=27.0`；打包的 Mach-O 架构与最低部署目标见 `BinaryDeploymentTargets.json`。
- 签名：ad-hoc 签名；未进行 Apple 公证。

## 验证结果

- Python 编译检查：主界面、候选字引擎、文字组件及四个文件转换器均通过。
- OpenCC 规则自检：繁体规范转换、简繁转换和现代/古汉语分词模式通过。
- 候选引擎：七种文字规则的输出与 OpenCC 一致；五个有一对多映射的规则共核对 5 个候选跨度，另两种规则确认不产生候选跨度。
- 格式回归：TXT、SRT、ASS、LRC、DOCX、EPUB、带文本层 PDF 均通过。
- Qt offscreen 界面检查：文字转换标签创建成功，提交文字后结果正常显示。
- 只读挂载最终 DMG 后，镜像内 `.app` 通过 `codesign --verify --deep --strict` 和 `--self-test`；版本 1.4.6、架构 arm64、最低系统 27.0。DMG CRC32 校验通过。

DMG SHA-256 记录在 `SHA256SUMS-1.4.6.txt`。构建时 PyInstaller 在含 Finder 元数据的工作副本自动签名阶段给出警告；发布脚本在清理元数据的临时副本重新签名，最终 DMG 中应用已验证通过。签名为 ad-hoc 且仅在当前 macOS 27.2 环境完成验证；未验证较旧 macOS 版本或 Apple 公证流程。

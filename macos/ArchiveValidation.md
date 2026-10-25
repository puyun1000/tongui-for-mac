# TongguiMac 1.4.5 核查记录

验证日期：2026-10-25（Asia/Shanghai）。环境：Apple Silicon / macOS 27.2（26B5112a），Python 3.13.16。

- 上游基准为 TerryTian-tech 项目 1.4.5 提交 `aba2391859910d36f52fe0983d088216b8f10c6b`；该提交的完整上游历史已合入仓库。Mac 目录同步其词典与规则，并移植 DOCX、EPUB 更新，同时保留本地界面、编码检测和 PDF 排版适配。
- 依赖锁定记录见 `requirements-lock-macos-arm64-py313.txt`。本次升级 chardet 至 7.7.0、Pillow 至 13.0.0；其他 Mac 运行依赖按锁定版本安装。第三方许可文本与版本表已随 DMG 一同提供。
- 从干净 PyInstaller 构建生成 `dist/TongguiMac.app` 和 `dist/TongguiMac-1.4.5-macOS27-arm64.dmg`。构建内置五类 OpenCC 规则资源自检通过；DMG 使用 `hdiutil verify` 校验通过。
- 现有 `verify_formats.py` 检查 TXT、SRT、ASS、LRC、DOCX、EPUB 和带文本层 PDF，全部通过。临时样例另外确认 DOCX 文本框转换，以及 EPUB 跨行内标签词组转换、注释/脚本跳过、EPUB 2 NCX 目录标签转换均符合预期；临时文件已自动清理。
- 只读挂载最终 DMG 后，应用通过 `codesign --verify --deep --strict` 与 `--self-test`。版本/构建号为 1.4.5，架构 arm64，`LSMinimumSystemVersion` 为 27.0。第三方声明及许可目录存在于镜像内。
- 对构建应用内的 219 个 Mach-O 文件逐一解析最低系统版本，目标为 11.0、13.0、15.0 和 27.0；应用整体最低要求由 Python 等核心组件决定，为 macOS 27.0。明细见 `BinaryDeploymentTargets.json`。

DMG 使用 ad-hoc 签名，未完成 Apple 公证；仅在 macOS 27.2 进行本机验证。PDF 通过提取文字和重建页面转换，版式仍可能变化；输出内容需人工校对。

DMG SHA-256：`9aa7f4cbeee27ec558ea542e522fd97fb090877adcec842c56203c7233f7ad30`。

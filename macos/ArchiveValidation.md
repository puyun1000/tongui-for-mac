# TongguiMac 1.4.4 核查记录

验证日期：2026-10-19（Asia/Shanghai）。环境：Apple Silicon / macOS 27.2（26B5112a），Python 3.13.16。

- 在新虚拟环境中按原构建脚本安装依赖、构建、签名和生成 DMG，成功；精确依赖版本见 `macos/requirements-lock-macos-arm64-py313.txt`。
- 现有 DMG 完整性校验通过；只读挂载后应用通过 `codesign --verify --deep --strict`，版本/构建号均为 1.4.4、arm64、Info.plist 声明为 13.0，但该声明与打包依赖不一致，实际运行组件最高最低目标为 macOS 27.0。
- 现有 DMG 中打包的 constants、doc_converter、epub_converter、mac_opencc、main、pdf_converter、self_test、text_converter 八个 Python 模块，与归档源码编译结果一致（比较时仅归一化代码对象中的源码文件路径）。updater 未被使用/打包，verify_formats 为独立测试脚本。
- 现有 DMG 应用通过五种 OpenCC 规则资源自检；干净构建也通过成品自检。源码运行七类实际格式转换检查：TXT、SRT、ASS、LRC、DOCX、EPUB、带文本层 PDF，全部通过。
- DMG 应用执行 offscreen Qt 启动检查，保持运行 4 秒后由验证进程结束；这项检查不代替完整图形交互验收。
- 上游来源为 TerryTian-tech/OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards，基准提交 fe735503935bc6dce401ae5ce13b8e569dfa8e07。原浅克隆的上游历史已在归档副本补全，保留 464 个原始提交。原始目录未修改。
- Apache-2.0 原许可及上游署名保留；另补充依赖版本、第三方许可文本和 Qt for Python 官方版本的许可证文本。
- 当前上传源码及完整可达历史使用 Gitleaks 默认规则扫描，未发现命中；额外检查私钥/令牌格式、签名材料文件名和个人绝对路径。扫描不等于穷尽安全审计。

现有 DMG 中的 app 经分发阶段再次签名，因此部分 Mach-O/签名文件与原 dist 目录不同；打包 Python 代码已独立验证一致。原 DMG 不做改写，补充的第三方许可文件作为独立 Release 附件同时提供。

逐个核查 139 个不同的 Mach-O 文件：组件最低目标包含 11.0、13.0、15.0、27.0，其中 Python、OpenSSL、libmpdec 与多数 Python 扩展为 27.0，PySide6/Shiboken 绑定为 15.0；未发现依赖原开发机 /Users、/opt/homebrew 或 /usr/local 路径。实际成品要求 macOS 27 或更新版本，已在 27.2 运行验证。完整组件清单见 `BinaryDeploymentTargets.json`。

当前成品为 ad-hoc 签名，未公证。原构建脚本仍保留 13.0 的元数据设置；为遵守不修改应用功能/源码的要求，本次仅更正文档。较旧系统支持需要后续重建及实测。PDF 重建可能影响版式，转换与字形结果仍需人工审校。

现有 DMG SHA-256：`22646beb9aa35b840755fa46d921363af675ea787361f31e58204a2a0860368f`。

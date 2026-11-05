# 规范繁体字形转换器 for Mac 1.4.6

本版基于 [TerryTian-tech 的 OpenCC 项目](https://github.com/TerryTian-tech/OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards) 1.4.6，并同步上游截至 2026-11-03 的 `main`（`ba18e712d315676981a6dd5b040f040575844432`）。

## 目标用户与界面

面向编辑、出版校对、字幕和电子书制作者，以及需要按《通用规范汉字表》处理繁体字形的研究者。应用采用 macOS 桌面窗口，提供“文件转换”“文字转换”“设置”“关于”四个标签页，支持拖入文件与 Finder“打开方式”。

- **文件转换**：批量处理 DOCX、TXT、MD、SRT、ASS/SSA、LRC、EPUB，以及带文本层的 PDF；输出至指定文件夹。
- **文字转换**：选择七种转换规则；一对多歧义会以红色波浪线标注，点击可查看并手动选择候选字。支持复制和清空。
- **文件选项**：DOCX 保留格式并可选择转换脚注/尾注；PDF 可标记变更；文本文件可指定编码；文件转换可选择现代或古汉语分词模式。
- **1.4.6 与后续修复**：同步更新字表、词典及候选映射；加入 EPUB `<` 特殊字符修复和 PDF 跨页词语上下文修复。

转换工具适合校对辅助，成稿仍需人工审校。PDF 通过提取文本并重建页面，版式可能变化；无文本层的扫描 PDF 无法转换。加密 EPUB、旧版 `.doc` 和独立 LLMCC AI 模块不包含在本 Mac 版中。

## 依赖与构建

转换核心采用 Python 3.13、`opencc-py` 1.4.2、PySide6 Essentials 6.11.2、jieba、python-docx、chardet、Beautiful Soup、lxml、pdf-oxide 和 Pillow；PyInstaller 6.22.3 负责打包。精确构建依赖锁定在 `requirements-lock-macos-arm64-py313.txt`，基础直接依赖列表见 `requirements-mac.txt`。Mac 版直接移植上游 `transformer-linux/` 的转换器和候选字引擎，并保留 macOS 文件访问、编码和 PDF 适配。

在 Apple Silicon Mac 上安装 Python 3.13 与 Xcode Command Line Tools 后，在本目录运行：

```sh
./build_mac.sh
```

脚本会创建隔离环境、安装锁定依赖、将仓库规则和分词资源装入 `opencc_data`、运行转换与歧义自检，再构建 arm64 `.app` 和 DMG。默认 Python 为 `/opt/homebrew/bin/python3.13`；可通过 `PYTHON_BIN` 和 `VENV_DIR` 调整位置。

手动验证：

```sh
.venv/bin/python self_test.py
.venv/bin/python verify_ambiguity.py
.venv/bin/python verify_formats.py
dist/TongguiMac.app/Contents/MacOS/TongguiMac --self-test
```

## 分发

输出文件为 `dist/TongguiMac-1.4.6-macOS27-arm64.dmg`，镜像中包含应用、许可说明和第三方许可。目标为 Apple Silicon，当前最低系统要求是 macOS 27。应用使用 ad-hoc 签名，未经过 Apple 公证；公开分发如需无提示安装，应使用开发者证书重新签名并完成公证。

上游源码和 Apache-2.0 许可保留在仓库中；第三方依赖许可见 `THIRD_PARTY_NOTICES.md` 与 `third_party_licenses/`。

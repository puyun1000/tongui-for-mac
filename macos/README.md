# 规范繁体字形转换器 for Mac 1.4.5

本目录是基于 [TerryTian-tech 的 OpenCC 项目](https://github.com/TerryTian-tech/OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards) 制作的 macOS 版本。上游基准为 1.4.5 提交 [`aba2391859910d36f52fe0983d088216b8f10c6b`](https://github.com/TerryTian-tech/OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards/commit/aba2391859910d36f52fe0983d088216b8f10c6b)，包含 1.4.5 字表、词典和 DOCX、EPUB、PDF 更新。

## 用途与界面

面向编辑、出版校对、字幕和电子书制作者，以及需要按《通用规范汉字表》处理繁体字形的研究者。应用使用 Qt Widgets 桌面窗口，支持 macOS 文件拖入和 Finder 的“打开方式”，提供：

- **文件转换**：批量处理 DOCX、TXT、MD、SRT、ASS/SSA、LRC、EPUB，以及带文本层的 PDF；输出到指定文件夹，文件名前加 `convert_`。
- **文字转换**：粘贴短文本、选择转换规则、复制结果。
- **七种基本规则**：繁体转规范繁体、旧字形转新字形、前两者的保留简体变体、繁体转简体、异体字转简体、简体转规范繁体。文件转换另可选择现代或古汉语结巴分词模式。
- **格式选项**：DOCX 尽量保留格式并可转换脚注；PDF 可标出修改字；文本文件可手动指定编码。
- **1.4.5 同步改进**：转换 DOCX 文本框内容，并按选项处理脚注/尾注；EPUB 词组转换可跨相邻行内标签保持上下文，跳过注释和脚本内容，并转换 EPUB 2 NCX 目录标签。

词典规则是一种便于校对的转换工具，出版前仍需人工审校。PDF 采用提取文字并重建页面的方法，版面可能变化；无文本层的扫描 PDF 无法转换。加密 EPUB、旧版 `.doc` 和独立 LLMCC AI 模块不在此 Mac 包内。

## 上游功能与依赖

上游仓库包含 `t2gov/` 的 OpenCC 配置与字词典、`jieba/` 的分词资源，以及 Windows、Win7 和 Linux 三套 Python 转换程序。本版基于 `transformer-linux/`：其 `text_converter.py` 处理文本和字幕，`doc_converter.py` 处理 DOCX，`epub_converter.py` 处理 EPUB，`pdf_converter.py` 处理 PDF，`main.py` 提供界面和批量工作线程。旧版 `.doc` 在 Windows 版依赖 Word COM / pywin32，无法直接移植。

运行核心使用 Python 3.13、`opencc-py` / `opencc-data` 1.4.2、PySide6 Essentials 6.11.2、jieba、python-docx、chardet 7.7.0、Beautiful Soup、lxml、pdf-oxide 和 Pillow 13.0.0。精确版本见 `requirements-mac.txt`。使用 PyInstaller 6.22.3 生成独立 `.app`。Mac 版只用 QtCore、QtGui、QtWidgets，因此不安装完整的 PySide6 Addons。

## 关键移植改动

1. 同步上游 1.4.5 规则、词典和分词资源，并一起装入 `opencc_data`，使 `.app` 离线运行。
2. `mac_opencc.py` 为结巴配置提供绝对路径，满足 `opencc-py` 1.4.2 对分词词典的查找方式。
3. 修复上游文本编码检测：有效 UTF-8 不再仅因置信度略低而改按 GB18030 读取。
4. 合入上游 DOCX 文本框和可选脚注/尾注转换，以及 EPUB 批量文本节点和 NCX 目录转换。
5. 添加粘贴转换、拖入文件、Finder 打开文件与同名结果覆盖提示；移除未随本包提供的 LLMCC 启动入口和指向非 Mac 安装包的更新入口。
6. 保留本地 PDF 字体和扫描页处理适配，打包 arm64 应用，设置名称、版本、文件关联及真实最低系统版本。应用采用 ad-hoc 签名，未公证。

## 从源码构建

在 Apple Silicon Mac 上安装 Python 3.13，进入本目录执行：

```sh
./build_mac.sh
```

脚本会创建隔离的 `.venv`、安装固定版本依赖、装入仓库词典、运行资源检查，再生成 `dist/TongguiMac.app` 和 `dist/TongguiMac-1.4.5-arm64.dmg`。如 Python 不在 `/opt/homebrew/bin/python3.13`，可设置 `PYTHON_BIN`；如已有虚拟环境，可设置 `VENV_DIR`。构建需要联网下载依赖。

可单独验证：

```sh
.venv/bin/python self_test.py
.venv/bin/python verify_formats.py
dist/TongguiMac.app/Contents/MacOS/TongguiMac --self-test
```

`verify_formats.py` 会临时生成 TXT、SRT、ASS、LRC、DOCX、EPUB 和带文本层的 PDF，用实际转换结果检查字形和格式结构。测试文件在结束时自动清理。

## 分发

本次交付为 Apple Silicon（arm64）的 `.dmg`，镜像内有 `.app`、项目许可、第三方声明和第三方许可文本，可复制到“应用程序”。**本次成品实际要求 macOS 27 或更新版本。** 应用的 `LSMinimumSystemVersion` 与 Python/OpenSSL 等运行组件均标为 27.0；需在 macOS 27.2 上完成构建验证。支持更旧系统需更换兼容依赖后重新构建。正式公开分发前，应以开发者证书签名、公证，并在目标系统版本上再次测试。

本项目改编部分保留上游 Apache-2.0 许可，见 `LICENSE`。第三方依赖各自的许可仍需在公开分发时遵守；此源码包给出了依赖版本和复现方式。

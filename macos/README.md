# 规范繁体字形转换器 for Mac 1.4.4

本目录是基于 [TerryTian-tech 的 OpenCC 项目](https://github.com/TerryTian-tech/OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards) 制作的 macOS 版本。转换规则和主要文件处理模块取自 2026-10-17 的 `main` 提交 `fe735503935bc6dce401ae5ce13b8e569dfa8e07`；该提交的程序版本为 1.4.4。上游最新发布包 1.4.3 早于这个提交。

## 用途与界面

面向编辑、出版校对、字幕和电子书制作者，以及需要按《通用规范汉字表》处理繁体字形的研究者。应用使用 Qt Widgets 桌面窗口，支持 macOS 文件拖入和 Finder 的“打开方式”，提供：

- **文件转换**：批量处理 DOCX、TXT、MD、SRT、ASS/SSA、LRC、EPUB，以及带文本层的 PDF；输出到指定文件夹，文件名前加 `convert_`。
- **文字转换**：粘贴短文本、选择转换规则、复制结果。
- **七种基本规则**：繁体转规范繁体、旧字形转新字形、前两者的保留简体变体、繁体转简体、异体字转简体、简体转规范繁体。文件转换另可选择现代或古汉语结巴分词模式。
- **格式选项**：DOCX 尽量保留格式并可转换脚注；PDF 可标出修改字；文本文件可手动指定编码。

词典规则是一种便于校对的转换工具，出版前仍需人工审校。PDF 采用提取文字并重建页面的方法，版面可能变化；无文本层的扫描 PDF 无法转换。加密 EPUB、旧版 `.doc` 和独立 LLMCC AI 模块不在此 Mac 包内。

## 上游功能与依赖

上游仓库包含 `t2gov/` 的 OpenCC 配置与字词典、`jieba/` 的分词资源，以及 Windows、Win7 和 Linux 三套 Python 转换程序。本版基于 `transformer-linux/`：其 `text_converter.py` 处理文本和字幕，`doc_converter.py` 处理 DOCX，`epub_converter.py` 处理 EPUB，`pdf_converter.py` 处理 PDF，`main.py` 提供界面和批量工作线程。旧版 `.doc` 在 Windows 版依赖 Word COM / pywin32，无法直接移植。

运行核心使用 Python 3.13、`opencc-py` / `opencc-data` 1.4.2、PySide6 Essentials 6.11.2、jieba、python-docx、chardet、Beautiful Soup、lxml、pdf-oxide 和 Pillow。精确版本见 `requirements-mac.txt`。使用 PyInstaller 6.22.3 生成独立 `.app`。Mac 版只用 QtCore、QtGui、QtWidgets，因此不安装完整的 PySide6 Addons。

## 关键移植改动

1. 将上游最新规则、词典和分词资源一起装入 `opencc_data`，使 `.app` 离线运行。
2. `mac_opencc.py` 为结巴配置提供绝对路径，满足 `opencc-py` 1.4.2 对分词词典的查找方式。
3. 修复上游文本编码检测：有效 UTF-8 不再仅因置信度略低而改按 GB18030 读取。
4. 添加粘贴转换、拖入文件、Finder 打开文件与同名结果覆盖提示；移除未随本包提供的 LLMCC 启动入口和指向非 Mac 安装包的更新入口。
5. 复用上游 PDF 的 macOS 字体搜索逻辑，打包 arm64 应用，设置名称、版本及文件关联。应用采用 ad-hoc 签名，未公证。

## 从源码构建

在 Apple Silicon Mac 上安装 Python 3.13，进入本目录执行：

```sh
./build_mac.sh
```

脚本会创建隔离的 `.venv`、安装固定版本依赖、装入仓库词典、运行资源检查，再生成 `dist/TongguiMac.app`。如 Python 不在 `/opt/homebrew/bin/python3.13`，可设置 `PYTHON_BIN`；如已有虚拟环境，可设置 `VENV_DIR`。构建需要联网下载依赖。

可单独验证：

```sh
.venv/bin/python self_test.py
.venv/bin/python verify_formats.py
dist/TongguiMac.app/Contents/MacOS/TongguiMac --self-test
```

`verify_formats.py` 会临时生成 TXT、SRT、ASS、LRC、DOCX、EPUB 和带文本层的 PDF，用实际转换结果检查字形和格式结构。测试文件在结束时自动清理。

## 分发

本次交付为 Apple Silicon（arm64）的 `.dmg`，镜像内有 `.app`，可复制到“应用程序”。**本次成品实际要求 macOS 27 或更新版本，已在 macOS 27.2 实测。** 逐个检查运行组件发现 Python、OpenSSL 等的最低目标为 27.0，PySide6/Shiboken 绑定为 15.0；原脚本及 Info.plist 的 13.0 声明不代表实际兼容性。本次未修改构建代码，支持更旧系统需更换兼容依赖后重新构建。正式公开分发前，应以开发者证书签名、公证，并在目标系统版本上再次测试。

本项目改编部分保留上游 Apache-2.0 许可，见 `LICENSE`。第三方依赖各自的许可仍需在公开分发时遵守；此源码包给出了依赖版本和复现方式。

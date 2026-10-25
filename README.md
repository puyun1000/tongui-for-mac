# TongguiMac · 规范繁体字形转换器

**macOS 移植版 1.4.5**。提供短文本与批量文件的规范繁体字形转换，可处理 DOCX、TXT、MD、SRT、ASS/SSA、LRC、EPUB 和带文本层的 PDF。采用 Qt Widgets 桌面界面，支持拖入文件与 Finder“打开方式”。DOCX 文本框转换、EPUB 跨标签词组处理和 EPUB 2 目录转换同步上游 1.4.5。转换结果仍需人工审校。

## 系统要求与安装

**本次成品要求 Apple Silicon（arm64）与 macOS 27 或更新版本，已在 macOS 27.2 验证。**

成品内组件的最低系统目标为 macOS 27.0；应用元数据也会标明这一要求。若需支持较旧 macOS，必须更换兼容依赖并重新构建、实测。

在本仓库 Releases 下载对应 DMG，打开后将 `TongguiMac.app` 复制到“应用程序”。镜像也附带第三方依赖的声明和许可文本。当前成品使用 ad-hoc 签名，未完成 Apple 公证；如系统阻止首次启动，可在确认来源后使用“隐私与安全性”中的允许打开操作。

## 从源码构建

需要 Apple Silicon Mac、Python 3.13 与 Xcode Command Line Tools，首次构建需要联网安装依赖。

```sh
cd macos
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock-macos-arm64-py313.txt
./build_mac.sh
```

默认 Python 路径为 `/opt/homebrew/bin/python3.13`，其他位置可用 `PYTHON_BIN=/path/to/python3.13 ./build_mac.sh` 指定。脚本建立 `.venv`，安装 `requirements-mac.txt` 中的固定版本依赖，装入随仓库提供的 OpenCC 和结巴词典，运行自检，生成 `dist/TongguiMac.app` 与 `dist/TongguiMac-1.4.5-macOS27-arm64.dmg`。

```sh
.venv/bin/python self_test.py
.venv/bin/python verify_formats.py
dist/TongguiMac.app/Contents/MacOS/TongguiMac --self-test
```

完整依赖锁定记录见 `macos/requirements-lock-macos-arm64-py313.txt`（验证环境）；主要依赖为 PySide6 Essentials、OpenCC、jieba、python-docx、pdf-oxide、Pillow 等。`macos/README.md` 保留移植说明。

## 上游来源、许可与致谢

上游作者/维护者为 **[TerryTian-tech](https://github.com/TerryTian-tech)**，来源仓库：

[OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards](https://github.com/TerryTian-tech/OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards)

本版基于上游 1.4.5 提交 [`aba2391859910d36f52fe0983d088216b8f10c6b`](https://github.com/TerryTian-tech/OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards/commit/aba2391859910d36f52fe0983d088216b8f10c6b)，由 `transformer-linux/` 移植至 `macos/`；保留上游 Git 历史、原平台源码、词典、[1.4.5 原始 README](doc/README-upstream.md) 与 [Apache-2.0 许可](LICENSE)。Mac 适配涉及路径、打包、编码检测和系统文件打开方式；详见 [修改说明](macos/README.md#关键移植改动)。

感谢 TerryTian-tech 提供转换程序与规则，感谢词典中署名的 Yi Jianpeng、Hu Xinmei、Duan Yatong，以及 [OpenCC / BYVoid](https://github.com/BYVoid/OpenCC)、[jieba](https://github.com/fxsjy/jieba) 和其他依赖的贡献者。各组件分别适用其自身许可，详见 [第三方声明](macos/THIRD_PARTY_NOTICES.md)。

PDF 通过提取文字并重建页面处理，版式可能变化；不支持无文本层扫描 PDF、加密 EPUB、旧版 `.doc`，本移植包不含独立 LLMCC AI 模块。

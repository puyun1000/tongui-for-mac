# TongguiMac · 规范繁体字形转换器

**macOS 移植版 1.4.8** 基于 TerryTian-tech 的 OpenCC 规范繁体项目，服务于编辑、出版校对、字幕与电子书制作，以及需要按《通用规范汉字表》处理繁体字形的用户。应用提供短文本与批量文件转换，支持 DOCX、TXT、MD、SRT、ASS/SSA、LRC、EPUB 和带文本层的 PDF；转换结果仍需人工审校。

1.4.8 在覆盖同名输出前列出文件并请求确认。同步了上游文字转换模块的整理，并加入“干的 → 乾的 / 幹的”候选。

## 下载与系统要求

需要 Apple Silicon（arm64）与 macOS 27 或更新版本；本版在 macOS 27.2 上构建验证。镜像内附有应用、第三方声明和许可文本。将应用复制到“应用程序”即可使用。

当前版本采用 ad-hoc 签名，未经 Apple 公证。首次打开如被系统拦截，可在确认下载来源后到“系统设置 → 隐私与安全性”允许打开。

前往 [GitHub Releases](https://github.com/puyun1000/tongui-for-mac/releases) 下载 `TongguiMac-1.4.8-macOS27-arm64.dmg`。

## 从源码构建

需要 Apple Silicon Mac、Python 3.13、Xcode Command Line Tools；首次构建需联网获取固定版本依赖。

```sh
cd macos
./build_mac.sh
```

默认 Python 路径为 `/opt/homebrew/bin/python3.13`；其他位置可设置 `PYTHON_BIN`。构建脚本会同步本仓库附带的 OpenCC 配置和结巴词典，运行转换与歧义检测自检，再生成 `.app` 与 DMG。

```sh
.venv/bin/python self_test.py
.venv/bin/python verify_formats.py
.venv/bin/python verify_ambiguity.py
dist/TongguiMac.app/Contents/MacOS/TongguiMac --self-test
```

## 构建验证

本机验证记录与产物 SHA-256 见 [`macos/Validation-1.4.8.md`](macos/Validation-1.4.8.md)、[`macos/SHA256SUMS-1.4.8.txt`](macos/SHA256SUMS-1.4.8.txt) 和 [`macos/BinaryDeploymentTargets.json`](macos/BinaryDeploymentTargets.json)。

## 上游来源、改动与许可

上游作者为 [TerryTian-tech](https://github.com/TerryTian-tech)，项目地址：[OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards](https://github.com/TerryTian-tech/OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards)。版本基于上游 `Transformer(1.4.8)`，并同步到 2026-11-08 的 `main` 提交 [`64130dbf0f1d73b64243c31869064e564c138fe1`](https://github.com/TerryTian-tech/OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards/commit/64130dbf0f1d73b64243c31869064e564c138fe1)。

项目保留上游源码、Git 历史、规则词典和 [Apache-2.0 许可](LICENSE)。Mac 版增加原生打包、Finder 打开方式、Unicode 文本编码保护、候选歧义标注及 macOS 文件界面；移植说明见 [`macos/README.md`](macos/README.md)，上游完整说明见 [`doc/README-upstream.md`](doc/README-upstream.md)。第三方组件分别遵循各自许可，见 [`macos/THIRD_PARTY_NOTICES.md`](macos/THIRD_PARTY_NOTICES.md)。

DOCX 尽量保留原格式并可处理脚注、尾注和文本框；EPUB 支持跨标签上下文转换。PDF 通过提取文字并重建页面，版式可能变化；无文本层的扫描 PDF 不支持。加密 EPUB、旧版 `.doc` 和独立 LLMCC AI 模块不包含在 Mac 应用中。

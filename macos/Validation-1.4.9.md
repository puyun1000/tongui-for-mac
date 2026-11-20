# 1.4.9 构建与验证记录

验证日期：2026-11-20（Asia/Shanghai）。

- 上游正式版为 Transformer(1.4.9)，合入 main 最新提交 ba9901d757db41f30c94aafc9db424fb05b67d8b。保留上游 Git 历史、源码与许可。
- 新增多层文件夹递归转换，输出保留原目录结构，按相对路径检查重名和已存在的输出；跳过输入目录中嵌套的输出目录。同步删除“垔”的转换规则。
- 本次同时发布此前 Mac 侧边栏界面改版与 DOCX 页眉页脚修复。七种转换模式、候选字、编码、分词、PDF 高亮、格式保留及脚注尾注选项继续保留。
- 构建环境：Apple Silicon、macOS 27.3（26C5035r）、Python 3.13.18；在本地临时目录创建干净环境，使用 requirements-lock-macos-arm64-py313.txt 的固定依赖，通过 PyInstaller 构建。
- self_test.py 通过：OpenCC 内置及两种结巴配置可用，“垔”保持原字；无页眉页脚的 DOCX 不会生成多余部件。
- verify_ambiguity.py 通过：七种转换模式与 OpenCC 输出一致，共验证五处候选跨度。
- verify_formats.py 通过：TXT、SRT、ASS、LRC、DOCX、EPUB、带文字层 PDF，共七项生成样本的格式回归。
- verify_batch.py 通过：三份中文文件名文档覆盖顶层与多层目录、跨目录同名、嵌套输出排除；相对路径冲突清单、默认取消、确认覆盖；硬链接原件保护、符号链接输出子目录拦截、多选文件平铺重名拦截，以及直接工作线程的递归入口。测试使用独立设置文件和临时样本。
- hdiutil verify 通过；只读挂载最终 DMG 后，核对 CFBundleShortVersionString / CFBundleVersion 为 1.4.9，LSMinimumSystemVersion 为 27.0；codesign --verify --deep --strict、包内 --self-test 及离屏 GUI 启动检查通过。
- 镜像中 219 个 Mach-O 路径全部为 arm64；逐个检查最低部署版本，最高为 27.0。完整明细见 BinaryDeploymentTargets.json。
- 自动界面测试采用 Qt 离屏运行，不等于人工交互验收。此次升级未替换已安装的应用，未转换用户原始文档。
- 分发要求：Apple Silicon（arm64）、macOS 27+。应用使用 ad-hoc 签名，未经过 Apple 公证。旧式 DOC、独立 AI 模块、无文字层扫描 PDF OCR 不包含在 Mac 应用中；PDF 重建可能改变版式。

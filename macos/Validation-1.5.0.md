# 1.5.0 构建与验证记录

验证日期：2026-11-24（Asia/Shanghai）。

- 合入上游 Transformer(1.5.0) 与 main 提交 dcd55a8；完整 SHA 见仓库 README。保留上游源码、Git 历史、贡献者名单和许可，并更新上游说明与依赖清单快照。
- Mac 文件转换页面新增文件夹批量选项：保留原文件名、仅转换指定类型（DOCX、TXT、MD、SRT、ASS/SSA、LRC、EPUB、PDF）。类型选择和命名设置会保存；选择文件对话框增加格式分类。
- 保留 Mac 侧边栏、递归目录结构、嵌套输出目录排除、Unicode 编码处理、候选字、两种结巴模式、PDF 高亮与原件保护。上游 DOCX 页眉页脚修复与此前 Mac 修复一致，本次合并后继续保留。
- 覆盖预检与工作线程采用相同命名规则；保留原文件名仅对文件夹模式生效，输出目录与原目录相同时自动改用 convert_ 前缀。识别符号链接目录别名，并保留硬链接原件保护。
- 构建环境：Apple Silicon、macOS 27.3（26C5047e）、Python 3.13.18。从干净 Git archive 创建临时构建目录，在本地临时虚拟环境安装锁定依赖，使用 PyInstaller 构建。上游 certifi 清单更新已同步；Mac 不使用上游 requests 更新器，运行依赖维持现有锁定版本。
- self_test.py 通过：OpenCC 内置规则、两种结巴配置及 DOCX 无多余页眉页脚部件。verify_ambiguity.py 通过：七种转换模式与 OpenCC 一致，验证五处候选跨度。
- verify_formats.py 通过：TXT、SRT、ASS、LRC、DOCX、EPUB、带文字层 PDF 在默认前缀与保留原名两种模式下分别验证命名和内容，共 14 项。
- verify_batch.py 通过：递归目录、跨目录同名、嵌套输出排除、相对路径覆盖清单、默认取消与确认覆盖、原件硬链接保护、输出子目录符号链接拦截、多选平铺重名拦截；1.5.0 指定类型与大写扩展名、原名输出及覆盖、空类型拒绝、设置保存与恢复、同目录前缀回退、目录别名回退、单文件不受文件夹选项影响，以及工作线程直接入口的筛选和命名。
- Qt 离屏检查默认浅色界面和 760×700 深色小窗口：新选项分两行排列，内容可滚动，底部进度和操作保持可见。自动检查不等于人工交互验收。
- hdiutil verify 通过；只读挂载最终 DMG 后确认版本为 1.5.0、最低 macOS 27.0；codesign --verify --deep --strict、包内 --self-test 和离屏 GUI 启动检查通过。
- 镜像中 219 个 Mach-O 路径全部为 arm64，逐个检查最低部署版本，最高为 27.0；完整明细见 BinaryDeploymentTargets.json。
- 分发要求：Apple Silicon、macOS 27+，ad-hoc 签名、未经 Apple 公证。旧式 DOC、独立 AI 模块和扫描 PDF OCR 不包含在 Mac 版中。未替换已安装应用，未转换用户原始文档。

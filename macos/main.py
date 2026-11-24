import os
import sys
from unicodedata import normalize

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTextEdit, QFileDialog, QLabel, QProgressBar,
                             QMessageBox, QGroupBox, QComboBox, QCheckBox, QLineEdit,
                             QMenu, QFrame, QScrollArea, QStackedWidget, QButtonGroup, QSizePolicy, QGridLayout)
from PySide6.QtCore import Qt, QThread, Signal, QSettings, QEvent
from PySide6.QtGui import (QIcon, QColor, QPalette, QKeySequence, QAction, QShortcut, QFont)
from mac_opencc import OpenCC
from text_tab import AmbiguityOutputEdit, TextConversionWorker

from constants import VERSION

SUPPORTED_EXTENSIONS = {".docx", ".txt", ".md", ".srt", ".ass", ".ssa", ".lrc", ".epub", ".pdf"}

CONVERSION_TYPES = {
    "繁体转规范繁体": "t2gov",
    "繁体旧字形转新字形，但保留异体字不转换": "t2new",
    "繁体转规范繁体，但保留文档内原有简体字": "t2gov_keep_simp",
    "繁体旧字形转新字形，但保留文档内原有简体字和异体字": "t2new_keep_simp",
    "繁体转简体": "t2s",
    "只将异体字转为简体字": "v2s",
    "简体转规范繁体": "s2t",
}
from text_converter import convert_txt_file, convert_srt_file, convert_ass_file, convert_lrc_file
from doc_converter import convert_docx_file
from epub_converter import convert_epub_file
from pdf_converter import convert_pdf_file
import jieba


def collect_supported_files(input_path, exclude_path=None, extensions=None):
    """Return sorted relative paths, skipping nested output directories."""
    exclude = os.path.realpath(exclude_path) if exclude_path else None
    allowed = SUPPORTED_EXTENSIONS if extensions is None else set(extensions)
    result = []
    for root, dirs, files in os.walk(input_path):
        dirs[:] = sorted(
            (d for d in dirs
             if not exclude or os.path.realpath(os.path.join(root, d)) != exclude),
            key=str.lower)
        for name in sorted(files, key=str.lower):
            path = os.path.join(root, name)
            if os.path.splitext(name)[1].lower() in allowed and os.path.isfile(path):
                result.append(os.path.relpath(path, input_path))
    return result



def output_filename(file_path, output_folder, keep_original_name=False):
    """Share naming rules between overwrite checks and actual conversion."""
    same_directory = os.path.realpath(os.path.dirname(file_path)) == os.path.realpath(output_folder)
    prefix = "" if keep_original_name and not same_directory else "convert_"
    return prefix + os.path.basename(file_path)


class ConversionWorker(QThread):
    """
    转换工作线程，避免UI阻塞
    """
    progress_updated = Signal(int, str)  # 进度信号
    conversion_finished = Signal(bool, str, int, int)  # 完成信号 (success, message, success_count, total_files)
    log_message = Signal(str)  # 日志消息信号

    def __init__(self, input_path, output_folder, conversion_type='t2gov', preserve_format=True,
                 convert_footnotes=True, force_encoding=None, segment_mode=None, input_paths=None,
                 highlight_pdf=False, output_folders=None,
                 folder_extensions=None, keep_original_name=False):
        super().__init__()
        self.input_path = input_path
        self.output_folder = output_folder
        self.conversion_type = conversion_type
        self.preserve_format = preserve_format
        self.convert_footnotes = convert_footnotes
        self.force_encoding = force_encoding
        self.segment_mode = segment_mode
        self.input_paths = input_paths
        self.output_folders = output_folders
        self.folder_extensions = folder_extensions
        self.keep_original_name = keep_original_name
        self.highlight_pdf = highlight_pdf
        self._is_cancelled = False

        # 根据分词模式自动调整OpenCC配置名称
        if self.segment_mode == 'jieba_modern':
            self.conversion_type += '_jieba'
        elif self.segment_mode == 'jieba_ancient':
            self.conversion_type += '_jieba_traditional'

    def run(self):
        try:
            self._success_count = 0
            self._total_files = 0
            success = self.process_files()

            # 检查是否已取消
            if self._is_cancelled:
                self.conversion_finished.emit(False, "转换已被用户取消", 0, 0)
                return

            if self._total_files > 0:
                # 多文件模式
                if self._success_count == self._total_files:
                    self.conversion_finished.emit(True, "转换成功完成", self._success_count, self._total_files)
                elif self._success_count > 0:
                    self.conversion_finished.emit(False, "部分文件转换失败", self._success_count, self._total_files)
                else:
                    self.conversion_finished.emit(False, "转换过程中出现错误", 0, self._total_files)
            else:
                # 单文件模式
                if success:
                    self.conversion_finished.emit(True, "转换成功完成", 1, 1)
                else:
                    self.conversion_finished.emit(False, "转换过程中出现错误", 0, 1)
        except Exception as e:
            self.conversion_finished.emit(False, f"转换失败: {str(e)}", 0, 0)

    def cancel(self):
        """取消转换"""
        self._is_cancelled = True
        self.log_message.emit("用户取消转换")

    def process_files(self):
        """处理文件的主要逻辑"""
        # 检查是否已取消
        if self._is_cancelled:
            return False

        self.progress_updated.emit(0, "开始处理...")

        # 检查是否已取消
        if self._is_cancelled:
            return False

        # 处理文件列表（多选文件模式）
        if self.input_paths:
            total_files = len(self.input_paths)
            self.log_message.emit(f"找到 {total_files} 个文件待处理")
            success_count = 0

            for i, file_path in enumerate(self.input_paths, 1):
                if self._is_cancelled:
                    return False

                progress = int((i / total_files) * 100)
                self.progress_updated.emit(progress, f"处理文件 {i}/{total_files}: {os.path.basename(file_path)}")

                output_folder = self.output_folders[i - 1] if self.output_folders else self.output_folder
                keep_name = output_filename(file_path, output_folder, self.keep_original_name) == os.path.basename(file_path)
                file_ext = os.path.splitext(file_path)[1].lower()

                if file_ext == '.docx':
                    try:
                        result = convert_docx_file(
                            file_path, output_folder, self.conversion_type,
                            self.preserve_format,
                            self.convert_footnotes,
                            lambda msg: self.log_message.emit(msg),
                            lambda: self._is_cancelled,
                            keep_original_name=keep_name
                        )
                        if result:
                            success_count += 1
                    except Exception as e:
                        self.log_message.emit(f"处理 {os.path.basename(file_path)} 时出错: {str(e)}")

                elif file_ext == '.txt':
                    if convert_txt_file(
                        file_path, output_folder, self.conversion_type,
                        lambda msg: self.log_message.emit(msg),
                        lambda: self._is_cancelled,
                        self.force_encoding,
                        self.segment_mode,
                        keep_original_name=keep_name
                    ):
                        success_count += 1

                elif file_ext == '.md':
                    if convert_txt_file(
                        file_path, output_folder, self.conversion_type,
                        lambda msg: self.log_message.emit(msg),
                        lambda: self._is_cancelled,
                        keep_original_name=keep_name
                    ):
                        success_count += 1

                elif file_ext == '.srt':
                    if convert_srt_file(
                        file_path, output_folder, self.conversion_type,
                        lambda msg: self.log_message.emit(msg),
                        lambda: self._is_cancelled,
                        keep_original_name=keep_name
                    ):
                        success_count += 1

                elif file_ext in ['.ass', '.ssa']:
                    if convert_ass_file(
                        file_path, output_folder, self.conversion_type,
                        lambda msg: self.log_message.emit(msg),
                        lambda: self._is_cancelled,
                        keep_original_name=keep_name
                    ):
                        success_count += 1

                elif file_ext == '.lrc':
                    if convert_lrc_file(
                        file_path, output_folder, self.conversion_type,
                        lambda msg: self.log_message.emit(msg),
                        lambda: self._is_cancelled,
                        keep_original_name=keep_name
                    ):
                        success_count += 1

                elif file_ext == '.epub':
                    try:
                        if convert_epub_file(
                            file_path, output_folder, self.conversion_type,
                            lambda msg: self.log_message.emit(msg),
                            lambda: self._is_cancelled,
                            keep_original_name=keep_name
                        ):
                            success_count += 1
                    except Exception as e:
                        self.log_message.emit(f"处理 {os.path.basename(file_path)} 时出错: {str(e)}")

                elif file_ext == '.pdf':
                    try:
                        if convert_pdf_file(
                            file_path, output_folder, self.conversion_type,
                            lambda msg: self.log_message.emit(msg),
                            lambda: self._is_cancelled,
                            self.highlight_pdf,
                            keep_original_name=keep_name
                        ):
                            success_count += 1
                    except Exception as e:
                        self.log_message.emit(f"处理 {os.path.basename(file_path)} 时出错: {str(e)}")

                else:
                    self.log_message.emit(f"跳过不支持的文件: {os.path.basename(file_path)}")

            self.log_message.emit(f"处理完成！成功转换 {success_count}/{total_files} 个文件")
            self.progress_updated.emit(100, "转换完成!")
            self._success_count = success_count
            self._total_files = total_files
            return success_count == total_files

        # 处理单个文件
        if os.path.isfile(self.input_path):
            keep_name = False
            file_ext = os.path.splitext(self.input_path)[1].lower()

            # 检查是否已取消
            if self._is_cancelled:
                return False

            if file_ext == '.docx':
                result = convert_docx_file(
                    self.input_path, self.output_folder, self.conversion_type,
                    self.preserve_format,
                    self.convert_footnotes,
                    lambda msg: self.log_message.emit(msg),
                    lambda: self._is_cancelled,
                    keep_original_name=keep_name
                )
                if result:
                    self.progress_updated.emit(100, "转换完成!")
                    return True
                else:
                    return False
            elif file_ext == '.txt':
                result = convert_txt_file(
                    self.input_path, self.output_folder, self.conversion_type,
                    lambda msg: self.log_message.emit(msg),
                    lambda: self._is_cancelled,
                    self.force_encoding,
                    self.segment_mode,
                    keep_original_name=keep_name
                )
                if result:
                    self.progress_updated.emit(100, "转换完成!")
                    return True
                else:
                    return False
            elif file_ext == '.md':
                result = convert_txt_file(
                    self.input_path, self.output_folder, self.conversion_type,
                    lambda msg: self.log_message.emit(msg),
                    lambda: self._is_cancelled,
                    keep_original_name=keep_name
                )
                if result:
                    self.progress_updated.emit(100, "转换完成!")
                    return True
                else:
                    return False
            elif file_ext == '.srt':
                result = convert_srt_file(
                    self.input_path, self.output_folder, self.conversion_type,
                    lambda msg: self.log_message.emit(msg),
                    lambda: self._is_cancelled,
                    keep_original_name=keep_name
                )
                if result:
                    self.progress_updated.emit(100, "转换完成!")
                    return True
                else:
                    return False
            elif file_ext in ['.ass', '.ssa']:
                result = convert_ass_file(
                    self.input_path, self.output_folder, self.conversion_type,
                    lambda msg: self.log_message.emit(msg),
                    lambda: self._is_cancelled,
                    keep_original_name=keep_name
                )
                if result:
                    self.progress_updated.emit(100, "转换完成!")
                    return True
                else:
                    return False
            elif file_ext == '.lrc':
                result = convert_lrc_file(
                    self.input_path, self.output_folder, self.conversion_type,
                    lambda msg: self.log_message.emit(msg),
                    lambda: self._is_cancelled,
                    keep_original_name=keep_name
                )
                if result:
                    self.progress_updated.emit(100, "转换完成!")
                    return True
                else:
                    return False
            elif file_ext == '.epub':
                result = convert_epub_file(
                    self.input_path, self.output_folder, self.conversion_type,
                    lambda msg: self.log_message.emit(msg),
                    lambda: self._is_cancelled,
                    keep_original_name=keep_name
                )
                if result:
                    self.progress_updated.emit(100, "转换完成!")
                    return True
                else:
                    return False
            elif file_ext == '.pdf':
                try:
                    result = convert_pdf_file(
                        self.input_path, self.output_folder, self.conversion_type,
                        lambda msg: self.log_message.emit(msg),
                        lambda: self._is_cancelled,
                        self.highlight_pdf,
                        keep_original_name=keep_name
                    )
                except Exception as e:
                    self.log_message.emit(f"处理 {os.path.basename(self.input_path)} 时出错: {str(e)}")
                    result = False
                if result:
                    self.progress_updated.emit(100, "转换完成!")
                    return True
                else:
                    return False
            else:
                self.log_message.emit("错误：不支持的文件格式，仅支持docx、txt、md、srt、ass、ssa、lrc、epub、pdf文件")
                return False

        # 处理文件夹
        elif os.path.isdir(self.input_path):
            supported_files = collect_supported_files(self.input_path, self.output_folder, self.folder_extensions)
            if self._is_cancelled:
                return False

            if not supported_files:
                self.log_message.emit("在指定文件夹（含子文件夹）中未找到支持的docx、txt、md、srt、ass、ssa、lrc、epub、pdf文件")
                return False

            self.log_message.emit(f"找到 {len(supported_files)} 个文件待处理")

            success_count = 0
            total_files = len(supported_files)

            for i, filename in enumerate(supported_files, 1):
                # 检查是否已取消
                if self._is_cancelled:
                    return False

                progress = int((i / total_files) * 100)
                self.progress_updated.emit(progress, f"处理文件 {i}/{total_files}: {filename}")

                file_path = os.path.join(self.input_path, filename)
                output_folder = os.path.join(self.output_folder, os.path.dirname(filename))
                keep_name = output_filename(file_path, output_folder, self.keep_original_name) == os.path.basename(file_path)
                file_ext = os.path.splitext(filename)[1].lower()

                if file_ext == '.docx':
                    # 对于docx文件，使用转换器类
                    try:
                        result = convert_docx_file(
                            file_path, output_folder, self.conversion_type,
                            self.preserve_format,
                            self.convert_footnotes,
                            lambda msg: self.log_message.emit(msg),
                            lambda: self._is_cancelled,
                            keep_original_name=keep_name
                        )
                        if result:
                            success_count += 1

                    except Exception as e:
                        self.log_message.emit(f"处理 {filename} 时出错: {str(e)}")

                elif file_ext == '.txt':
                    if convert_txt_file(
                        file_path, output_folder, self.conversion_type,
                        lambda msg: self.log_message.emit(msg),
                        lambda: self._is_cancelled,
                        self.force_encoding,
                        self.segment_mode,
                        keep_original_name=keep_name
                    ):
                        success_count += 1

                elif file_ext == '.md':
                    if convert_txt_file(
                        file_path, output_folder, self.conversion_type,
                        lambda msg: self.log_message.emit(msg),
                        lambda: self._is_cancelled,
                        keep_original_name=keep_name
                    ):
                        success_count += 1

                elif file_ext == '.srt':
                    if convert_srt_file(
                        file_path, output_folder, self.conversion_type,
                        lambda msg: self.log_message.emit(msg),
                        lambda: self._is_cancelled,
                        keep_original_name=keep_name
                    ):
                        success_count += 1

                elif file_ext in ['.ass', '.ssa']:
                    if convert_ass_file(
                        file_path, output_folder, self.conversion_type,
                        lambda msg: self.log_message.emit(msg),
                        lambda: self._is_cancelled,
                        keep_original_name=keep_name
                    ):
                        success_count += 1

                elif file_ext == '.lrc':
                    if convert_lrc_file(
                        file_path, output_folder, self.conversion_type,
                        lambda msg: self.log_message.emit(msg),
                        lambda: self._is_cancelled,
                        keep_original_name=keep_name
                    ):
                        success_count += 1

                elif file_ext == '.epub':
                    try:
                        if convert_epub_file(
                            file_path, output_folder, self.conversion_type,
                            lambda msg: self.log_message.emit(msg),
                            lambda: self._is_cancelled,
                            keep_original_name=keep_name
                        ):
                            success_count += 1
                    except Exception as e:
                        self.log_message.emit(f"处理 {filename} 时出错: {str(e)}")

                elif file_ext == '.pdf':
                    try:
                        if convert_pdf_file(
                            file_path, output_folder, self.conversion_type,
                            lambda msg: self.log_message.emit(msg),
                            lambda: self._is_cancelled,
                            self.highlight_pdf,
                            keep_original_name=keep_name
                        ):
                            success_count += 1
                    except Exception as e:
                        self.log_message.emit(f"处理 {filename} 时出错: {str(e)}")

            self.log_message.emit(f"处理完成！成功转换 {success_count}/{total_files} 个文件")
            self.progress_updated.emit(100, "转换完成!")
            self._success_count = success_count
            self._total_files = total_files
            return success_count == total_files

        else:
            self.log_message.emit("错误：输入的路径既不是有效的文件也不是文件夹")
            return False


class ModernUI(QMainWindow):
    def __init__(self):
        super().__init__()

        # 初始化设置存储
        self.settings = QSettings("TerryTian-tech", "TongguiMac")

        # 从设置中加载主题，如果不存在则使用默认的暗色主题
        saved_theme = self.settings.value("theme", "light")
        self.current_theme = saved_theme

        # 存储多选文件列表
        self.selected_files = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("规范繁体字形转换器")
        self.resize(1000, 730)
        self.setMinimumSize(760, 570)
        self.setAcceptDrops(True)
        self.setWindowIcon(QIcon(self.get_logo_path()))
        self.apply_theme(self.current_theme)

        root = QWidget()
        root.setObjectName("workspace")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(164)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(14, 24, 14, 16)
        nav.setSpacing(7)
        brand = QLabel("通规 · Mac")
        brand.setObjectName("brand")
        nav.addWidget(brand)
        nav.addSpacing(18)
        layout.addWidget(sidebar)

        self.pages = QStackedWidget()
        layout.addWidget(self.pages, 1)
        self.navigation = QButtonGroup(self)
        for index, (name, page) in enumerate((
            ("文件转换", self.create_conversion_tab()),
            ("文字转换", self.create_text_tab()),
            ("设置", self.scroll_page(self.create_settings_tab())),
            ("关于", self.scroll_page(self.create_about_tab())),
        )):
            self.pages.addWidget(page)
            button = QPushButton(name)
            button.setObjectName("navigation")
            button.setCheckable(True)
            self.navigation.addButton(button, index)
            if index == 2:
                nav.addStretch()
            nav.addWidget(button)
        self.navigation.idClicked.connect(self.pages.setCurrentIndex)
        self.navigation.button(0).setChecked(True)
        settings_action = QAction("设置…", self)
        settings_action.setMenuRole(QAction.MenuRole.PreferencesRole)
        settings_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Preferences))
        settings_action.triggered.connect(lambda: self.navigation.button(2).click())
        self.menuBar().addMenu("应用").addAction(settings_action)
        self.statusBar().showMessage("就绪")

    @staticmethod
    def scroll_page(content):
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        return scroll

    @staticmethod
    def page_heading(layout, title, description):
        heading = QLabel(title)
        heading.setObjectName("pageHeading")
        layout.addWidget(heading)
        detail = QLabel(description)
        detail.setObjectName("muted")
        detail.setWordWrap(True)
        layout.addWidget(detail)

    def create_text_tab(self):
        """创建文字转换选项卡：顶部选转换类型与候选字显示，左侧输入、右侧输出"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 18)
        self.page_heading(layout, "文字转换", "粘贴文字，即时校对并复制转换结果。")

        # 顶部选项：转换类型 + 是否显示候选字 + 转换按钮
        options_group = QGroupBox("转换选项")
        options_layout = QHBoxLayout(options_group)
        options_layout.setSpacing(15)
        options_layout.setContentsMargins(15, 12, 15, 12)

        options_layout.addWidget(QLabel("转换类型:"))
        self.text_type_combo = QComboBox()
        for display_name in CONVERSION_TYPES:
            self.text_type_combo.addItem(display_name)
        # 恢复上次选择的转换类型（先设索引再连信号，避免初始化时误触发）
        saved_index = self.settings.value("text_conversion_index", 0, type=int)
        if 0 <= saved_index < self.text_type_combo.count():
            self.text_type_combo.setCurrentIndex(saved_index)
        self.text_type_combo.currentIndexChanged.connect(self.on_text_type_changed)
        options_layout.addWidget(self.text_type_combo, 1)

        self.show_candidates_cb = QCheckBox("显示候选字")
        self.show_candidates_cb.setChecked(True)
        self.show_candidates_cb.setToolTip(
            "转换结果中的一对多歧义词以红色波浪线标注，\n点击波浪线可查看该词的全部候选转换值。")
        self.show_candidates_cb.stateChanged.connect(self.on_show_candidates_changed)
        options_layout.addWidget(self.show_candidates_cb)

        self.text_convert_btn = QPushButton("转换")
        self.text_convert_btn.setObjectName("startButton")
        self.text_convert_btn.clicked.connect(self.on_text_convert)
        options_layout.addWidget(self.text_convert_btn)

        layout.addWidget(options_group)

        # 中部：左输入、右输出（两侧均为纯文本、自动换行、同一字号，保证显示对齐）
        panel_font = QFont(self.font())
        panel_font.setPointSize(14)

        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(12)

        input_group = QGroupBox("输入文字")
        input_layout = QVBoxLayout(input_group)
        input_layout.setContentsMargins(12, 19, 12, 12)
        self.text_input_edit = QTextEdit()
        self.text_input_edit.setAcceptRichText(False)  # 粘贴/拖入一律按纯文本处理
        self.text_input_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        self.text_input_edit.setFont(panel_font)
        self.text_input_edit.setPlaceholderText("粘贴或输入文字，按 ⌘↩ 转换")
        self.text_input_edit.textChanged.connect(self.on_text_input_changed)
        for seq in (QKeySequence("Ctrl+Return"), QKeySequence("Ctrl+Enter")):
            shortcut = QShortcut(seq, self.text_input_edit)
            shortcut.activated.connect(self.on_text_convert)
        input_layout.addWidget(self.text_input_edit)
        panels_layout.addWidget(input_group, 1)

        output_group = QGroupBox("转换结果")
        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(12, 19, 12, 12)
        self.text_output_edit = AmbiguityOutputEdit()
        self.text_output_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        self.text_output_edit.setFont(panel_font)
        self.text_output_edit.setPlaceholderText("转换结果显示在这里")
        self.text_output_edit.ambiguity_clicked.connect(self.show_candidate_menu)
        output_layout.addWidget(self.text_output_edit)
        panels_layout.addWidget(output_group, 1)

        layout.addLayout(panels_layout, 1)

        # 底部：操作按钮与状态信息
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        self.text_copy_btn = QPushButton("复制结果")
        self.text_copy_btn.setObjectName("browseButton")
        self.text_copy_btn.clicked.connect(self.copy_text_result)
        bottom_layout.addWidget(self.text_copy_btn)

        self.text_clear_btn = QPushButton("清空")
        self.text_clear_btn.setObjectName("browseButton")
        self.text_clear_btn.clicked.connect(self.clear_text_tab)
        bottom_layout.addWidget(self.text_clear_btn)

        bottom_layout.addStretch()

        self.text_status_label = QLabel("输入文字后点击“转换”；分词模式与“设置”页一致。")
        self.text_status_label.setWordWrap(True)
        bottom_layout.addWidget(self.text_status_label, 1)

        layout.addLayout(bottom_layout)

        # 文字转换运行期状态
        self.text_worker = None
        self._text_result = None  # 最近一次转换结果（切换“显示候选字”时用于重绘）

        return tab

    def on_text_type_changed(self, index):
        """切换转换类型：保存选择并作废当前结果"""
        self.settings.setValue("text_conversion_index", index)
        self._text_result = None
        self.text_output_edit.clear_result()
        self.set_text_status("已切换转换类型，请重新转换")

    def on_text_input_changed(self):
        """输入变化后作废当前结果"""
        if self._text_result is not None:
            self._text_result = None
            self.text_output_edit.clear_result()
            self.set_text_status("输入已修改，请重新转换")

    def on_show_candidates_changed(self):
        """切换“显示候选字”后按最近一次转换结果重绘波浪线"""
        self.text_output_edit.set_mark_ambiguities(self.show_candidates_cb.isChecked())

    def on_text_convert(self):
        """执行文字转换（后台线程）"""
        text = self.text_input_edit.toPlainText()
        if not text.strip():
            self.set_text_status("请先输入要转换的文字", error=True)
            return

        config = CONVERSION_TYPES[self.text_type_combo.currentText()]
        # 分词模式与“设置”页保持一致（同文件转换）
        if self.jieba_modern_cb.isChecked():
            config += '_jieba'
        elif self.jieba_ancient_cb.isChecked():
            config += '_jieba_traditional'

        # 如果已有转换线程在运行，先取消并等待其结束
        if self.text_worker is not None and self.text_worker.isRunning():
            self.text_worker.cancel()
            self.text_worker.wait()

        self.text_convert_btn.setEnabled(False)
        self.set_text_status("正在转换…")
        self.text_worker = TextConversionWorker(text, config)
        self.text_worker.conversion_done.connect(self.on_text_convert_done)
        self.text_worker.conversion_failed.connect(self.on_text_convert_failed)
        self.text_worker.start()

    def on_text_convert_done(self, result):
        """文字转换完成：显示结果并标注歧义"""
        self.text_convert_btn.setEnabled(True)
        self._text_result = result
        self.text_output_edit.display_result(
            result["output"], result["spans"], self.show_candidates_cb.isChecked())
        notice = result.get("notice")
        if notice:
            self.set_text_status(notice, error=True)
            return
        if result["spans"]:
            message = "转换完成：%d 处一对多歧义（点击红色波浪线查看候选）" % len(result["spans"])
            if result.get("skipped"):
                message += "；另有 %d 处因与实际转换无法对齐未标注" % result["skipped"]
        else:
            message = "转换完成，未发现一对多歧义"
        self.set_text_status(message)

    def on_text_convert_failed(self, message):
        """文字转换失败"""
        self.text_convert_btn.setEnabled(True)
        self.set_text_status(message, error=True)

    def set_text_status(self, message, error=False):
        """更新文字转换页底部的状态信息"""
        self.text_status_label.setText(message)
        self.text_status_label.setStyleSheet("color: #e74c3c;" if error else "")

    def show_candidate_menu(self, span_idx, global_pos):
        """在歧义跨度处弹出候选字菜单，选中候选后原地替换"""
        span = self.text_output_edit.spans()[span_idx]
        menu = QMenu(self)
        header = QAction("原文：%s" % span["source"], menu)
        header.setEnabled(False)
        menu.addAction(header)
        current = self.text_output_edit.span_text(span_idx)
        for candidate in span["candidates"]:
            action = menu.addAction(candidate)
            action.setCheckable(True)
            action.setChecked(candidate == current)
            action.triggered.connect(
                lambda checked, c=candidate, i=span_idx:
                    self.text_output_edit.apply_candidate(i, c))
        menu.exec(global_pos)

    def copy_text_result(self):
        """复制转换结果（含手动修正）到剪贴板"""
        text = self.text_output_edit.toPlainText()
        if not text:
            self.set_text_status("暂无转换结果可复制", error=True)
            return
        QApplication.clipboard().setText(text)
        self.set_text_status("已复制转换结果")

    def clear_text_tab(self):
        """清空输入与结果"""
        self.text_input_edit.clear()
        self.text_output_edit.clear_result()
        self._text_result = None
        self.set_text_status("已清空")

    def choose_paths(self, paths):
        paths = [os.path.abspath(path) for path in paths if os.path.exists(path)]
        if not paths:
            return
        if len(paths) == 1 and os.path.isdir(paths[0]):
            self.selected_files = []
            self.input_edit.setText(paths[0])
            default_output = os.path.dirname(paths[0])
        else:
            self.selected_files = [path for path in paths if os.path.isfile(path)]
            if not self.selected_files:
                return
            self.input_edit.setText(self.selected_files[0] if len(self.selected_files) == 1
                                    else f"已选择 {len(self.selected_files)} 个文件")
            default_output = os.path.dirname(self.selected_files[0])
        names = [os.path.basename(path) for path in (self.selected_files or paths)]
        summary = "、".join(names[:3])
        if len(names) > 3:
            summary += f" 等 {len(names)} 个文件"
        self.source_summary.setText(summary)
        self.source_summary.setToolTip("\n".join(names))
        self.source_summary.show()
        if not self.output_edit.text():
            self.output_edit.setText(default_output)
        if hasattr(self, "navigation"):
            self.navigation.button(0).click()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.choose_paths([url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()])
        event.acceptProposedAction()

    def get_logo_path(self):
        """
        获取logo文件的路径
        程序会按以下顺序查找logo文件：
        1. 与程序同目录下的"logo.ico"
        2. 与程序同目录下的"logo.png"
        3. 程序内部资源（如果没有外部文件，则返回空）
        """
        # 尝试查找logo.ico文件
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.ico")
        if os.path.exists(logo_path):
            return logo_path

        # 尝试查找logo.png文件
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
        if os.path.exists(logo_path):
            return logo_path

        # 如果没有找到外部文件，可以创建一个临时的logo
        # 这里我们创建一个简单的程序内建图标作为fallback
        return ""

    def create_settings_tab(self):
        """创建设置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(16)
        self.page_heading(layout, "设置", "调整外观和转换所用的默认选项。")

        # 主题设置区域
        theme_group = QGroupBox("主题设置")
        theme_layout = QVBoxLayout(theme_group)
        theme_layout.setSpacing(15)
        theme_layout.setContentsMargins(15, 20, 15, 15)

        # 主题选择说明
        theme_label = QLabel("选择您喜欢的界面主题:")
        theme_layout.addWidget(theme_label)

        # 主题选择按钮
        theme_button_layout = QHBoxLayout()

        # 创建复选框（互斥：勾选一个自动取消另一个）
        self.dark_theme_cb = QCheckBox("暗色主题")
        self.light_theme_cb = QCheckBox("浅色主题")

        # 根据保存的主题设置默认选中
        if self.current_theme == "dark":
            self.dark_theme_cb.setChecked(True)
        else:
            self.light_theme_cb.setChecked(True)

        # 将复选框添加到布局
        theme_button_layout.addWidget(self.dark_theme_cb)
        theme_button_layout.addWidget(self.light_theme_cb)
        theme_button_layout.addStretch()

        theme_layout.addLayout(theme_button_layout)

        # 连接信号：勾选一个时自动取消另一个（互斥行为）
        self.dark_theme_cb.stateChanged.connect(lambda state: self.on_theme_changed("dark", state))
        self.light_theme_cb.stateChanged.connect(lambda state: self.on_theme_changed("light", state))

        layout.addWidget(theme_group)

        # 文件编码检测设置区域
        encoding_group = QGroupBox("编码检测设置")
        encoding_group_layout = QVBoxLayout(encoding_group)
        encoding_group_layout.setSpacing(15)
        encoding_group_layout.setContentsMargins(15, 20, 15, 15)

        # 编码检测说明
        encoding_desc = QLabel(
            "指定读取TXT等文本文件时使用的编码，默认为自动检测。\n"
            "如果自动检测识别错误（例如Big5编码被误识别为GB18030），\n"
            "可在此手动强制指定编码。"
        )
        encoding_desc.setWordWrap(True)
        encoding_group_layout.addWidget(encoding_desc)

        # 编码选择
        encoding_select_layout = QHBoxLayout()
        encoding_select_layout.setSpacing(10)
        encoding_select_layout.addWidget(QLabel("强制编码:"))

        self.encoding_combo = QComboBox()
        self.encoding_combo.addItem("自动检测", None)
        self.encoding_combo.addItem("强制使用 GB18030", "gb18030")
        self.encoding_combo.addItem("强制使用 GBK", "gbk")
        self.encoding_combo.addItem("强制使用 GB2312", "gb2312")
        self.encoding_combo.addItem("强制使用 UTF-8", "utf-8")
        self.encoding_combo.addItem("强制使用 Big5", "cp950")
        self.encoding_combo.addItem("强制使用 Big5-HKSCS", "big5-hkscs")
        self.encoding_combo.setToolTip(
            "对于TXT等文本文件，指定读取时使用的编码。\n"
            "默认为自动检测；如果自动检测识别错误，可手动强制指定。"
        )

        # 从设置中恢复编码选择
        saved_encoding_index = self.settings.value("encoding_index", 0, type=int)
        if 0 <= saved_encoding_index < self.encoding_combo.count():
            self.encoding_combo.setCurrentIndex(saved_encoding_index)

        self.encoding_combo.currentIndexChanged.connect(self.on_encoding_changed)
        encoding_select_layout.addWidget(self.encoding_combo)
        encoding_group_layout.addLayout(encoding_select_layout)

        layout.addWidget(encoding_group)

        # 分词设置区域
        segment_group = QGroupBox("分词设置")
        segment_layout = QVBoxLayout(segment_group)
        segment_layout.setSpacing(15)
        segment_layout.setContentsMargins(15, 20, 15, 15)

        # 分词说明
        segment_desc = QLabel(
            "分词功能可以在转换前对文本进行分词预处理，以提高转换准确性。"
        )
        segment_desc.setWordWrap(True)
        segment_layout.addWidget(segment_desc)

        # 分词选项
        segment_options_layout = QVBoxLayout()

        # 不分词选项
        self.no_segment_cb = QCheckBox("不分词（默认）")
        self.no_segment_cb.setChecked(True)
        self.no_segment_cb.stateChanged.connect(lambda state: self.on_segment_mode_changed("none", state))

        # 结巴分词（现代汉语）选项
        self.jieba_modern_cb = QCheckBox("结巴分词 · 现代汉语")
        self.jieba_modern_cb.stateChanged.connect(lambda state: self.on_segment_mode_changed("jieba_modern", state))

        # 结巴分词（古汉语）选项
        self.jieba_ancient_cb = QCheckBox("结巴分词 · 古汉语")
        self.jieba_ancient_cb.stateChanged.connect(lambda state: self.on_segment_mode_changed("jieba_ancient", state))

        segment_options_layout.addWidget(self.no_segment_cb)
        segment_options_layout.addWidget(self.jieba_modern_cb)
        segment_options_layout.addWidget(self.jieba_ancient_cb)
        segment_layout.addLayout(segment_options_layout)

        # 从设置中恢复分词选择
        saved_segment_mode = self.settings.value("segment_mode", "none")
        self._apply_segment_mode(saved_segment_mode)

        layout.addWidget(segment_group)

        # PDF校对模式设置区域
        pdf_group = QGroupBox("PDF校对模式")
        pdf_group_layout = QVBoxLayout(pdf_group)
        pdf_group_layout.setSpacing(15)
        pdf_group_layout.setContentsMargins(15, 20, 15, 15)

        # 校对模式说明
        pdf_desc = QLabel(
            "勾选后，PDF转换输出的文档中被转换修改的汉字将以黄色底纹标出，便于校对。"
        )
        pdf_desc.setWordWrap(True)
        pdf_group_layout.addWidget(pdf_desc)

        self.highlight_pdf_cb = QCheckBox("PDF转换后为被修改的字添加黄色高亮")
        self.highlight_pdf_cb.setToolTip("仅对PDF文件生效：转换中被修改的汉字以黄色底纹标出")
        self.highlight_pdf_cb.stateChanged.connect(self.on_pdf_highlight_changed)
        pdf_group_layout.addWidget(self.highlight_pdf_cb)

        # 从设置中恢复PDF校对模式
        saved_pdf_highlight = self.settings.value("pdf_highlight", False, type=bool)
        self.highlight_pdf_cb.setChecked(saved_pdf_highlight)

        layout.addWidget(pdf_group)

        layout.addStretch()
        return tab

    def _apply_segment_mode(self, mode):
        """应用分词模式设置"""
        self.no_segment_cb.setChecked(False)
        self.jieba_modern_cb.setChecked(False)
        self.jieba_ancient_cb.setChecked(False)

        if mode == "jieba_modern":
            self.jieba_modern_cb.setChecked(True)
        elif mode == "jieba_ancient":
            self.jieba_ancient_cb.setChecked(True)
        else:
            self.no_segment_cb.setChecked(True)

    def on_segment_mode_changed(self, mode, state):
        """分词模式更改事件处理（互斥逻辑）"""
        if state != Qt.CheckState.Checked.value:
            return

        # 互斥：勾选一个时取消其他
        if mode == "none":
            self.jieba_modern_cb.setChecked(False)
            self.jieba_ancient_cb.setChecked(False)
        elif mode == "jieba_modern":
            self.no_segment_cb.setChecked(False)
            self.jieba_ancient_cb.setChecked(False)
        elif mode == "jieba_ancient":
            self.no_segment_cb.setChecked(False)
            self.jieba_modern_cb.setChecked(False)

        # 保存设置
        self.settings.setValue("segment_mode", mode)
        mode_display = {
            "none": "不分词",
            "jieba_modern": "结巴分词（现代汉语）",
            "jieba_ancient": "结巴分词（古汉语）"
        }
        self.statusBar().showMessage(f"分词设置已更改为: {mode_display.get(mode, '不分词')}")

    def on_encoding_changed(self, index):
        """编码设置更改事件处理"""
        self.settings.setValue("encoding_index", index)
        encoding_name = self.encoding_combo.currentText()
        self.statusBar().showMessage(f"编码设置已更改为: {encoding_name}")

    def on_pdf_highlight_changed(self, state):
        """PDF校对模式（修改字黄色高亮）更改事件处理"""
        checked = self.highlight_pdf_cb.isChecked()
        self.settings.setValue("pdf_highlight", checked)
        self.statusBar().showMessage(
            f"PDF校对模式（修改字黄色高亮）已{'开启' if checked else '关闭'}")

    def on_theme_changed(self, theme, state):
        """主题更改事件处理（复选框互斥逻辑）"""
        if state != Qt.CheckState.Checked.value:
            return
        # 互斥：勾选一个时取消另一个
        if theme == "dark":
            self.light_theme_cb.setChecked(False)
        else:
            self.dark_theme_cb.setChecked(False)
        self.change_theme(theme)

    def apply_theme(self, theme):
        dark = theme == "dark"
        self.current_theme = "dark" if dark else "light"
        canvas, sidebar, surface, ink, muted, border, selected = (
            ("#1e2226", "#252a30", "#2b3137", "#edf2f6", "#b4c0ca", "#48545e", "#20465f")
            if dark else
            ("#f6f8fa", "#eaf0f5", "#ffffff", "#1b2936", "#4c6275", "#c6d2dc", "#cde6f8")
        )
        accent = "#08629b"
        focus = "#57aee8" if dark else accent
        palette = QApplication.style().standardPalette()
        for role, color in (
            (QPalette.Window, canvas), (QPalette.Base, surface), (QPalette.Text, ink),
            (QPalette.WindowText, ink), (QPalette.ButtonText, ink), (QPalette.Button, surface),
            (QPalette.Highlight, accent), (QPalette.HighlightedText, "#ffffff"),
            (QPalette.PlaceholderText, muted), (QPalette.Link, focus),
        ):
            palette.setColor(role, QColor(color))
        QApplication.instance().setPalette(palette)
        self.setStyleSheet(f"""
            QWidget#workspace {{ background: {canvas}; }}
            QFrame#sidebar {{ background: {sidebar}; border-right: 1px solid {border}; }}
            QLabel#brand {{ font-size: 18px; font-weight: 700; padding: 0 8px; }}
            QLabel#pageHeading {{ font-size: 29px; font-weight: 700; }}
            QLabel#muted {{ color: {muted}; }}
            QPushButton#navigation {{
                text-align: left; padding: 8px 12px; border: 1px solid transparent;
                border-radius: 8px; background: transparent; font-weight: 500;
            }}
            QPushButton#navigation:hover, QPushButton#navigation:checked {{ background: {selected}; }}
            QPushButton#navigation:checked {{ font-weight: 700; }}
            QPushButton#navigation:focus {{ border-color: {focus}; }}
            QGroupBox {{
                background: {surface}; border: 1px solid {border}; border-radius: 10px;
                margin-top: 9px; font-weight: 600;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; subcontrol-position: top left;
                left: 13px; padding: 0 5px; background: {surface};
            }}
            QLineEdit, QTextEdit {{
                background: {surface}; border: 1px solid {border};
                border-radius: 6px; padding: 5px; color: {ink};
            }}
            QLineEdit:focus, QTextEdit:focus {{ border-color: {focus}; }}
            QPushButton#startButton {{
                background: {accent}; color: white; border: 2px solid transparent;
                border-radius: 7px; padding: 5px 16px; font-weight: 600;
            }}
            QPushButton#startButton:hover {{ background: #074e7c; }}
            QPushButton#startButton:focus {{ border-color: #79c8ff; }}
            QPushButton#startButton:disabled {{ background: {sidebar}; color: {muted}; }}
            QFrame#actionBar {{ border-top: 1px solid {border}; background: {surface}; }}
        """)

    def change_theme(self, theme):
        """更改主题"""
        if theme != self.current_theme:
            self.apply_theme(theme)
            # 保存主题设置
            self.settings.setValue("theme", theme)
            self.statusBar().showMessage(f"已切换至{theme}主题，设置已保存")

    def _checked_batch_types(self):
        return [ext for checkbox, extensions in self.batch_type_checkboxes.values()
                if checkbox.isChecked() for ext in extensions]

    def save_batch_settings(self, *_):
        self.settings.setValue("batch_convert_all_types", not self.batch_custom_types_cb.isChecked())
        self.settings.setValue("batch_custom_types", self._checked_batch_types())
        self.settings.setValue("keep_original_filename", self.keep_original_name_cb.isChecked())

    def on_batch_types_changed(self, custom):
        for checkbox, _ in self.batch_type_checkboxes.values():
            checkbox.setEnabled(custom)
        self.save_batch_settings()

    def save_settings(self):
        """保存所有设置"""
        # 保存主题
        self.settings.setValue("theme", self.current_theme)
        # 保存编码设置
        self.settings.setValue("encoding_index", self.encoding_combo.currentIndex())
        # 保存分词设置
        if self.jieba_modern_cb.isChecked():
            segment_mode = 'jieba_modern'
        elif self.jieba_ancient_cb.isChecked():
            segment_mode = 'jieba_ancient'
        else:
            segment_mode = 'none'
        self.settings.setValue("segment_mode", segment_mode)

        # 保存PDF校对模式设置
        self.settings.setValue("pdf_highlight", self.highlight_pdf_cb.isChecked())
        self.save_batch_settings()

    def create_conversion_tab(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(15)
        self.page_heading(layout, "文件转换", "选择文件或文件夹（含全部子文件夹）。转换结果另存到指定位置。")

        source = QGroupBox("1. 选择来源")
        source_layout = QVBoxLayout(source)
        source_layout.setContentsMargins(15, 20, 15, 13)
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("拖入文件或文件夹，也可粘贴完整路径")
        self.input_edit.setAccessibleName("输入路径")
        self.input_edit.textEdited.connect(self.on_input_edited)
        source_layout.addWidget(self.input_edit)
        self.source_summary = QLabel()
        self.source_summary.setObjectName("muted")
        self.source_summary.setWordWrap(True)
        self.source_summary.setTextFormat(Qt.TextFormat.PlainText)
        self.source_summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.source_summary.hide()
        source_layout.addWidget(self.source_summary)
        choices = QHBoxLayout()
        for name, callback in (("选择文件…", self.browse_input), ("选择文件夹…", self.browse_input_folder)):
            button = QPushButton(name)
            button.clicked.connect(callback)
            choices.addWidget(button)
        choices.addStretch()
        source_layout.addLayout(choices)
        layout.addWidget(source)

        rules = QGroupBox("2. 选择转换规则")
        rules_layout = QVBoxLayout(rules)
        rules_layout.setContentsMargins(15, 20, 15, 13)
        self.type_combo = QComboBox()
        self.type_combo.addItems(CONVERSION_TYPES)
        self.type_combo.setAccessibleName("文件转换规则")
        rules_layout.addWidget(self.type_combo)
        self.preserve_format_cb = QCheckBox("Word：尽量保留原有格式")
        self.preserve_format_cb.setChecked(True)
        rules_layout.addWidget(self.preserve_format_cb)
        self.convert_footnotes_cb = QCheckBox("Word：转换脚注和尾注")
        self.convert_footnotes_cb.setChecked(True)
        rules_layout.addWidget(self.convert_footnotes_cb)
        layout.addWidget(rules)

        batch = QGroupBox("文件夹批量选项")
        batch_layout = QVBoxLayout(batch)
        batch_layout.setContentsMargins(15, 20, 15, 13)
        info = QLabel("仅选择文件夹时生效，包含全部子文件夹。")
        info.setObjectName("muted")
        batch_layout.addWidget(info)
        self.batch_custom_types_cb = QCheckBox("只转换指定文件类型")
        custom = not self.settings.value("batch_convert_all_types", True, type=bool)
        self.batch_custom_types_cb.setChecked(custom)
        batch_layout.addWidget(self.batch_custom_types_cb)
        grid = QGridLayout()
        saved = self.settings.value("batch_custom_types", sorted(SUPPORTED_EXTENSIONS))
        if isinstance(saved, str):
            saved = [saved]
        saved = set(saved or [])
        self.batch_type_checkboxes = {}
        options = [("DOCX", [".docx"]), ("TXT", [".txt"]), ("MD", [".md"]),
                   ("SRT", [".srt"]), ("ASS/SSA", [".ass", ".ssa"]), ("LRC", [".lrc"]),
                   ("EPUB", [".epub"]), ("PDF", [".pdf"])]
        for i, (name, extensions) in enumerate(options):
            checkbox = QCheckBox(name)
            checkbox.setChecked(any(ext in saved for ext in extensions))
            checkbox.setEnabled(custom)
            checkbox.toggled.connect(self.save_batch_settings)
            self.batch_type_checkboxes[name] = (checkbox, extensions)
            grid.addWidget(checkbox, i // 4, i % 4)
        batch_layout.addLayout(grid)
        self.keep_original_name_cb = QCheckBox("保留原文件名（不加 convert_ 前缀）")
        self.keep_original_name_cb.setToolTip("输出到原文件所在目录时仍加 convert_ 前缀，以保护原件。")
        self.keep_original_name_cb.setChecked(
            self.settings.value("keep_original_filename", False, type=bool))
        self.keep_original_name_cb.toggled.connect(self.save_batch_settings)
        self.batch_custom_types_cb.toggled.connect(self.on_batch_types_changed)
        batch_layout.addWidget(self.keep_original_name_cb)
        layout.addWidget(batch)

        output = QGroupBox("3. 选择输出文件夹")
        output_layout = QVBoxLayout(output)
        output_layout.setContentsMargins(15, 20, 15, 13)
        row = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("选择文件夹或粘贴文件夹路径")
        self.output_edit.setAccessibleName("输出文件夹")
        row.addWidget(self.output_edit, 1)
        browse = QPushButton("选择位置…")
        browse.clicked.connect(self.browse_output)
        row.addWidget(browse)
        output_layout.addLayout(row)
        hint = QLabel("默认加上 convert_ 前缀；文件夹转换保留目录结构，可选择保留原文件名。")
        hint.setObjectName("muted")
        output_layout.addWidget(hint)
        layout.addWidget(output)
        layout.addStretch()
        page_layout.addWidget(self.scroll_page(content), 1)

        footer = QFrame()
        footer.setObjectName("actionBar")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(24, 10, 24, 12)
        actions = QHBoxLayout()
        self.progress_label = QLabel("准备就绪")
        self.progress_label.setTextFormat(Qt.TextFormat.PlainText)
        self.progress_label.setWordWrap(True)
        self.progress_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        actions.addWidget(self.progress_label, 1)
        self.log_button = QPushButton("查看日志")
        self.log_button.setCheckable(True)
        actions.addWidget(self.log_button)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_conversion)
        actions.addWidget(self.cancel_button)
        self.start_button = QPushButton("开始转换")
        self.start_button.setObjectName("startButton")
        self.start_button.clicked.connect(self.start_conversion)
        actions.addWidget(self.start_button)
        footer_layout.addLayout(actions)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximumHeight(14)
        footer_layout.addWidget(self.progress_bar)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(118)
        self.log_text.hide()
        self.log_button.toggled.connect(self.log_text.setVisible)
        self.log_button.toggled.connect(
            lambda shown: self.log_button.setText("收起日志" if shown else "查看日志"))
        footer_layout.addWidget(self.log_text)
        page_layout.addWidget(footer)
        return page

    def create_about_tab(self):
        """创建关于选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)

        # 描述区域
        desc_label = QLabel(f"""
        <h2>规范繁体字形转换器 V{VERSION} for Mac</h2>
        <p>专业的繁体字形转换工具，助您将繁体旧字形、异体字和港台标准的繁体字形转换为《通用规范汉字表》的规范繁体字形。</p>
        <p><b>主要特性:</b></p>
        <ul>
            <li>支持Word文档、TXT文本文件、EPUB文件、字幕文件的繁体字形转换</li>
            <li>有限支持PDF文件的繁体字形转换</li>
            <li>基于《通用规范汉字表》</li>
            <li>转换后保留原文档格式</li>
            <li>支持批量处理文件</li>
            <li>多种转换预设模式适合处理情况复杂的文档</li>
        </ul>
        <p><b>请从以下页面获取本工具最新版本：</p>
        <ul>
              <p>主仓库（Github）：https://github.com/TerryTian-tech/OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards
              <p>镜像1（Gitee）：https://gitee.com/terrytian-tech/tonggui-traditional-chinese
              <p>镜像2（GitCode）：https://gitcode.com/TerryTian-tech/OpenCC-Tonggui-Traditional-Chinese
        </ul>
        <p><b>本软件遵循Apache-2.0开源协议发布。</p>
        <p>交流繁简转换相关问题可进QQ群：1055649831。</p>
        """)
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(desc_label)
        check_update_btn = QPushButton("查看上游项目")
        check_update_btn.setObjectName("browseButton")
        check_update_btn.clicked.connect(lambda: __import__('webbrowser').open(
            'https://github.com/TerryTian-tech/OpenCC-Traditional-Chinese-characters-according-to-Chinese-government-standards'))
        layout.addWidget(check_update_btn, alignment=Qt.AlignCenter)

        layout.addStretch()
        return tab

    def browse_input(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", "",
            "所有支持的文件 (*.docx *.txt *.md *.srt *.ass *.ssa *.lrc *.epub *.pdf);;文本文件 (*.txt);;Markdown 文件 (*.md);;字幕文件 (*.srt *.ass *.ssa *.lrc);;Word 文档 (*.docx);;EPUB 电子书 (*.epub);;PDF 文件 (*.pdf);;所有文件 (*)"
        )
        if paths:
            self.choose_paths(paths)

    def browse_input_folder(self):
        path = QFileDialog.getExistingDirectory(self, "选择输入文件夹")
        if path:
            self.choose_paths([path])

    def on_input_edited(self):
        """用户手动编辑输入框时，清空多选文件列表"""
        self.selected_files = []
        self.source_summary.hide()
        # 如果当前显示的是多选占位文本，清空输入框以避免状态不同步
        text = self.input_edit.text()
        if text.startswith("已选择 ") and text.endswith(" 个文件"):
            self.input_edit.clear()
            
    def browse_output(self):
        """浏览输出路径"""
        path = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if path:
            self.output_edit.setText(path)

    def start_conversion(self):
        """开始转换"""
        input_path = self.input_edit.text()
        output_path = self.output_edit.text()

        if not input_path or not output_path:
            QMessageBox.warning(self, "警告", "请输入完整的路径信息")
            return

        if os.path.exists(output_path) and not os.path.isdir(output_path):
            QMessageBox.warning(self, "输出路径无效", "输出路径必须是文件夹")
            return

        # 验证输入路径
        if self.selected_files:
            # 多文件模式：验证每个文件是否存在
            missing_files = [f for f in self.selected_files if not os.path.exists(f)]
            if missing_files:
                QMessageBox.critical(self, "错误", f"以下文件不存在:\n" + "\n".join(missing_files))
                return
        else:
            if not os.path.exists(input_path):
                QMessageBox.critical(self, "错误", "输入路径不存在")
                return

        folder_mode = not self.selected_files and os.path.isdir(input_path)
        folder_extensions = self._checked_batch_types() if folder_mode and self.batch_custom_types_cb.isChecked() else None
        keep_original_name = folder_mode and self.keep_original_name_cb.isChecked()
        if folder_extensions == []:
            QMessageBox.warning(self, "未选择文件类型", "请至少勾选一种文件类型，或关闭“只转换指定文件类型”。")
            return

        try:
            if self.selected_files:
                source_paths = list(self.selected_files)
            elif os.path.isdir(input_path):
                source_paths = [
                    os.path.join(input_path, rel)
                    for rel in collect_supported_files(input_path, output_path, folder_extensions)
                ]
            else:
                source_paths = [input_path]

            source_paths = [
                path for path in source_paths
                if os.path.isfile(path) and os.path.splitext(path)[1].lower() in SUPPORTED_EXTENSIONS
            ]
            if not source_paths:
                QMessageBox.warning(self, "没有可转换文件", "请选择受支持的文档或包含受支持文档的文件夹。")
                return

            names = [
                os.path.join(os.path.dirname(os.path.relpath(path, input_path)),
                             output_filename(path, os.path.join(output_path, os.path.dirname(os.path.relpath(path, input_path))),
                                             keep_original_name))
                if folder_mode else output_filename(path, output_path)
                for path in source_paths
            ]
            # macOS 常用文件系统可能忽略大小写和 Unicode 组合形式。
            name_keys = {normalize("NFC", name).casefold() for name in names}
            if len(names) != len(name_keys):
                QMessageBox.warning(self, "文件重名", "本批文件会生成同名结果，请分批转换或改用不同的输出文件夹。")
                return

            source_ids = {(st.st_dev, st.st_ino) for st in map(os.stat, source_paths)}
            existing = []
            for name in names:
                destination = os.path.join(output_path, name)
                parent = os.path.dirname(os.path.abspath(destination))
                while parent != os.path.abspath(output_path):
                    if os.path.islink(parent) or (os.path.exists(parent) and not os.path.isdir(parent)):
                        QMessageBox.warning(self, "输出路径冲突", f"请选择其他输出文件夹：{name}")
                        return
                    parent = os.path.dirname(parent)
                if not os.path.lexists(destination):
                    continue
                if os.path.islink(destination) or not os.path.isfile(destination):
                    QMessageBox.warning(self, "输出路径冲突", f"请选择其他输出文件夹：{name}")
                    return
                st = os.stat(destination)
                if (st.st_dev, st.st_ino) in source_ids:
                    QMessageBox.warning(self, "输出与原件冲突", f"为保护原件，请选择其他输出文件夹：{name}")
                    return
                existing.append(name)
        except OSError as exc:
            QMessageBox.warning(self, "无法检查文件", str(exc))
            return

        if existing:
            preview = "\n".join(existing[:10])
            if len(existing) > 10:
                preview += f"\n…（共 {len(existing)} 个文件）"
            dialog = QMessageBox(QMessageBox.Icon.Question, "已有转换结果",
                                 f"以下结果已存在，是否覆盖？\n\n{preview}",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
            dialog.button(QMessageBox.StandardButton.Yes).setText("覆盖")
            dialog.button(QMessageBox.StandardButton.No).setText("取消")
            dialog.setDefaultButton(QMessageBox.StandardButton.No)
            dialog.setEscapeButton(QMessageBox.StandardButton.No)
            dialog.setTextFormat(Qt.TextFormat.PlainText)
            if dialog.exec() != QMessageBox.StandardButton.Yes:
                return

        conversion_type = CONVERSION_TYPES[self.type_combo.currentText()]

        # 获取转换选项的实际值
        preserve_format = self.preserve_format_cb.isChecked()
        convert_footnotes = self.convert_footnotes_cb.isChecked()
        highlight_pdf = self.highlight_pdf_cb.isChecked()

        # 获取强制编码选项
        force_encoding = self.encoding_combo.currentData()

        # 获取分词模式
        if self.jieba_modern_cb.isChecked():
            segment_mode = 'jieba_modern'
        elif self.jieba_ancient_cb.isChecked():
            segment_mode = 'jieba_ancient'
        else:
            segment_mode = None

        # 如果已有转换线程在运行，先取消并等待其结束
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
            
        # 启动转换线程
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.log_text.clear()

        # 在日志中显示当前设置
        segment_mode_display = {
            None: '不分词',
            'jieba_modern': '结巴分词（现代汉语）',
            'jieba_ancient': '结巴分词（古汉语）'
        }
        self.append_log(f"转换设置：保留格式={preserve_format}，转换脚注={convert_footnotes}，强制编码={force_encoding or '自动'}，分词模式={segment_mode_display.get(segment_mode, '不分词')}，PDF修改字高亮={'开' if highlight_pdf else '关'}")

        self.worker = ConversionWorker(
            input_path,
            output_path,
            conversion_type,
            preserve_format,  # 使用复选框的实际值
            convert_footnotes,  # 使用复选框的实际值
            force_encoding,
            segment_mode,
            input_paths=source_paths,
            output_folders=[os.path.dirname(os.path.join(output_path, name)) for name in names],
            highlight_pdf=highlight_pdf,
            folder_extensions=folder_extensions,
            keep_original_name=keep_original_name
        )
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.conversion_finished.connect(self.conversion_finished)
        self.worker.log_message.connect(self.append_log)
        self.worker.start()

    def update_progress(self, value, message):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
        self.append_log(f"[{value}%] {message}")

    def append_log(self, message):
        """添加日志消息"""
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def cancel_conversion(self):
        """取消转换"""
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.cancel()  # 调用自定义的取消方法
            self.append_log("正在取消转换...")
            self.statusBar().showMessage("正在取消转换...")

    def conversion_finished(self, success, message, success_count, total_files):
        """转换完成"""
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)  # 转换完成后禁用取消按钮

        if success:
            self.progress_label.setText(f"已转换 {success_count}/{total_files} 个文件")
            self.statusBar().showMessage("转换完成")
        else:
            if "取消" in message or "已取消" in message:
                QMessageBox.information(self, "已取消", "转换已被用户取消")
                self.statusBar().showMessage("转换已取消")
            elif "部分" in message:
                self.log_button.setChecked(True)
                self.progress_label.setText("部分转换失败")
                QMessageBox.warning(self, "部分失败", f"成功转换 {success_count}/{total_files} 个文件，部分文件转换失败")
                self.statusBar().showMessage("部分转换失败")
            else:
                self.log_button.setChecked(True)
                self.progress_label.setText("转换失败，请查看日志")
                QMessageBox.critical(self, "错误", message)
                self.statusBar().showMessage("转换失败")

    def closeEvent(self, event):
        """窗口关闭事件，保存设置"""
        # 如果转换正在进行，先取消
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
        if getattr(self, 'text_worker', None) is not None and self.text_worker.isRunning():
            self.text_worker.cancel()
            self.text_worker.wait()

        # 保存当前设置
        self.save_settings()
        event.accept()


class MacApplication(QApplication):
    def __init__(self, arguments):
        super().__init__(arguments)
        self.pending_open = []

    def event(self, event):
        if event.type() == QEvent.Type.FileOpen:
            if hasattr(self, 'main_window'):
                self.main_window.choose_paths([event.file()])
            else:
                self.pending_open.append(event.file())
            return True
        return super().event(event)


def main():
    if '--self-test' in sys.argv:
        from self_test import run_self_test
        run_self_test()
        return
    app = MacApplication(sys.argv)
    app.setApplicationName("规范繁体字形转换器")
    app.setOrganizationName("TerryTian-tech")

    # 设置应用程序图标（会显示在任务栏）
    # 注意：Windows上可能还需要单独的.ico文件才能正确显示任务栏图标
    app_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.ico")
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))
    else:
        # 如果没有找到图标文件，可以尝试png格式
        app_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
        if os.path.exists(app_icon_path):
            app.setWindowIcon(QIcon(app_icon_path))

    window = ModernUI()
    app.main_window = window
    if app.pending_open:
        window.choose_paths(app.pending_open)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

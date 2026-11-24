"""Exercise recursive conversion through the real Mac UI with isolated settings."""
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox
import main


def run():
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="tonggui-batch-") as directory:
        root = Path(directory)
        settings = QSettings(str(root / "settings.ini"), QSettings.Format.IniFormat)
        with patch.object(main, "QSettings", return_value=settings):
            window = main.ModernUI()

        source = root / "来源"
        output = source / "转换结果"
        for rel in ("顶层.txt", "甲/同名.txt", "乙/深层/同名.txt"):
            path = source / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("啟淨垔", encoding="utf-8")
        output.mkdir()
        (output / "既有.txt").write_text("不要再次转换", encoding="utf-8")
        (source / "ignore.bin").write_bytes(b"ignore")
        assert main.collect_supported_files(str(source), str(output)) == [
            "顶层.txt", "乙/深层/同名.txt", "甲/同名.txt"]

        def wait():
            deadline = time.monotonic() + 20
            while window.worker.isRunning():
                app.processEvents()
                assert time.monotonic() < deadline, "Conversion timed out"
                time.sleep(0.01)
            app.processEvents()
            assert window.worker._success_count == 3
            assert window.worker._total_files == 3

        window.selected_files = []
        window.input_edit.setText(str(source))
        window.output_edit.setText(str(output))
        window.start_conversion()
        wait()
        results = sorted(output.rglob("convert_*.txt"))
        assert len(results) == 3
        for path in results:
            assert path.read_text(encoding="utf-8") == "啓净垔"
        assert (output / "既有.txt").read_text(encoding="utf-8") == "不要再次转换"
        print("Recursive UI conversion, directory layout, nested output exclusion: OK")

        previews = []
        def cancel(dialog):
            previews.append(dialog.text())
            assert dialog.defaultButton() == dialog.button(QMessageBox.StandardButton.No)
            return QMessageBox.StandardButton.No
        old_worker = window.worker
        with patch.object(QMessageBox, "exec", cancel):
            window.start_conversion()
        assert window.worker is old_worker
        assert "甲/convert_同名.txt" in previews[0] and "乙/深层/convert_同名.txt" in previews[0]
        with patch.object(QMessageBox, "exec", return_value=QMessageBox.StandardButton.Yes):
            window.start_conversion()
        wait()
        print("Relative conflict preview, default cancel and confirmed overwrite: OK")

        result = output / "甲/convert_同名.txt"
        result.unlink()
        os.link(source / "甲/同名.txt", result)
        with patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Ok) as warning:
            previous = window.worker
            window.start_conversion()
            assert window.worker is previous
            assert warning.call_args.args[1] == "输出与原件冲突"
        result.unlink()
        print("Hard-linked original protection: OK")


        import shutil
        shutil.rmtree(output / "甲")
        outside = root / "outside"
        outside.mkdir()
        (output / "甲").symlink_to(outside, target_is_directory=True)
        with patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Ok) as warning:
            previous = window.worker
            window.start_conversion()
            assert window.worker is previous
            assert warning.call_args.args[1] == "输出路径冲突"
        assert not list(outside.iterdir())
        (output / "甲").unlink()
        print("Symbolic-link output directory protection: OK")

        window.selected_files = [str(source / "甲/同名.txt"), str(source / "乙/深层/同名.txt")]
        with patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Ok) as warning:
            previous = window.worker
            window.start_conversion()
            assert window.worker is previous
            assert warning.call_args.args[1] == "文件重名"
        window.selected_files = []
        print("Multi-file flat-output duplicate protection: OK")

        # 1.5.0 options must use the same plan for warnings and conversion.
        batch_source = root / "类型筛选"
        batch_source.mkdir()
        (batch_source / "测试.TXT").write_text("啟淨", encoding="utf-8")
        (batch_source / "跳过.md").write_text("啟淨", encoding="utf-8")
        batch_output = root / "保留文件名"
        window.input_edit.setText(str(batch_source))
        window.output_edit.setText(str(batch_output))
        window.keep_original_name_cb.setChecked(True)
        window.batch_custom_types_cb.setChecked(True)
        for name, (checkbox, _) in window.batch_type_checkboxes.items():
            checkbox.setChecked(name == "TXT")

        def run_batch(expected_count):
            window.start_conversion()
            deadline = time.monotonic() + 20
            while window.worker.isRunning():
                app.processEvents()
                assert time.monotonic() < deadline
                time.sleep(0.01)
            app.processEvents()
            assert window.worker._success_count == expected_count
            assert window.worker._total_files == expected_count

        run_batch(1)
        assert [p.name for p in batch_output.iterdir()] == ["测试.TXT"]
        assert (batch_output / "测试.TXT").read_text(encoding="utf-8") == "啓净"
        old_worker = window.worker
        with patch.object(QMessageBox, "exec", cancel):
            window.start_conversion()
        assert window.worker is old_worker and "测试.TXT" in previews[-1]
        with patch.object(QMessageBox, "exec", return_value=QMessageBox.StandardButton.Yes):
            run_batch(1)
        print("1.5.0 file filter, original filenames, cancel and overwrite: OK")

        window.batch_type_checkboxes["TXT"][0].setChecked(False)
        with patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Ok) as warning:
            window.start_conversion()
            assert warning.call_args.args[1] == "未选择文件类型"
        # Persist an explicitly empty selection, then reload it without resetting.
        settings.sync()
        with patch.object(main, "QSettings", return_value=settings):
            restored = main.ModernUI()
        assert restored.batch_custom_types_cb.isChecked()
        assert restored._checked_batch_types() == []
        assert restored.keep_original_name_cb.isChecked()
        restored.close()
        print("Empty type selection rejection and settings persistence: OK")

        window.batch_type_checkboxes["TXT"][0].setChecked(True)
        window.output_edit.setText(str(batch_source))
        run_batch(1)
        assert (batch_source / "测试.TXT").read_text(encoding="utf-8") == "啟淨"
        assert (batch_source / "convert_测试.TXT").read_text(encoding="utf-8") == "啓净"
        print("Same-directory original-name fallback protects source: OK")

        # Directory aliases must also trigger the original-protecting prefix.
        alias = root / "来源别名"
        alias.symlink_to(batch_source, target_is_directory=True)
        assert main.output_filename(str(batch_source / "测试.TXT"), str(alias), True) == "convert_测试.TXT"

        # Folder-only settings do not change explicit file selections.
        window.selected_files = [str(batch_source / "跳过.md")]
        window.input_edit.setText(str(batch_source / "跳过.md"))
        window.output_edit.setText(str(root / "explicit"))
        run_batch(1)
        assert (root / "explicit/convert_跳过.md").exists()
        print("Directory alias fallback and explicit-file mode isolation: OK")

        # Direct worker folder entry follows the same recursive behavior.
        direct = root / "direct"
        worker = main.ConversionWorker(str(source), str(direct))
        # Remove nested old output from this direct-mode sample.
        (output / "既有.txt").unlink()
        import shutil
        shutil.rmtree(output)
        worker.run()
        assert worker._success_count == 3
        assert len(list(direct.rglob("convert_*.txt"))) == 3
        filtered = root / "direct-filtered"
        worker = main.ConversionWorker(str(batch_source), str(filtered),
                                       folder_extensions=[".md"], keep_original_name=True)
        worker.run()
        assert worker._success_count == worker._total_files == 1
        assert (filtered / "跳过.md").read_text(encoding="utf-8") == "啓净"
        print("Direct worker type filter and original naming: OK")
        window.close()
        app.processEvents()
        print("Direct recursive worker: OK")


if __name__ == "__main__":
    run()

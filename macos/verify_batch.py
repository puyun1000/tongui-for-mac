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
        window.close()
        app.processEvents()
        print("Direct recursive worker: OK")


if __name__ == "__main__":
    run()

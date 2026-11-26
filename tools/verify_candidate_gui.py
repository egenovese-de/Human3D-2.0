"""Run the installed desktop workflow against local, authorized synthetic photos."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PySide6.QtCore import QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QPushButton
from pxr import Usd

from human3d import __version__
from human3d.appearance_dialog import AppearanceDialog
from human3d.desktop import PhotosWindow
from human3d.garment_dialog import GarmentDialog
from human3d.mask_dialog import MaskDialog


def click(widget):
    assert widget.isEnabled(), widget.text()
    QTest.mouseClick(widget, Qt.MouseButton.LeftButton)


def drive_modal(cls, labels, errors):
    execute = cls.exec

    def drive(dialog):
        def respond():
            try:
                for label in labels:
                    buttons = [b for b in dialog.findChildren(QPushButton) if b.text().replace("&", "") == label]
                    button, = buttons
                    click(button)
                if isinstance(dialog, MaskDialog):
                    assert dialog.result() == dialog.DialogCode.Accepted, dialog.message.text()
            except Exception as error:
                errors.append(error)
            finally:
                if not isinstance(dialog, MaskDialog) or errors:
                    dialog.accept()

        QTimer.singleShot(0, respond)
        return execute(dialog)

    return patch.object(cls, "exec", drive)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("photos", nargs="+", type=Path, help="Target first, followed by reference photos")
    args = parser.parse_args()
    app = QApplication([])
    with TemporaryDirectory(prefix="human3d-gui-") as tmp, ExitStack() as stack:
        root = Path(tmp)
        project = root / "project"
        exports = [root / name for name in ("body.usdc", "textured.usdz", "outfit.usdz")]
        errors = []
        stack.enter_context(patch.object(QMessageBox, "information"))
        stack.enter_context(patch.object(QMessageBox, "warning", side_effect=lambda *a: errors.append(a[-1])))
        stack.enter_context(patch.object(QFileDialog, "getExistingDirectory",
                                         side_effect=[str(project), str(args.assets.resolve()), str(project)]))
        stack.enter_context(patch.object(QFileDialog, "getOpenFileNames",
                                         return_value=([str(path.resolve()) for path in args.photos], "")))
        stack.enter_context(patch.object(QFileDialog, "getOpenFileName",
                                         return_value=(str(args.model.resolve()), "")))
        stack.enter_context(patch.object(QFileDialog, "getSaveFileName",
                                         side_effect=[(str(path), "") for path in exports]))
        stack.enter_context(drive_modal(MaskDialog, ["Apply mask"], errors))
        stack.enter_context(drive_modal(AppearanceDialog, ["Export textured USDZ"], errors))
        stack.enter_context(drive_modal(GarmentDialog, ["Fit garment", "Export garment assembly"], errors))
        project.mkdir()
        window = PhotosWindow()
        stack.callback(window.close)
        window.resize(1000, 700)
        window.show()
        app.processEvents()
        for action in ("New project", "Add photos", "Freeze rest body", "Review target mask",
                       "Fit included photos", "Export USD", "Inspect appearance",
                       "Assemble garments", "Open project"):
            click(window.actions[action])
            assert not errors, errors
            print(f"GUI PASS {action}", flush=True)
        saved = window.store.load()
        assert len(saved.photos.photos) == len(args.photos)
        assert window.session.current_shared_fit() is not None
        if len(args.photos) > 1:
            item = window.photos.item(1)
            QTest.mouseClick(window.photos.viewport(), Qt.MouseButton.LeftButton,
                             pos=window.photos.visualItemRect(item).center())
            assert window.store.load().photos.target != saved.photos.target
            assert window.store.load().shared_fit_digest == saved.shared_fit_digest
        for export in exports:
            stage = Usd.Stage.Open(str(export))
            assert stage and stage.GetDefaultPrim()
            if export.name == "outfit.usdz":
                assert stage.GetPrimAtPath("/Human/Garments/top")
            del stage
        print("CANDIDATE_GUI " + json.dumps({
            "status": "PASS", "version": __version__, "photos": len(args.photos),
            "exports": {path.name: path.stat().st_size for path in exports},
        }), flush=True)


if __name__ == "__main__":
    main()

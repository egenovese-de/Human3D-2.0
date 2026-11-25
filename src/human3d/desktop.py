"""Minimal desktop workflow; reconstruction is not yet available."""
from pathlib import Path
from PIL import Image, ImageOps
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QFileDialog, QInputDialog, QLabel, QMenu, QMessageBox)
from .session import Session
from .originals import OriginalStore
from .ingestion import folder_inputs
from .thumbnails import thumbnail
from .mask_dialog import MaskDialog
from .vision import PoseLandmarker
from .frozen_body import load_project_body


class PhotosWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.store = None
        self.session = None
        self.fitted_preview = None
        self.pose_corrections = {}
        self.setWindowTitle("Human3D 2.0")
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        layout.addLayout(toolbar)
        for label, callback in (("New project", self.new_project),
                                ("Open project", self.open_project),
                                ("Add photos", self.add_photos),
                                ("Add folder", self.add_folder),
                                ("Review target mask", self.review_target_mask),
                                ("Freeze rest body", self.freeze_rest_body),
                                ("Inspect fitted body", self.inspect_fitted_body),
                                ("Export USD", self.export_fitted_body)):
            button = QPushButton(label)
            button.clicked.connect(callback)
            toolbar.addWidget(button)
        self.photos = QListWidget()
        self.photos.setViewMode(QListWidget.ViewMode.IconMode)
        from PySide6.QtCore import QSize
        self.photos.setIconSize(QSize(160, 160))
        self.photos.itemClicked.connect(self.select_target)
        self.photos.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.photos.customContextMenuRequested.connect(self.photo_actions)
        layout.addWidget(self.photos)
        self.status = QLabel("Create or open a project. Reconstruction unavailable.")
        layout.addWidget(self.status)
        shared = QPushButton("Fit included photos")
        shared.clicked.connect(self.fit_included)
        layout.addWidget(shared)
        revisions = QHBoxLayout()
        edit = QPushButton("Edit body control")
        edit.clicked.connect(lambda: self.guarded(self.edit_shared_fit))
        revisions.addWidget(edit)
        refine_head = QPushButton("Refine head width")
        refine_head.clicked.connect(lambda: self.guarded(self.refine_head_width))
        revisions.addWidget(refine_head)
        restore = QPushButton("Restore body revision")
        restore.clicked.connect(lambda: self.guarded(self.restore_shared_fit))
        revisions.addWidget(restore)
        appearance = QPushButton("Inspect appearance")
        appearance.clicked.connect(lambda: self.guarded(self.inspect_appearance))
        revisions.addWidget(appearance)
        garment = QPushButton("Assemble garments")
        garment.clicked.connect(lambda: self.guarded(self.assemble_garments))
        revisions.addWidget(garment)
        layout.addLayout(revisions)

    def guarded(self, operation):
        try:
            operation()
        except (OSError, ValueError, RuntimeError, KeyError, ImportError) as error:
            QMessageBox.warning(self, "Operation failed", str(error))

    def new_project(self):
        directory = QFileDialog.getExistingDirectory(self, "Select project directory")
        if directory:
            self.guarded(lambda: self.attach(directory, True))

    def open_project(self):
        directory = QFileDialog.getExistingDirectory(self, "Open project")
        if directory:
            self.guarded(lambda: self.attach(directory, False))

    def attach(self, directory, create=False):
        session = Session(Path(directory), create)
        self.session = session
        self.fitted_preview = None
        self.store = session.store
        self.refresh()

    def add_photos(self):
        if self.store is None:
            return
        paths, _ = QFileDialog.getOpenFileNames(self, "Add photos")
        if paths:
            self.guarded(lambda: self.ingest([Path(p) for p in paths]))

    def add_folder(self):
        if self.store is None:
            return
        directory = QFileDialog.getExistingDirectory(self, "Add folder")
        if directory:
            self.guarded(lambda: self.ingest(folder_inputs(Path(directory))))

    def ingest(self, paths):
        results = self.session.ingest(paths)
        self.refresh()
        counts = ", ".join(f"{status}: {sum(r.status == status for r in results)}"
                           for status in ("accepted", "duplicate", "rejected"))
        self.status.setText(counts + " | Reconstruction unavailable")
        return results

    def _corrected_fit(self, project, body, fit, alignment):
        saved = self.pose_corrections.get((project.id, project.revision))
        if saved is not None and saved[0] == fit:
            alignment = saved[1]
        return body, fit, alignment

    def current_fit(self):
        if self.store is not None and self.fitted_preview is not None:
            project = self.store.load()
            project_id, revision, body, result, alignment = self.fitted_preview
            if project.id == project_id and project.revision == revision:
                return self._corrected_fit(project, body, result, alignment)
        if self.session is not None:
            shared = self.session.current_shared_fit()
            if shared is not None:
                project = self.store.load()
                target = project.photos.target
                if target in shared.alignments:
                    return self._corrected_fit(project, load_project_body(self.store), shared.fit,
                                               shared.alignments[target])
        self.status.setText("Fit the current target or the included photos first.")
        return None

    def fit_included(self):
        if self.session is None:
            return
        self.guarded(self.run_shared_fit)

    def run_shared_fit(self):
        project = self.store.load()
        if project.frozen_body_digest is None:
            raise ValueError("Freeze a rest body first.")
        missing = [photo.id for photo in project.photos.photos
                   if photo.included and project.observation(photo.id) is None]
        if missing:
            model = self.pick_model()
            if not model:
                return
            self.detect_references(missing, model)
        result = self.session.fit_shared()
        self.fitted_preview = None
        evidence = self.session.shared_evidence()
        coverage = "\n".join(f"{region.replace('_', ' ')} {len(evidence.supporting_views(region))}"
                             for region in ("torso", "left_arm", "right_arm", "left_leg", "right_leg"))
        self.status.setText(f"{len(result.scores)} fitted views | overlap "
                            f"{result.fit.bootstrap_iou:.1%} → {result.fit.fitted_iou:.1%}")
        names = {photo.id: photo.name for photo in self.store.load().photos.photos}
        scores = "\n".join(f"{names[key]}: {score:.1%}" for key, score in result.scores.items())
        missing = "\n".join(f"{names[key]}: {reason.replace('_', ' ')}" for key, reason in evidence.unresolved)
        summary = f"Supporting photos by region\n{coverage}\n\nSilhouette overlap by photo\n{scores}"
        if missing:
            summary += f"\n\nNeeds review\n{missing}"
        QMessageBox.information(self, "Shared fit", summary)

    def refine_head_width(self):
        from .face import propose_head_width

        current = self.session.current_shared_fit() if self.session is not None else None
        if current is None:
            raise ValueError("Fit included photos first.")
        proposal, views = propose_head_width(load_project_body(self.store), self.session.shared_evidence(), current)
        edited = self.session.edit_shared_control("head_width", proposal)
        self.fitted_preview = None
        self.status.setText(f"Head-width control {proposal:+.2f} from {views} eye view(s). "
                            f"Silhouette overlap {edited.fit.fitted_iou:.1%}.")

    def edit_shared_fit(self):
        from .frozen_body import morph_controls
        from .proportions import length_controls

        current = self.session.current_shared_fit() if self.session is not None else None
        if current is None:
            raise ValueError("Fit the included photos before editing body controls.")
        body = load_project_body(self.store)
        controls = (*morph_controls(body), *length_controls(body))
        from .face import has_head_control

        if has_head_control(body):
            controls += ("head_width",)
        if "jaw" in body["rig"]["bones"]:
            controls += ("jaw_width",)
        name, accepted = QInputDialog.getItem(self, "Edit body control", "Control", controls, editable=False)
        if not accepted:
            return
        value, accepted = QInputDialog.getDouble(self, "Edit body control", name,
                                                current.fit.controls.get(name, 0), -0.5, 0.5, 3)
        if accepted:
            self.session.edit_shared_control(name, value)
            self.fitted_preview = None
            self.status.setText("Body edit saved as a new revision.")

    def restore_shared_fit(self):
        revisions = self.session.restorable_fits() if self.session is not None else ()
        if not revisions:
            raise ValueError("No prior body revision matches the current references.")
        digest, accepted = QInputDialog.getItem(self, "Restore body revision", "Revision",
                                                tuple(reversed(revisions)), editable=False)
        if accepted:
            self.session.restore_shared_fit(digest)
            self.fitted_preview = None
            self.status.setText("Prior body revision restored.")

    def pick_model(self):
        model, _ = QFileDialog.getOpenFileName(self, "Select local Pose Landmarker model",
                                                filter="MediaPipe model (*.task)")
        return Path(model) if model else None

    def detect_references(self, ids, model):
        detector = PoseLandmarker(model, segmentation=True)
        try:
            for photo_id in ids:
                self.session.detect_photo(photo_id, detector)
        finally:
            detector.close()

    def photo_actions(self, point):
        item = self.photos.itemAt(point)
        if self.session is None or item is None:
            return
        photo_id = item.data(Qt.ItemDataRole.UserRole)
        project = self.store.load()
        photo = next(photo for photo in project.photos.photos if photo.id == photo_id)
        menu = QMenu(self)
        inclusion = menu.addAction("Exclude from fit" if photo.included else "Include in fit")
        inclusion.setEnabled(photo_id != project.photos.target)
        retry = menu.addAction("Retry detection")
        retry.setEnabled(photo.included)
        choice = menu.exec(self.photos.viewport().mapToGlobal(point))
        if choice is inclusion:
            self.guarded(lambda: self.set_reference_inclusion(photo_id, not photo.included))
        elif choice is retry:
            model = self.pick_model()
            if model:
                self.guarded(lambda: self.detect_references((photo_id,), model))

    def set_reference_inclusion(self, photo_id, included):
        self.session.include_reference(photo_id, included)
        self.refresh()

    def inspect_fitted_body(self):
        from .body_preview import BodyPreview

        def inspect():
            fit = self.current_fit()
            if fit is not None:
                project = self.store.load()
                def save_pose(alignment):
                    if self.store.load() == project:
                        self.pose_corrections[(project.id, project.revision)] = (fit[1], alignment)

                BodyPreview(*fit, parent=self, on_pose_applied=save_pose).exec()

        self.guarded(inspect)

    def _prepare_appearance(self):
        from .appearance import prepare_view

        current = self.current_fit()
        if current is None:
            return
        body, fit, target_alignment = current
        project = self.store.load()
        target = project.photos.target
        shared = self.session.current_shared_fit()
        alignments = (shared.alignments if shared is not None and shared.fit == fit else {}) | {target: target_alignment}
        evidence = self.session.shared_evidence()
        originals = OriginalStore(self.store.directory)
        views = {
            view.ref.photo_id: (prepare_view(originals, view, alignments[view.ref.photo_id]), view.detection.image_size)
            for view in evidence.views
            if view.mask is not None and view.ref.photo_id in alignments
            and alignments[view.ref.photo_id].camera.horizontal_sign == 1
        }
        if target not in views:
            raise ValueError("Review the target mask and refit with M3 before baking appearance.")
        return project, body, fit, target_alignment, views, target

    def assemble_garments(self):
        from .garment_dialog import GarmentDialog

        context = self._prepare_appearance()
        if context is None:
            return
        project, body, fit, target_alignment, views, target = context

        def export(color, garments):
            from .usd_export import export_body

            if self.store.load() != project:
                raise ValueError("The project changed. Reopen the assembly before exporting.")
            destination, _ = QFileDialog.getSaveFileName(self, "Export garment assembly", "outfit.usdz",
                                                        "OpenUSD package (*.usdz)")
            if destination:
                export_body(Path(destination), body, fit, target_alignment, texture=color, garments=garments)
                self.status.setText("Body and independent garments exported with their shared rig.")

        GarmentDialog(body, fit, views, target, export, parent=self).exec()

    def inspect_appearance(self):
        from .appearance_dialog import AppearanceDialog
        from .texture_bake import bake_atlas

        context = self._prepare_appearance()
        if context is None:
            return
        project, body, fit, target_alignment, views, target = context
        atlas = bake_atlas(body, fit.controls, views, target)
        if self.store.load() != project:
            raise ValueError("The project changed during texture baking. Bake the current target again.")

        def export(color, roughness):
            def save():
                from .usd_export import export_body

                if self.store.load() != project:
                    raise ValueError("The project changed. Rebuild the target appearance before exporting.")
                destination, _ = QFileDialog.getSaveFileName(self, "Export textured body", "body.usdz",
                                                            "OpenUSD package (*.usdz)")
                if destination:
                    export_body(Path(destination), body, fit, target_alignment,
                                texture=color, roughness=roughness)
                    self.status.setText("Textured, rigged USDZ exported and validated.")

            self.guarded(save)

        AppearanceDialog(atlas, export, parent=self).exec()

    def export_fitted_body(self):
        self.guarded(self.choose_export_destination)

    def choose_export_destination(self):
        fit = self.current_fit()
        if fit is None:
            return
        destination, _ = QFileDialog.getSaveFileName(self, "Export rigged body", "body.usda",
                                                    "OpenUSD (*.usd *.usda *.usdc)")
        if destination:
            self.write_fitted_body(Path(destination), fit)

    def write_fitted_body(self, destination, fit):
        from .usd_export import export_body

        export_body(destination, *fit)
        self.status.setText("Rigged USD exported and reopened for validation.")

    def freeze_rest_body(self):
        if self.store is None:
            self.status.setText("Create or open a project first.")
            return
        assets = QFileDialog.getExistingDirectory(self, "Select verified bootstrap assets directory")
        if assets:
            self.guarded(lambda: self.attach_rest_body(Path(assets)))

    def attach_rest_body(self, assets):
        from .bootstrap import freeze_project

        freeze_project(self.store, assets)
        self.status.setText("Rest body attached. Review the target mask to inspect alignment.")

    def review_target_mask(self):
        if self.session is None or self.session.snapshot().project.photos.target is None:
            self.status.setText("Select a target photo first.")
            return
        model, _ = QFileDialog.getOpenFileName(self, "Select local Pose Landmarker model", filter="MediaPipe model (*.task)")
        if model:
            self.guarded(lambda: self.analyze_mask(Path(model)))

    def analyze_mask(self, model):
        self.fitted_preview = None
        detector = PoseLandmarker(model, segmentation=True)
        try:
            evidence = self.session.detect_target(detector)
        finally:
            detector.close()
        if evidence is None or not evidence.candidates:
            self.status.setText("No current subject candidate. Select another photo and retry.")
            return
        original = OriginalStore(self.store.directory).verify(evidence.photo_digest)
        with Image.open(original) as image:
            photo = ImageQt(ImageOps.exif_transpose(image).convert("RGB"))
        body = load_project_body(self.store) if self.store.load().frozen_body_digest else None
        def fit(draft, alignment):
            from .fitting import fit_body

            mask = self.session.apply_mask(draft)
            project = self.store.load()
            result = fit_body(body, mask, alignment)
            if self.store.load() != project:
                raise ValueError("The project changed during fitting. Review the current target again.")
            self.fitted_preview = (project.id, project.revision, body, result, alignment)
            return result

        def apply(draft):
            self.session.apply_mask(draft)
            self.fitted_preview = None

        _, correction = self.session.read_observation(self.store.load().photos.target)
        if MaskDialog(photo, evidence, apply, self, body=body, fit=fit, correction=correction).exec():
            self.status.setText("Subject mask saved to the project.")
        elif self.fitted_preview is not None:
            self.status.setText("Fitted body ready for inspection or USD export.")

    def refresh(self):
        snapshot = self.session.snapshot()
        project = snapshot.project
        self.photos.clear()
        for photo in project.photos.photos:
            pixmap = QPixmap()
            pixmap.loadFromData(thumbnail(OriginalStore(self.store.directory), photo.digest))
            item = QListWidgetItem(QIcon(pixmap), photo.name)
            item.setData(Qt.ItemDataRole.UserRole, photo.id)
            self.photos.addItem(item)
            if not photo.included:
                item.setText(photo.name + " [Excluded]")
            if photo.id == project.photos.target:
                item.setText(photo.name + " [Target]")
                self.photos.setCurrentItem(item)
        self.status.setText(f"{len(project.photos.photos)} photos | Reconstruction unavailable")

    def select_target(self, item):
        def select():
            photo_id = item.data(Qt.ItemDataRole.UserRole)
            if not any(photo.id == photo_id and photo.included for photo in self.store.load().photos.photos):
                self.status.setText("Include this photo before selecting it as the target.")
                return
            self.session.select_target(photo_id)
            self.refresh()
        self.guarded(select)


def main():
    app = QApplication([])
    window = PhotosWindow()
    window.resize(1000, 700)
    window.show()
    return app.exec()

"""Versioned application service for the empirical desktop."""
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import file_digest, sha256
from io import BytesIO
import json
import os
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile, TemporaryDirectory
from threading import Event, Lock
from time import perf_counter
from typing import Callable, Protocol
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
from PIL import Image, ImageDraw

from .asset_preflight import verify_assets
from .originals import OriginalStore
from .project import PhotoSet
from .project_store import sync_directory, writer_lock
from .session import Session

SCHEMA_VERSION = 1
BASELINE = "m6"
BASELINE_REVISION = "e0ae4eae57347466b5757bbcdaaa7194bdd31c94"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    with path.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())


def sha_file(path):
    with path.open("rb") as handle:
        return file_digest(handle, "sha256").hexdigest()


@dataclass(frozen=True)
class ReconstructionRequest:
    id: str
    project_id: str
    photos: PhotoSet
    engine: str
    application_revision: str
    garment: str | None
    started_at: str
    calibration: str | None = None


@dataclass(frozen=True)
class Progress:
    stage: str
    outcome: str
    message: str = ""
    seconds: float | None = None


@dataclass
class Diagnostics:
    execution_revision: str
    executed_engine: str
    stages: list[Progress] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Result:
    directory: Path
    metadata: dict

    @property
    def id(self):
        return self.metadata["request"]["id"]

    def file(self, name):
        if name not in self.metadata["artifacts"] or Path(name).name != name:
            raise ValueError("Artifact unavailable.")
        return self.directory / name


class Cancelled(RuntimeError):
    pass


class StaleRequest(RuntimeError):
    pass


class Engine(Protocol):
    revision: str

    def reconstruct(self, session: Session, request: ReconstructionRequest, output: Path,
                    execution: "Execution") -> str: ...


class Execution:
    def __init__(self, diagnostics: Diagnostics, cancel: Event, notify: Callable[[Progress], None]):
        self.diagnostics = diagnostics
        self.cancel = cancel
        self.notify = notify

    def checkpoint(self):
        if self.cancel.is_set():
            raise Cancelled("Reconstruction cancelled.")

    @contextmanager
    def stage(self, name, *, optional=False):
        self.checkpoint()
        self.notify(Progress(name, "running"))
        start = perf_counter()
        outcome, message = "passed", ""
        try:
            yield
        except Exception as error:
            self.checkpoint()
            outcome, message = "failed", str(error)
            if not optional:
                raise
            self.diagnostics.warnings.append(f"{name}: {message}")
        finally:
            if self.cancel.is_set():
                outcome, message = "cancelled", ""
            event = Progress(name, outcome, message, perf_counter() - start)
            self.diagnostics.stages.append(event)
            self.notify(event)
        self.checkpoint()


class ReconstructionService:
    def __init__(self, session: Session, engines: dict[str, Engine], application_revision: str):
        self.session = session
        self.engines = engines
        self.revision = application_revision
        self.attempts = session.store.directory / "reconstructions"
        self._running = Lock()

    def request(self, engine=BASELINE, garment=None, calibration=None):
        project = self.session.store.load()
        if not project.photos.target:
            raise ValueError("Import a photograph and select a target first.")
        if engine not in self.engines:
            raise ValueError("The requested engine is unavailable.")
        return ReconstructionRequest(uuid4().hex, project.id, project.photos, engine,
                                     self.revision, garment, utc_now(), calibration)

    def _check_inputs(self, request):
        project = self.session.store.load()
        if project.id != request.project_id or project.photos != request.photos:
            raise StaleRequest("The references or target changed. Run Generate 3D again.")

    def generate(self, request, cancel: Event, notify: Callable[[Progress], None]) -> Result:
        if not self._running.acquire(blocking=False):
            raise RuntimeError("A reconstruction is already running.")
        try:
            return self._generate(request, cancel, notify)
        finally:
            self._running.release()

    def _generate(self, request, cancel, notify):
        engine = self.engines[request.engine]
        diagnostics = Diagnostics(engine.revision, request.engine)
        execution = Execution(diagnostics, cancel, notify)
        self.attempts.mkdir(exist_ok=True)
        destination = self.attempts / request.id
        start = perf_counter()
        with TemporaryDirectory(prefix=".attempt-", dir=self.attempts) as temporary:
            output = Path(temporary) / request.id
            output.mkdir()
            canonical = None
            failure = None
            try:
                with execution.stage("Validate project inputs"):
                    self._check_inputs(request)
                    originals = OriginalStore(self.session.store.directory)
                    for photo in request.photos.photos:
                        if photo.included:
                            originals.verify(photo.digest)
                canonical = engine.reconstruct(self.session, request, output, execution)
                if not (output / "preview.npz").is_file() or not any(output.glob("canonical.usd*")):
                    raise ValueError("Engine failed to produce canonical artifacts.")
                with execution.stage("Verify publication inputs"):
                    self._check_inputs(request)
                artifacts = {path.name: {"sha256": sha_file(path), "bytes": path.stat().st_size}
                             for path in output.iterdir()}
            except Exception as error:
                failure = error
                if execution.cancel.is_set() and not isinstance(error, Cancelled):
                    failure = Cancelled("Reconstruction cancelled.")
            with writer_lock(self.session.store.directory):
                if failure is None:
                    try:
                        execution.checkpoint()
                        self._check_inputs(request)
                        evidence_digest = diagnostics.metrics.get("photographic_evidence_digest")
                        if evidence_digest is not None:
                            from .fusion import fuse_observations

                            latest = fuse_observations(self.session.store.load(), self.session.observations)
                            if latest.dependency_digest != evidence_digest:
                                raise StaleRequest("Photographic evidence changed. Run Generate 3D again.")
                    except (Cancelled, StaleRequest) as error:
                        failure = error
                if failure is not None:
                    shutil.rmtree(output)
                    output.mkdir()
                    artifacts = {}
                    canonical = None
                status = ("complete" if failure is None else "cancelled" if isinstance(failure, Cancelled)
                          else "stale" if isinstance(failure, StaleRequest) else "failed")
                request_metadata = asdict(request)
                if request.calibration:
                    request_metadata["calibration"] = Path(request.calibration).name
                metadata = {"schema_version": SCHEMA_VERSION, "request": request_metadata,
                            "status": status, "canonical_id": canonical,
                            "target_result_id": request.id if any(name.startswith("target.usd") for name in artifacts) else None,
                            "diagnostics": asdict(diagnostics), "artifacts": artifacts,
                            "finished_at": utc_now(), "duration_seconds": perf_counter() - start,
                            "error": str(failure) if failure is not None else None}
                write_json(output / "result.json", metadata)
                if destination.exists():
                    raise FileExistsError("Reconstruction identity was already published.")
                os.replace(output, destination)
                sync_directory(self.attempts)
            if failure is not None:
                raise failure
            return Result(destination, metadata)

    def results(self, *, include_failures=False):
        results = []
        for path in self.attempts.glob("*/result.json"):
            if path.parent.name.startswith("."):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data["schema_version"] == SCHEMA_VERSION and data["request"]["id"] == path.parent.name:
                    if include_failures or data["status"] == "complete":
                        results.append(Result(path.parent, data))
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return sorted(results, key=lambda result: result.metadata["request"]["started_at"], reverse=True)

    def export(self, result, destination: Path, *, target=True):
        if result.metadata["status"] != "complete":
            raise ValueError("Select a completed reconstruction.")
        prefix = "target." if target else "canonical."
        name = next((name for name in result.metadata["artifacts"] if name.startswith(prefix + "usd")), None)
        if name is None:
            raise ValueError("The selected representation is unavailable.")
        source = result.file(name)
        if destination.suffix.lower() != source.suffix:
            raise ValueError(f"Use the {source.suffix} extension for this asset.")
        temporary = None
        try:
            with NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
                temporary = Path(stream.name)
                with source.open("rb") as handle:
                    shutil.copyfileobj(handle, stream)
                stream.flush()
                os.fsync(stream.fileno())
            if sha_file(temporary) != result.metadata["artifacts"][name]["sha256"]:
                raise ValueError("The stored export failed its integrity check.")
            os.replace(temporary, destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def export_evidence(self, result, destination: Path, *, include_photos=False, viewport_png=None):
        metadata = result.metadata
        diagnostics = metadata["diagnostics"]
        temporary = None
        try:
            with NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
                temporary = Path(stream.name)
            with ZipFile(temporary, "w", ZIP_DEFLATED) as archive:
                archive.writestr("diagnostics.json", json.dumps(metadata, indent=2))
                summary = [f"# Reconstruction {result.id}", "", f"Status — {metadata['status']}",
                           f"Engine — {diagnostics['executed_engine']}", "",
                           *[f"- {step['stage']} — {step['outcome']}" for step in diagnostics["stages"]],
                           "", *[f"- {warning}" for warning in diagnostics["warnings"]]]
                if metadata["error"]:
                    summary.extend(("", metadata["error"]))
                archive.writestr("summary.md", "\n".join(summary) + "\n")
                if "overlay.png" in metadata["artifacts"]:
                    archive.write(result.file("overlay.png"), "overlay.png")
                if viewport_png is not None:
                    archive.writestr("viewport.png", viewport_png)
                if include_photos:
                    originals = OriginalStore(self.session.store.directory)
                    for photo in metadata["request"]["photos"]["photos"]:
                        suffix = Path(photo["name"]).suffix.lower()
                        archive.write(originals.verify(photo["digest"]), f"references/{photo['id']}{suffix}")
            os.replace(temporary, destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


class M6Engine:
    revision = BASELINE_REVISION

    def __init__(self, assets: Path, model: Path):
        self.assets = assets
        self.model = model

    def reconstruct(self, session, request, output, execution):
        from .bootstrap import freeze_project, ASSETS, MORPH_ASSETS, TORSO_ASSETS
        from .frozen_body import load_project_body
        from .vision import PoseLandmarker, MODEL_SHA256

        diagnostics = execution.diagnostics
        target = request.photos.target
        photos = [photo for photo in request.photos.photos if photo.included]
        diagnostics.metrics.update(imported_photos=len(request.photos.photos), target=target,
                                   metric_scale="unknown", camera_model="estimated weak perspective")
        with execution.stage("Verify MakeHuman and MediaPipe assets"):
            report = verify_assets(self.model, self.assets)
            if report["status"] != "PASS":
                failed = ", ".join(item["asset"] for item in report["assets"] if item["status"] != "PASS")
                raise ValueError(f"Run setup to restore missing or invalid assets: {failed}")
            project = session.store.load()
            body = load_project_body(session.store) if project.frozen_body_digest else None
            if body is None or body["source_asset_digests"] != ASSETS | MORPH_ASSETS | TORSO_ASSETS:
                freeze_project(session.store, self.assets)
                body = load_project_body(session.store)
        with execution.stage("Extract or reuse photographic observations"):
            detector = PoseLandmarker(self.model, segmentation=True)
            detector.cancel_event = execution.cancel
            reused = 0
            for index, photo in enumerate(photos, start=1):
                execution.checkpoint()
                current = session.read_observation(photo.id)
                if (current is not None and current[0].model_digest == MODEL_SHA256
                        and (current[0].masks or current[1] is not None)):
                    reused += 1
                    continue
                execution.notify(Progress(f"Detect subject · {index}/{len(photos)}", "running"))
                try:
                    if session.detect_photo(photo.id, detector) is None:
                        raise StaleRequest("Photographic inputs changed.")
                except StaleRequest:
                    raise
                except (OSError, RuntimeError, ValueError) as error:
                    execution.checkpoint()
                    diagnostics.warnings.append(f"{photo.name}: {error}")
            diagnostics.metrics["observations_reused"] = reused
        with execution.stage("Register views and fit canonical anatomy"):
            evidence = session.shared_evidence()
            names = {photo.id: photo.name for photo in photos}
            diagnostics.warnings.extend(f"{names.get(key, key)}: {reason.replace('_', ' ')}."
                                        for key, reason in evidence.unresolved)
            body, shared = self.fit_canonical(session, request, execution, body, evidence)
            from .fusion import REGIONS

            confidence = {}
            for view in evidence.views:
                points = view.detection.visible_pose(view.candidate)
                confidence[view.ref.photo_id] = {
                    region: min(points[index].visibility * points[index].presence for index in REGIONS[region])
                    for region in view.observed_regions
                }
            diagnostics.metrics.update(contributing_photos=len(shared.scores), silhouette_iou=shared.scores,
                                       photographic_evidence_digest=shared.evidence_digest,
                                       regional_evidence_confidence=confidence)
        return build_artifacts(session, request, output, execution, body, shared, evidence)

    def fit_canonical(self, session, request, execution, body, evidence):
        shared = session.current_shared_fit()
        execution.diagnostics.metrics["canonical_fit_reused"] = shared is not None
        if shared is None:
            try:
                shared = session.fit_shared()
            except ValueError as error:
                if str(error) == "no_aligned_subject_masks":
                    raise ValueError("No usable mask and body alignment. Try a full-body photo with visible shoulders and hips.") from error
                raise
        execution.diagnostics.metrics["anatomical_controls"] = shared.fit.controls
        return body, shared


def build_artifacts(session, request, output, execution, body, shared, evidence):
    from .alignment import Alignment, Camera
    from .appearance import prepare_view
    from .frozen_body import deform_vertices
    from .native_rig import pose_transforms, skin_vertices, validate_pose, validate_rebind
    from .texture_bake import bake_atlas
    from .usd_export import export_body

    diagnostics = execution.diagnostics
    target = request.photos.target
    metrics = diagnostics.metrics
    warnings = diagnostics.warnings
    warnings.append("Metric scale is unknown. Orientation, framing and articulation are estimated. "
                    "For ambiguous views add a well-lit full-body front and complementary side photo.")
    fit = shared.fit
    target_view = next((view for view in evidence.views if view.ref.photo_id == target), None)
    alignment = shared.alignments.get(target)
    rest = Alignment(Camera(0, 1, 0, 1), 0, {})
    with execution.stage("Validate canonical geometry, UV and rig"):
        neutral = np.asarray(deform_vertices(body, fit.controls), dtype=float)
        joints = validate_rebind(body, neutral)
        faces = np.array([[idx for idx, _ in face["corners"]] for face in body["mesh"]["faces"]
                          if face["group"] == "body"], dtype=np.int32)
        if len(faces) == 0 or any(len(set(row)) != len(row) for row in faces):
            raise ValueError("Invalid body topology.")
        if not np.all((np.asarray(body["mesh"]["texcoords"]) >= 0) & (np.asarray(body["mesh"]["texcoords"]) <= 1)):
            raise ValueError("Invalid UV domain.")
        if any(not body["rig"]["skin"][index] for index in np.unique(faces)):
            raise ValueError("Body vertices are missing skin weights.")
    posed = None
    if alignment is not None and target_view is not None and not target_view.geometry_only and alignment.limb_angles:
        with execution.stage("Validate target pose", optional=True):
            transforms = pose_transforms(body["rig"], joints, alignment)
            candidate = skin_vertices(neutral, body["rig"]["skin"], transforms)
            validate_pose(body, neutral, candidate)
            posed = candidate
    if posed is None:
        warnings.append("Target pose unresolved. The canonical body is available. Use a view with clearly visible joints.")
    metrics.update(target_pose="estimated" if posed is not None else "unresolved",
                   target_camera="estimated" if alignment is not None else "unresolved",
                   torso_rms_pixels=alignment.torso_rms_pixels if alignment is not None else None,
                   candidate_yaw_degrees=alignment.camera.yaw_degrees if alignment is not None else None,
                   orientation_confidence="unqualified", framing_confidence="unqualified")
    atlas, views = None, {}
    if posed is not None:
        with execution.stage("Bake optional appearance", optional=True):
            originals = OriginalStore(session.store.directory)
            for view in evidence.views:
                camera = shared.alignments.get(view.ref.photo_id)
                if view.mask is not None and camera and not view.geometry_only and camera.camera.horizontal_sign == 1:
                    try:
                        views[view.ref.photo_id] = (prepare_view(originals, view, camera), view.detection.image_size)
                    except (OSError, ValueError) as error:
                        warnings.append(f"Appearance view {view.ref.photo_id}: {error}")
            if target not in views:
                raise ValueError("Usable target appearance evidence is unavailable.")
            atlas = bake_atlas(body, fit.controls, views, target)
    metrics["texture_observed_fraction"] = atlas.observed_fraction if atlas else None
    if atlas:
        metrics["appearance_projections"] = {key: asdict(value) for key, value in atlas.view_diagnostics.items()}
    garments = []
    metrics["garment_status"] = "omitted: no supported category selected"
    if request.garment:
        metrics["garment_status"] = "omitted: processing failed"
        with execution.stage("Process optional garment", optional=True):
            from .garment_fit import fit_garment
            from .garments import GarmentAsset

            if atlas is None:
                raise ValueError("A garment layer needs usable target appearance.")
            view, image_size = views[target]
            garment = fit_garment(body, fit, view, image_size, request.garment)
            if garment.blocked:
                raise ValueError(garment.contacts.describe())
            texture = bake_atlas(body, fit.controls, views, target, garment=garment.garment)
            garments.append(GarmentAsset(garment.garment, texture.color, texture.observed_fraction))
            metrics["garment_status"] = "fitted; export validation pending"
    else:
        warnings.append("No independent garment selected. Clothing color may appear in the body texture.")
    with execution.stage("Validate and store USD assets"):
        color = atlas.color if atlas else None
        suffix = ".usdz" if color else ".usd"
        if color is not None:
            with execution.stage("Package optional textured USDZ", optional=True):
                export_body(output / f"canonical{suffix}", body, fit, rest, texture=color)
                if posed is not None:
                    export_body(output / f"target{suffix}", body, fit, alignment, texture=color, garments=garments)
                metrics["garment_status"] = "exported in target USDZ" if garments else metrics["garment_status"]
            if posed is not None and not (output / f"target{suffix}").exists() and garments:
                garments.clear()
                metrics["garment_status"] = "omitted: export validation rejected layer"
                with execution.stage("Package body-only textured target", optional=True):
                    export_body(output / f"target{suffix}", body, fit, alignment, texture=color)
            if not (output / f"canonical{suffix}").exists() or (posed is not None and not (output / f"target{suffix}").exists()):
                for path in output.glob("*.usdz"):
                    path.unlink()
                color, suffix = None, ".usd"
                garments.clear()
                if request.garment:
                    metrics["garment_status"] = "omitted: textured packaging unavailable"
        if color is None:
            export_body(output / f"canonical{suffix}", body, fit, rest)
            if posed is not None:
                export_body(output / f"target{suffix}", body, fit, alignment)
        metrics["structural_validation"] = "passed"
    with execution.stage("Prepare viewport and comparison"):
        arrays = {"faces": faces, "canonical": neutral}
        if posed is not None:
            arrays["target"] = posed
        if color is not None:
            arrays["colors"] = face_colors(body, color)
        if garments:
            from .garments import posed_garment
            garment = garments[0].garment
            triangles = [[corners[index][0] for index in (0, offset, offset + 1)]
                         for corners in garment.faces for offset in range(1, len(corners) - 1)]
            arrays["garment_faces"] = np.asarray(triangles, dtype=np.int32)
            arrays["garment"] = np.asarray(posed_garment(garment, transforms))
        np.savez_compressed(output / "preview.npz", **arrays)
        if posed is not None and target_view.mask is not None:
            with execution.stage("Compare projected and observed silhouette", optional=True):
                comparison_overlay(output / "overlay.png", target_view, alignment.camera, posed, faces)
    return sha256(neutral.astype("<f8").tobytes()).hexdigest()


def face_colors(body, color):
    uv = np.array(body["mesh"]["texcoords"])
    centers = np.array([uv[[index for _, index in face["corners"]]].mean(axis=0)
                        for face in body["mesh"]["faces"] if face["group"] == "body"])
    pixels = np.asarray(color.convert("RGB"))
    y = np.clip(((1 - centers[:, 1]) * pixels.shape[0]).astype(int), 0, pixels.shape[0] - 1)
    x = np.clip((centers[:, 0] * pixels.shape[1]).astype(int), 0, pixels.shape[1] - 1)
    return pixels[y, x]


def comparison_overlay(destination, view, camera, posed, faces):
    with Image.open(BytesIO(view.mask.png)) as mask:
        original_size = mask.size
        mask.thumbnail((640, 640), Image.Resampling.NEAREST)
        observed = np.array(mask.convert("L")) > 0
    height, width = observed.shape
    sx, sy = width / original_size[0], height / original_size[1]
    points = [(p.real * sx, p.imag * sy) for vertex in posed for p in (camera.project(vertex),)]
    raster = Image.new("1", (width, height))
    draw = ImageDraw.Draw(raster)
    for face in faces:
        draw.polygon([points[index] for index in face], fill=1)
    projected = np.array(raster)
    colored = np.zeros((height, width, 4), dtype=np.uint8)
    colored[projected & observed] = (70, 222, 174, 150)
    colored[projected & ~observed] = (242, 113, 98, 200)
    colored[observed & ~projected] = (106, 153, 254, 200)
    overlay = Image.fromarray(colored)
    draw = ImageDraw.Draw(overlay)
    for landmark in view.detection.visible_pose(view.candidate):
        if landmark.observed:
            x, y = landmark.x * width, landmark.y * height
            draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(255, 215, 100, 255))
    overlay.save(destination)

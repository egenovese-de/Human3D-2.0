"""Bounded G1 anatomy and G4 contour fitting for the empirical application."""
from dataclasses import dataclass, replace
from hashlib import sha256
from io import BytesIO
from math import prod
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion, distance_transform_edt
from scipy.sparse import csc_matrix

from .alignment import refine_views
from .fitting import Fit, SharedFit
from .native_rig import pose_transforms, rebind_joints, validate_rebind
from .reconstruction import M6Engine, sha_file

EXPERIMENTAL = "geometry"
G4_REVISION = "ca90165d259bada9b3cea945d1227be0f83656ef"


class NativeBasis:
    """Evaluate G1 dependency products using a setup-provisioned target registry."""

    def __init__(self, runtime, body):
        self.document = json.loads((runtime / "native-registry.json").read_text(encoding="utf-8"))
        if self.document["schema_version"] != 1:
            raise ValueError("Unsupported native evaluator registry.")
        self.base = np.asarray(body["mesh"]["vertices"], dtype=np.float64)
        self.globals = tuple(self.document["globals"])
        self.regional = tuple(item["name"] for item in self.document["local"] if item["fitted"])
        self.initial = dict.fromkeys(self.globals, .5) | {
            item["name"]: item["default"] for item in self.document["local"]
        }
        indices, indptr, deltas = [], [0], []
        for name, digest, size in self.document["files"]:
            path = runtime / "native" / name
            raw = path.read_bytes()
            if len(raw) != size or sha256(raw).hexdigest() != digest:
                raise ValueError(f"Native morph asset integrity failure: {name}")
            rows = [line.split() for line in raw.splitlines() if line.strip() and not line.lstrip().startswith(b"#")]
            data = np.asarray([row for row in rows if len(row) == 4], dtype=np.float64).reshape(-1, 4)
            vertex_ids = data[:, 0].astype(np.int32)
            if (not np.isfinite(data).all() or not np.array_equal(vertex_ids, data[:, 0])
                    or np.any(vertex_ids < 0) or np.any(vertex_ids >= len(self.base))):
                raise ValueError(f"Invalid native offsets: {name}")
            order = vertex_ids.argsort()
            indices.append((vertex_ids[order, None] * 3 + np.arange(3)).ravel().astype(np.int32))
            deltas.append(data[order, 1:].ravel())
            indptr.append(indptr[-1] + len(data) * 3)
        self.matrix = csc_matrix((np.concatenate(deltas), np.concatenate(indices), indptr),
                                 shape=(self.base.size, len(indices)))

    @staticmethod
    def factors(parameters):
        sex, age = parameters["Gender"], parameters["Age"]
        factors = {"female": 1 - sex, "male": sex, "african": 1 / 3, "asian": 1 / 3, "caucasian": 1 / 3,
                   "baby": max(0, 1 - age * 5.333) if age < .5 else 0,
                   "child": max(0, min(1, age * 5.333) - max(0, (age - .1875) * 3.2)) if age < .5 else 0,
                   "young": max(0, (age - .1875) * 3.2) if age < .5 else 2 - 2 * age,
                   "old": max(0, 2 * age - 1)}
        for key, names in (
            ("Weight", ("minweight", "averageweight", "maxweight")),
            ("Muscle", ("minmuscle", "averagemuscle", "maxmuscle")),
            ("Height", ("minheight", "averageheight", "maxheight")),
            ("BodyProportions", ("uncommonproportions", "regularproportions", "idealproportions")),
            ("BreastSize", ("mincup", "averagecup", "maxcup")),
            ("BreastFirmness", ("minfirmness", "averagefirmness", "maxfirmness")),
        ):
            lo, hi = max(0, 1 - 2 * parameters[key]), max(0, 2 * parameters[key] - 1)
            factors.update(zip(names, (lo, 1 - lo - hi, hi)))
        return factors

    def evaluate(self, parameters):
        values = self.initial | parameters
        factors = self.factors(values)
        weights = {}
        for rows in self.document["groups"]:
            for index, *tokens in rows:
                weight = prod(factors[key] for key in tokens[:-1])
                if weight:
                    weights[index] = weight
        for item in self.document["local"]:
            control = values[item["name"]]
            strengths = {item["left"]: max(0, -control), item["right"]: max(0, control)}
            if item["center"]:
                strengths[item["center"]] = 1 - abs(control)
            for index, *tokens in item["targets"]:
                weight = strengths[tokens[-1]] * prod(factors[key] for key in tokens[:-1])
                if weight:
                    weights[index] = weight
                else:
                    weights.pop(index, None)
        ids = np.fromiter(weights, dtype=np.int32)
        return (self.base.ravel() + self.matrix[:, ids] @ np.fromiter(weights.values(), dtype=float)).reshape(-1, 3)

    def parity_error_mm(self):
        return max(float(np.max(np.linalg.norm(self.evaluate(entry["controls"])[entry["indices"]]
                                               - entry["vertices"], axis=1))) * 100
                   for entry in self.document["parity_controls"])


@dataclass(frozen=True)
class CalibratedCamera:
    """G4 camera convention, with geometry supplied in MakeHuman decimeters."""
    yaw: float
    span: float = 215.
    center_y: float = 0.
    elevation: float = 0.
    distance: float = 650.
    perspective: bool = False
    roll: float = 0.
    dx: float = 0.
    dy: float = 0.

    def __post_init__(self):
        values = (self.yaw, self.span, self.center_y, self.elevation, self.distance, self.roll, self.dx, self.dy)
        if not np.isfinite(values).all() or self.span <= 0 or self.distance <= 0 or type(self.perspective) is not bool:
            raise ValueError("Invalid calibrated camera.")

    def project(self, vertices, size):
        azimuth, elevation = np.deg2rad([self.yaw, self.elevation])
        right = np.array([np.cos(azimuth), 0, -np.sin(azimuth)])
        towards = np.array([np.sin(azimuth) * np.cos(elevation), np.sin(elevation),
                            np.cos(azimuth) * np.cos(elevation)])
        up = np.cross(towards, right)
        roll = np.deg2rad(self.roll)
        axes = np.stack((right * np.cos(roll) + up * np.sin(roll),
                         -right * np.sin(roll) + up * np.cos(roll), towards))
        xyz = (vertices * 10 - [0, self.center_y, 0]) @ axes.T
        z = self.distance - xyz[:, 2]
        if self.perspective and (z <= 0).any():
            raise ValueError("Calibrated perspective lies inside the candidate body.")
        scale = size / self.span * (self.distance / z if self.perspective else 1.)
        return np.column_stack((size * (.5 + self.dx) + xyz[:, 0] * scale,
                                size * (.5 + self.dy) - xyz[:, 1] * scale))


@dataclass(frozen=True)
class Observation:
    id: str
    mask: np.ndarray
    project: object
    pose: object
    source: str
    uncertainty: float
    scale: str = "unknown"


def edge(mask):
    return mask & ~binary_erosion(mask, structure=np.ones((3, 3), bool))


class ContourLoss:
    """G4 symmetric truncated contour, uncertainty-weighted occupancy and internal gaps."""

    def __init__(self, mask, size, uncertainty):
        self.target = cv2.resize(mask.astype(np.uint8), (size, size), interpolation=cv2.INTER_NEAREST_EXACT).astype(bool)
        self.edge = edge(self.target)
        self.distance = distance_transform_edt(~self.edge)
        self.weight = np.where(self.distance <= 1, .35, 1.)
        self.gap = (np.maximum.accumulate(self.target, axis=1)
                    & np.maximum.accumulate(self.target[:, ::-1], axis=1)[:, ::-1]
                    & ~self.target & (self.distance > 1))
        self.area = max(1, self.target.sum())
        self.limit = .065 * size
        self.tolerance = min(3., uncertainty * size / 384 * .35)

    def __call__(self, predicted):
        boundary = edge(predicted)
        intersection = (predicted & self.target).sum()
        iou = intersection / max(1, (predicted | self.target).sum())
        if not boundary.any() or not self.edge.any():
            return 1., float(iou)
        forward = self.distance[boundary]
        reverse = distance_transform_edt(~boundary)[self.edge]
        symmetric = sum(np.sqrt(np.mean(np.clip(d - self.tolerance, 0, self.limit) ** 2))
                        for d in (forward, reverse)) / (2 * self.limit)
        occupancy = self.weight[predicted ^ self.target].sum() / self.area
        return float(symmetric + .16 * occupancy + .33 * (predicted & self.gap).sum() / self.area
                     + .14 * (1 - iou)), float(iou)


def raster(camera, vertices, faces, size):
    points = np.rint(camera(vertices, size) * 16).clip(-2**28, 2**28).astype(np.int32)
    packed = points[faces]
    mask = np.zeros((size, size), np.uint8)
    for face in packed:
        cv2.fillConvexPoly(mask, face, 1, shift=4)
    return mask.astype(bool)


def registrations(body, evidence, manifest, diagnostics):
    alignments, unresolved = refine_views(body, evidence)
    rejections = dict(unresolved)
    observations = []
    calibrations = {} if not manifest else calibration_entries(Path(manifest))
    for view in evidence.views:
        key = view.ref.photo_id
        candidate = alignments.get(key)
        if view.mask is None:
            rejections[key] = "No subject mask."
            continue
        with Image.open(BytesIO(view.mask.png)) as source:
            image = source.convert("L")
            width, height = image.size
            pad = max(width, height)
            offset_x, offset_y = (pad - width) // 2, (pad - height) // 2
            squared = Image.new("L", (pad, pad))
            squared.paste(image, (offset_x, offset_y))
            squared.thumbnail((384, 384), Image.Resampling.NEAREST)
            mask = np.array(squared) > 0
        calibrated = calibrations.get(view.ref.photo_digest)
        if calibrated:
            if width != height:
                raise ValueError("Calibrated input requires the original square G4 raster.")
            if not calibrated["canonical_pose"]:
                raise ValueError("Calibrated manifest requires canonical-pose fitting views.")
            camera = CalibratedCamera(**calibrated["camera"])
            observations.append(Observation(key, mask, camera.project, None, "calibrated", 0,
                                            "independent" if calibrated["independent_scale"] else "unknown"))
            continue
        if manifest:
            rejections[key] = "No calibrated camera for this digest."
            continue
        if candidate is None or view.geometry_only:
            rejections[key] = "Unresolved orientation or observation pose."
            continue
        camera = candidate.camera
        torso_pixels = candidate.torso_rms_pixels * 384 / pad
        if not mask.any() or np.mean(mask) > .85 or torso_pixels > 30:
            rejections[key] = "Unreliable camera framing or subject mask."
            continue
        if abs(camera.yaw_degrees) > 65:
            rejections[key] = "Ambiguous orientation: side/rear fit needs externally verified orientation."
            continue

        def project(vertices, size, *, cam=camera, side=pad, left=offset_x, top=offset_y):
            theta = np.deg2rad(cam.yaw_degrees)
            xy = cam.horizontal_sign * (vertices[:, 0] * np.cos(theta) + vertices[:, 2] * np.sin(theta))
            xy = cam.similarity * (xy - 1j * vertices[:, 1]) + cam.origin + complex(left, top)
            return np.column_stack((xy.real, xy.imag)) * (size / side)

        observations.append(Observation(key, mask, project, candidate, "estimated weak perspective",
                                        max(10., torso_pixels)))
    diagnostics.metrics["experimental_registration_exclusions"] = rejections
    diagnostics.metrics["experimental_registration_sources"] = {
        view.id: {"camera": view.source, "scale": view.scale, "sigma_on_384_px": view.uncertainty}
        for view in observations
    }
    if not observations:
        raise ValueError("Engine B found no admissible registration. Add a clear full-body frontal photo or select Engine A.")
    return observations, alignments


def calibration_entries(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported calibration manifest.")
    entries = {}
    for item in data["views"]:
        key = item["photo_sha256"]
        if key in entries or len(key) != 64 or type(item["canonical_pose"]) is not bool or type(item["independent_scale"]) is not bool:
            raise ValueError("Invalid calibrated view declaration.")
        entries[key] = item
    return entries


def bounded_fit(basis, body, observations, checkpoint):
    """Reuse G4's bounded search and guarded progression towards rejected candidates."""
    quads = np.asarray([[index for index, _ in f["corners"]] for f in body["mesh"]["faces"]
                        if f["group"] == "body"], dtype=np.int32)
    rig = body["rig"]
    packed = {}
    for index, influences in enumerate(rig["skin"]):
        for name, weight in influences.items():
            packed.setdefault(name, [[], []])
            packed[name][0].append(index)
            packed[name][1].append(weight)
    packed = {name: (np.array(indices, dtype=int), np.array(weights)[:, None])
              for name, (indices, weights) in packed.items()}
    skinned = np.unique(np.concatenate([indices for indices, _ in packed.values()]))
    scaled = any(view.scale == "independent" for view in observations)
    fields = [key for key in basis.globals if key != "Height" or scaled]
    weights = np.array([1 / (1 + (view.uncertainty / 9) ** 2) for view in observations])
    calls = 0

    def objective(size):
        losses = [ContourLoss(view.mask, size, view.uncertainty) for view in observations]

        def calculate(parameters):
            nonlocal calls
            checkpoint()
            calls += 1
            mesh = basis.evaluate(parameters)
            joints = rebind_joints(rig, mesh)
            costs, overlap = [], {}
            for view, loss in zip(observations, losses):
                points = mesh
                if view.pose is not None and view.pose.limb_angles:
                    points = mesh.copy()
                    points[skinned] = 0
                    for name, (rotation, translation) in pose_transforms(rig, joints, view.pose).items():
                        if name in packed:
                            indices, weights_ = packed[name]
                            points[indices] += (mesh[indices] @ rotation.T + translation) * weights_
                cost, overlap[view.id] = loss(raster(view.project, points, quads, size))
                costs.append(cost)
            if len(costs) > 2:
                costs = .22 * np.log1p(np.array(costs) / .22)
            prior = np.mean([(value - basis.initial[key]) ** 2 for key, value in parameters.items()])
            return float(np.average(costs, weights=weights) + .0015 * prior), overlap
        return calculate

    low, final = objective(96), objective(160)
    seed = basis.initial.copy()
    candidates = [seed]

    def sweep(parameters, selected, steps, evaluate):
        best, _ = evaluate(parameters)
        for step in steps:
            for key in selected:
                bounds = (.10, .90) if key in basis.globals else (-.65, .65)
                if key == "Age":
                    bounds = (.49, .90)
                center = parameters[key]
                for sign in (-1, 1):
                    value = float(np.clip(center + sign * step, *bounds))
                    if value == parameters[key]:
                        continue
                    trial = parameters | {key: value}
                    score, _ = evaluate(trial)
                    if score < best:
                        best, parameters = score, trial
        return parameters

    for gender in (.28, .72):
        candidates.append(sweep(seed | {"Gender": gender}, fields, (.18,), low))
    best = min(candidates, key=lambda p: low(p)[0])
    best = sweep(best, fields + list(basis.regional), (.12, .055), low)
    candidates.append(best)
    candidates.append(sweep(best, fields + list(basis.regional), (.03,), final))
    ranked = sorted(((final(parameters), parameters) for parameters in candidates), key=lambda entry: entry[0][0])
    rejected = []
    unsafe = None
    for (loss, iou), parameters in ranked:
        vertices = basis.evaluate(parameters)
        try:
            validate_rebind(body, vertices)
        except ValueError as error:
            rejected.append(str(error))
            if unsafe is None:
                unsafe = parameters
            continue
        if unsafe:
            safe = parameters.copy()
            lo, hi = 0., 1.
            for _ in range(8):
                alpha = (lo + hi) / 2
                trial = {key: (1 - alpha) * safe[key] + alpha * unsafe[key] for key in safe}
                candidate = basis.evaluate(trial)
                try:
                    validate_rebind(body, candidate)
                except ValueError:
                    hi = alpha
                    continue
                lo = alpha
                score, overlap = final(trial)
                if score < loss:
                    vertices, parameters, loss, iou = candidate, trial, score, overlap
        return vertices, parameters, iou, {"loss": loss, "evaluations": calls,
                                           "rebind_rejections": rejected, "stature_optimized": scaled}
    raise ValueError(f"No structurally valid Engine B candidate. Try Engine A. {', '.join(rejected)}")


class GeometryEngine(M6Engine):
    revision = G4_REVISION

    def __init__(self, root):
        super().__init__(root / "makehuman", root / "pose.task")
        self.root = root
        self.basis = None

    def fit_canonical(self, session, request, execution, body, evidence):
        diagnostics = execution.diagnostics
        manifest_identity = sha_file(Path(request.calibration)) if request.calibration else None
        key = sha256(f"{evidence.dependency_digest}:{manifest_identity}:{request.application_revision}".encode()).hexdigest()
        cache = session.store.directory / "experimental-canonical" / f"{key}.npz"
        if self.basis is None:
            self.basis = NativeBasis(self.root, body)
        parity = self.basis.parity_error_mm()
        if parity > .001:
            raise ValueError(f"Native evaluator parity failed ({parity:.6f} mm).")
        diagnostics.metrics["g1_parity_max_mm"] = parity
        native_home = self.basis.evaluate({})
        native_body = body | {"mesh": body["mesh"] | {"vertices": native_home},
                              "rig": body["rig"] | {"joints": rebind_joints(body["rig"], native_home)}}
        validate_rebind(body, native_home)
        observations, alignments = registrations(native_body, evidence, request.calibration, diagnostics)
        diagnostics.metrics["canonical_fit_reused"] = cache.is_file()
        if cache.is_file():
            with np.load(cache, allow_pickle=False) as data:
                vertices = data["vertices"]
                parameters, iou, fit_report = json.loads(str(data["metadata"]))
        else:
            vertices, parameters, iou, fit_report = bounded_fit(self.basis, body, observations, execution.checkpoint)
            from tempfile import NamedTemporaryFile
            import os

            cache.parent.mkdir(exist_ok=True)
            with NamedTemporaryFile(dir=cache.parent, delete=False) as stream:
                temporary = Path(stream.name)
                np.savez_compressed(stream, vertices=vertices, metadata=json.dumps([parameters, iou, fit_report]))
            try:
                execution.checkpoint()
                os.replace(temporary, cache)
            finally:
                temporary.unlink(missing_ok=True)
        validate_rebind(body, vertices)
        diagnostics.metrics.update(engine_b_fitting=fit_report, calibration_sha256=manifest_identity,
                                   anatomical_controls=parameters, scale_for_canonical_fit=(
                                       "independent calibration" if fit_report["stature_optimized"] else "unknown"))
        diagnostics.warnings.append("Engine B uses a bounded G4 contour fit. Estimated registration can bias shape; "
                                    "the target pose and viewport overlay use the M6 camera estimates.")
        fitted_body = body | {"mesh": body["mesh"] | {"vertices": vertices.tolist()}}
        score = float(np.mean(list(iou.values())))
        return fitted_body, SharedFit(Fit({}, score, score), alignments, evidence.dependency_digest, iou)

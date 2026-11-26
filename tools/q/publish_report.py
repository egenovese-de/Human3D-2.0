"""Consolidate completed Q experiments and write the Lab deliverables."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import statistics
import subprocess

import numpy as np


RELEASE = "480195f05fb2d1ed6c71dceabf4ba54b8bed69db"
LAB_BASE = "3828e922466bb53a8110114553b4aaa1c11fd758"
TASKS = [
    ("Q0", [
        "Verify release baseline, Lab infrastructure and reproducible execution environment",
        "Establish independent anatomical ground-truth meshes and asset provenance",
        "Implement automated Blender multi-view rendering and ground-truth extraction",
        "Implement procedural photographic transformations and optional AI photographic fixture generation",
        "Validate dataset consistency, calibration, manifests and independent evaluation splits",
    ]),
    ("Q1", [
        "Establish neutral geometry reconstruction baseline across anatomical subjects",
        "Measure regional surface reconstruction errors",
        "Measure circumference, proportion and volumetric reconstruction errors",
        "Measure morph sensitivity, saturation and deformation capacity",
        "Evaluate extreme anatomy and out-of-distribution body proportions",
        "Evaluate anatomical asymmetry, spinal curvature and pelvic orientation",
        "Separate geometry representation limits from optimization and convergence limits",
    ]),
    ("Q2", [
        "Execute fully automatic native pipeline baseline",
        "Measure reconstruction improvement using ground-truth segmentation",
        "Measure reconstruction improvement using ground-truth camera parameters",
        "Measure reconstruction improvement using ground-truth landmarks",
        "Measure reconstruction improvement using ground-truth anatomical evidence",
        "Measure reconstruction improvement using ground-truth pose",
        "Measure Geometry Engine limits using all supported ground-truth inputs",
        "Measure downstream reconstruction limits using ground-truth geometry",
    ]),
    ("Q3", [
        "Compare single-view and two-view reconstruction configurations",
        "Compare three-view, four-view, eight-view and sixteen-view reconstruction",
        "Measure the information value of individual camera orientations",
        "Evaluate redundant, contradictory and differently posed reference photographs",
        "Measure held-out reconstruction accuracy and diminishing returns",
    ]),
    ("Q4", [
        "Evaluate resolution, compression, blur and image noise",
        "Evaluate illumination, exposure and background complexity",
        "Evaluate focal length, perspective, camera elevation and orientation",
        "Evaluate cropping, occlusion and incomplete anatomical visibility",
        "Evaluate clothing-induced segmentation and anatomical reconstruction errors",
        "Evaluate photorealistic synthetic photographs and compound failure scenarios",
    ]),
    ("Q5", [
        "Measure facial landmark and regional facial geometry accuracy",
        "Evaluate facial profile, cranial proportions and facial deformation limits",
        "Measure skeletal joint positions, rotations and pose reconstruction errors",
        "Evaluate hand orientation, limb torsion, contact and extreme articulation",
        "Measure texture projection, observed coverage and color reconstruction accuracy",
        "Evaluate UV seams, occlusion contamination and unobserved appearance",
        "Measure garment geometry, fit, boundaries and body intersections",
        "Evaluate garment deformation, layer separation and editable export quality",
    ]),
    ("Q6", [
        "Consolidate experimental measurements and statistical uncertainty",
        "Identify component-level error contributions and verified root causes",
        "Produce comparative renders, failure atlas and reconstruction quality report",
        "Produce prioritized evidence-based M6 recommendations and final reproducibility manifest",
    ]),
]


def read(path, default=None):
    return json.loads(path.read_text()) if path.is_file() else default


def series(values, factor=1):
    values = np.asarray([x for x in values if x is not None], dtype=float) * factor
    if not len(values):
        return "0 | — | — | — | — | — | —"
    stats = [values.mean(), np.median(values), values.std(ddof=1) if len(values) > 1 else 0,
             *np.quantile(values, [.05, .95]), values.min()]
    return str(len(values)) + " | " + " | ".join(f"{v:.3f}" for v in stats)


def table(label, groups, factor=1):
    return (f"| {label} | n | Mean | Median | SD | P05 | P95 | Min |\n"
            "|---|---:|---:|---:|---:|---:|---:|---:|\n" +
            "\n".join(f"| {key} | {series(values, factor)} |" for key, values in groups.items()))


def collect(root, name):
    return {p.stem: read(p) for p in sorted((root / name).glob("*.json"))}


def mean(values):
    return statistics.mean(values) if values else None


def effect(values, factor=100):
    if not values:
        return "unavailable"
    return f"{mean(values)*factor:+.2f} across {len(values)} variants (range {min(values)*factor:+.2f} to {max(values)*factor:+.2f})"


def write_docs(root, lab):
    docs = lab / "DOCS"
    output = docs / "q"
    output.mkdir(exist_ok=True)
    evals = collect(root, "eval")
    ablations = {k: v for k, v in collect(root, "ablated").items() if "results" in v}
    stress = collect(root, "stress")
    detector = collect(root, "detector")
    photographic = stress | {k: v for k, v in detector.items() if k not in stress}
    pose = collect(root, "pose")
    components = collect(root, "components")
    native = {p.parent.name: read(p) for p in sorted((root / "native").glob("*/benchmark.json"))}
    success = {k: v for k, v in native.items() if "observed_uv_fraction" in v}
    failure = {k: v for k, v in native.items() if k not in success}
    ai = {name: read(root / f"ai-native-{name}/benchmark.json") for name in ("workshop", "woodland")}
    historical = read(root / "historical/geometry.json")
    validation = read(root / "validation.json", [])
    sections = read(root / "sections.json", [])
    manifests = {}
    for path in sorted((root / "pilot").glob("*/manifest.json")):
        manifests[path.parent.name] = {
            "blender": read(path),
            "native": read(path.parent / "native-8.json"),
            "perspective": read(path.parent / "perspective.json"),
            "depth": read(root / "depth" / path.parent.name / "manifest.json"),
            "photographic": read(path.parent / "robustness.json"),
        }
    asset_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted((root / "assets").iterdir()) if p.is_file()}
    source = root / "mblab/data/humanoid_library.blend"
    atlas = sorted((root / "visuals").glob("MBLab*.png"))
    for image in atlas:
        shutil.copy2(image, output / image.name)
    experiment_commit = subprocess.check_output(
        ["git", "-C", str(lab), "log", "-1", "--format=%H", "--", "tools/q"], text=True
    ).strip()
    attempts = {"ordered_native_runs": len(native), "native_success": len(success),
                "native_noncomplete": list(failure), "preflight_attempts_missing_host_gles": 12,
                "native_preflight_dirty_lab_retry_count": 1,
                "lab_attempts_missing_usr_bin_time": 12,
                "blender_usd_import": "operator absent in host Blender 4.3.2"}
    perf = {}
    for name, result in success.items():
        log = root / "native" / (name + ".log")
        if name == "MBLab_human_male_base-4":
            log = log.parent / "male-retry.log"
        tokens = re.findall(r"^real\s+(\d+)m([\d.]+)s$", log.read_text(), re.M)
        perf[name] = {"elapsed_seconds": (60 * int(tokens[-1][0]) + float(tokens[-1][1])) if tokens else None,
                      "stage_fit_seconds": result["fit_seconds"],
                      "artifact_bytes": sum(p.stat().st_size for p in (root / "native" / name).rglob("*") if p.is_file())}
    metrics = {"application_sha": RELEASE, "lab_source_commit": experiment_commit, "native": native,
               "failure_attempts": attempts, "native_performance": perf, "geometry": evals,
               "mask_camera_ablation": ablations, "detector": photographic, "pose": pose, "components": components,
               "ai": ai, "sections": sections, "fixture_validation": validation, "history": historical,
               "face_control": read(root / "face.json")}
    (output / "measurements.json").write_text(json.dumps(metrics, indent=2, allow_nan=False) + "\n")
    (output / "manifest.json").write_text(json.dumps({"fixtures": manifests, "runtime_asset_hashes": asset_hashes,
        "mblab_asset_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "ai_preprocessed_images": {p.stem: read(p) for p in (root / "ai-fixtures").glob("*.json")}}, indent=2) + "\n")

    def report(name, title, content):
        (docs / f"Q_{name}.md").write_text(f"# {title}\n\n{content.strip()}\n")

    held = defaultdict(list)
    distances = defaultdict(list)
    runtime = defaultdict(list)
    paired = defaultdict(list)
    for fixture in evals.values():
        results = fixture["results"]
        for name, row in results.items():
            h = mean([v["iou"] for v in row["held_out"].values()])
            held[name].append(h)
            distances[name].append(row["symmetric_mean_mm"])
            if "fit_seconds" in row:
                runtime[name].append(row["fit_seconds"])
            if name in ("front-profile", "front-rear", "three", "four", "eight"):
                paired[name].append(h - mean([v["iou"] for v in results["front"]["held_out"].values()]))
    quartet = defaultdict(list)
    oracle_paired = defaultdict(list)
    for record in ablations.values():
        values = {key: mean(list(value["independent_silhouette_iou"].values()))
                  for key, value in record["results"].items()}
        for name, iou in values.items():
            quartet[name].append(iou)
            oracle_paired[name].append(iou - values["matched_native"])
        oracle_paired["interaction"].append(values["mask_and_camera"] - values["mask_only"] -
                                            values["camera_only"] + values["matched_native"])
    photo_iou = defaultdict(list)
    photo_counts = defaultdict(lambda: [0, 0, 0])
    for rows in photographic.values():
        for row in rows:
            name = row.get("variant", f"yaw {row.get('yaw')}")
            counter = photo_counts[name]
            counter[0] += 1
            counter[1] += row.get("candidate_count") == 1
            counter[2] += row.get("review_reason") is not None or "error" in row
            if "mask_iou" in row:
                photo_iou[name].append(row["mask_iou"])
    pose_effect = [item["oracle_limb_directions_fixed_shape_iou"] -
                   item["native_pose_calibrated_evaluation_iou"] for item in pose.values()]
    blends = [f"- [{p.stem}](q/{p.name})" for p in atlas]
    completed = {"Q0-001", "Q0-002", "Q0-003", "Q0-004", "Q1-004", "Q2-001",
                 "Q4-001", "Q4-004", "Q6-001", "Q6-004"}
    if evals:
        completed |= {"Q1-001", "Q1-002", "Q1-005", "Q1-007", "Q3-001", "Q3-003", "Q3-005"}
    if ablations:
        completed |= {"Q2-002", "Q2-003", "Q6-002"}
    if pose:
        completed.add("Q2-006")
    if stress:
        completed |= {"Q4-002", "Q4-003"}
    if stress and all(item and "detections" in item for item in ai.values()):
        completed.add("Q4-006")
    if atlas:
        completed.add("Q6-003")
    blocked = {
      "Q0-005": "Camera/calibration validation passed. Independent subject holdout remains unavailable with two base meshes and their paired deformation variants.",
      "Q1-003": "Section perimeter proxies were measured. Anatomical tape correspondences and validated volumetric IoU were unavailable.",
      "Q1-006": "A torso displacement stress case was executed. Independently rigged spinal and pelvic rotations were unavailable.",
      "Q2-004": "Rig endpoints exist for selected bones. An independent 33-landmark surface protocol with detector-equivalent visibility was unavailable.",
      "Q2-005": "The provider accepts yaw and visibility only. True measurements or mesh evidence have no provider field, and yaw disagreement can cause rejection.",
      "Q2-007": "Fixed-camera/mask fits and separate limb-direction substitutions ran. A jointly valid pose and landmark oracle was unavailable.",
      "Q2-008": "Independent meshes have different topology, UV and rig. Texture and garment builders require a compatible frozen asset and its rig/UV bindings. No compatible independent adapter was validated.",
      "Q3-002": "Three, four and eight calibrated input cameras were executed. Sixteen calibrated fitting views were unavailable in the pilot.",
      "Q3-004": "Redundant, truly contradictory and differing-posed views were unavailable in calibrated pairs; unrelated AI photos were kept separate.",
      "Q4-005": "Clothed AI cases lack independently paired bare-body geometry and garment masks.",
      "Q5-001": "Cranial surface distance was measured. Annotated facial landmarks and dense facial region masks were unavailable.",
      "Q5-002": "Jaw control locality was exercised. Facial profile/cranial identity ground truth and controlled expressions were unavailable.",
      "Q5-003": "Rest-anchor position and segment-direction errors were measured. Registered ground-truth joint rotations were unavailable.",
      "Q5-004": "The pilot has a neutral stance. Independent articulated wrists, torsion and ground-contact annotations were unavailable.",
      "Q5-005": "Observed UV coverage was measured. A radiometrically calibrated texture target with correspondence was unavailable.",
      "Q5-006": "Measured observed fraction only. Matched UV seams, texture charts and occluder-labelled texels were unavailable.",
      "Q5-007": "Sampled shell clearance was measured. Independent garment mesh, hem alignment and exact triangle intersection labels were unavailable.",
      "Q5-008": "USD package structure and shell motion were inspected. Layered independent cloth and a USD-capable Blender executable were unavailable.",
    }
    for group, titles in TASKS:
        for index in range(1, len(titles) + 1):
            key = f"{group}-{index:03}"
            if key not in completed and key not in blocked:
                blocked[key] = "Required measurement did not produce a verified output in this run."
    backlog = ["| ID | Task | Status |", "|---|---|---|"]
    for group, titles in TASKS:
        for index, title in enumerate(titles, 1):
            key = f"{group}-{index:03}"
            backlog.append(f"| {key} | {title} | {'DONE' if key in completed else 'BLOCKED'} |")
    (docs / "BACKLOG_Q.md").write_text("\n".join(backlog) + "\n")
    report("EXPERIMENTAL_PROTOCOL", "Q experimental protocol", f"""
Release `{RELEASE}`. Native runs use the released Session, detector, fitting, appearance and exporter with no corrections or provider. The release and Lab worktrees are separate. Listwise under four-view intervention includes only views that produced a native fit. Fixed-camera intervention preserves estimated limb fields while overriding initialization and final camera refinement. The segmentation intervention changes the fitted mask field and leaves landmarks and confidence unchanged. The four conditions share the same photos and inference records.

All independent 3D comparisons use one fixed alignment per fixture. Map Human3D X/Y/Z into Blender X/−Z/Y, anchor the native rest floor to zero, and scale once from the neutral base height to the reference height. Do not recompute scale on fitted meshes. Report height-aligned millimeters and retain signed fit residuals. Compare 12,000 seeded area-weighted samples per surface using symmetric nearest-sample distances. Chamfer reports the mean squared bidirectional distance. No vertex correspondence is asserted across topologies. Regions are fixed fractional height bands. Section convex perimeters are outer-envelope proxies.

The controlled multiview arm fits Blender alpha and known orthographic projections without native limb estimation. Its two held-out azimuths per subject enter evaluation only. Direct 3D fitting uses a one-sided nearest-sample objective with the release bounded coordinate search at two step schedules and evaluates symmetric error separately. This supplies an achievable fit, with neither a global optimum guarantee nor matched pose. The fixed-shape pose intervention uses MB-Lab bone endpoint proxy directions.

Detector metrics compare binary native masks and rendered geometry; the single occlusion fixture evaluates the full in-frame silhouette and the compound case evaluates visible pixels. Report failures and exclusions, including unavailable masks. The pilot is descriptive. Its six variants form two correlated source-family clusters. P05/P95 and SD summarize observed variants. No population confidence intervals from two source families.
""")
    report("DATASET_MANIFEST", "Q dataset and asset provenance", f"""
{len(manifests)} metric fixtures from two independently sourced MB-Lab base meshes, each rendered in base, wider torso and bent/asymmetric torso variants. The meshes are more than independent morph coefficients in the Human3D basis. They come from the MB-Lab [pinned upstream](https://github.com/animate1978/MB-Lab/tree/063bff04e60f3e7c651fda628c30f5d83f3f3078), whose [license](https://github.com/animate1978/MB-Lab/blob/063bff04e60f3e7c651fda628c30f5d83f3f3078/license.txt) specifies AGPL-3.0 for the database and separate terms for non-reverse-engineering 2D renders. No MB-Lab meshes, joint databases, UV data, depth/surface rasters or raw datasets are redistributed here. Floor-normalized Y-up source geometry is never inferred from an AI photo. The Blender coordinate system is X lateral, negative Y frontal, Z up. Camera extrinsics are camera-to-world. For the orthographic baseline, the scale spans 2.16 m across 384 pixels.

The controlled set has {sum(len(v['blender']['images']) for v in manifests.values())} orthographic renders, {sum(len(v['perspective'] or []) for v in manifests.values())} perspective renders and {sum(len((v['photographic'] or {}).get('images', [])) for v in manifests.values())} different stress inputs including the perspective composites. Each base mesh includes eight train and two held-out camera azimuths. The camera check compared independently projected polygon masks to Blender alpha on {sum(len(v['validation']) for v in validation)} images. The source material is a documented uniform display color. Joint anchors are calculated from pinned MB-Lab rig vertex groups and offsets. Blender BVH pass records first visible polygon and camera-depth grids locally. Hashes, transformations, seed references and camera records are in [manifest.json](q/manifest.json). Recorded camera distances and axes are metric. No experimental dataset row comes from personal photos.

Two generated photographic fixtures represent separate fictional adults and provide detector and fitting stress cases without calibrated mesh, camera or identity correspondence. Pilot scale was chosen to validate the native and calibrated experiments before larger coverage. There are no independent subject-family test folds, animated-pose series or calibrated garments in this pilot.
""".replace("Floor-normalized Y-up source geometry", "Floor-normalized source geometry"))
    report("GEOMETRY_CAPACITY_REPORT", "Q geometry capacity", f"""
{len(evals)} completed independent variant evaluations. Each estimate is conditional on the rig family, rest stance and common height/floor alignment. Error mixes morphology and residual rest-stance mismatch.

{table('Symmetric sampled surface error, height-aligned mm', distances)}

The JSON contains region means, Chamfer, P95 error, fitted controls and saturation. Height and first-visible surface validation are independent of the release. Section metrics include hip, waist and chest convex perimeter residuals. Volume and registered vertex RMSE were left unavailable for independent meshes. The historical seeded sensitivity run recovered control displacement and saturation within the same basis. Direct-fit step refinement measures optimizer sensitivity conditional on its nearest-sample objective. A persistent residual after the direct search is evidence of a limitation under the tested rest alignment and basis; the pilot cannot uniquely attribute it to geometry capacity.
""")
    report("PIPELINE_ABLATION_REPORT", "Q native pipeline and ablations", f"""
Native completed runs {len(success)}/{len(native)}. Fit objectives use detector evidence, while the table below uses independent evaluation masks on matched, fitted cameras and poses. An intervention may worsen a score when the native camera compensated for other errors.

{table('Matched evaluated silhouette IoU (%)', quartet, 100)}

Mask delta (percentage points) {effect(oracle_paired['mask_only'])}. Camera delta {effect(oracle_paired['camera_only'])}. Joint substitution delta {effect(oracle_paired['mask_and_camera'])}. Factorial interaction {effect(oracle_paired['interaction'])}.

Fixed-shape ground-truth limb-direction proxy substitution on frontal silhouettes {effect(pose_effect)} percentage points. Model limb lengths, torso and root translation are fixed. This measures the pose output under one calibrated camera and exposes remaining anatomy/rig error. It does not measure a complete full-body oracle.

Pose landmarks and orientation/visibility provider contracts are documented in the protocol. Unsupported independent geometry cannot be passed silently through the native UV/rig contracts. Explicit omissions are recorded in the final report.
""")
    report("MULTIVIEW_REPORT", "Q multi-view scaling", f"""
{table('Configuration, held-out silhouette IoU (%)', held, 100)}

{table('Calibrated fit wall time (s)', runtime)}

Paired held-out effects versus one frontal calibrated photograph, in percentage points.

""" + "\n".join(f"- {key} {effect(values)}" for key, values in paired.items()) + """

The two-view front/profile and front/rear treatments differ solely in the second orientation. Four includes both profiles, eight includes 45-degree increments. Held-out values average two unused cameras per variant. Native one/four rows report neutral shapes under the same held-out cameras and fixed alignment. Their detector-mask training scores cannot be compared directly with controlled IoU. Runtime includes concurrent scheduling noise. Contradictory, redundant and different-pose cases remain open.
""")
    report("PHOTOGRAPHIC_ROBUSTNESS_REPORT", "Q photographic robustness", f"""
Measured {sum(c[0] for c in photo_counts.values())} detector calls. Mask statistics use available detector masks and include low-visibility cases. Missing masks are counted in the separate detector totals.

{table('Perturbation, mask IoU (%)', photo_iou, 100)}

| Perturbation | Calls | Single candidate | Review or error |
|---|---:|---:|---:|
""" + "\n".join(f"| {k} | {v[0]} | {v[1]} | {v[2]} |" for k, v in photo_counts.items()) + """

The perspective rows vary focal length, camera distance and elevation with known Blender matrices. This arm measures detector segmentation robustness, without attributing improvements to camera reconstruction. The clutter and illumination gradient are deterministic pixel transforms. Crop and occlusion are measured against their documented mask conventions. Extra stress photographs are available only as local regenerable artifacts.

The two photorealistic AI inputs have separate reports in the JSON. These results are qualitative for 3D accuracy, including generated clothing and backgrounds. They do not establish independent mask IoU or garment shape accuracy.
""")
    report("COMPONENT_QUALITY_REPORT", "Q face, pose, texture and garment evidence", f"""
- Face: the independent surface measurements include a cranial band. The controlled jaw invariant yielded {metrics['face_control']} at input control 0.5. This local-deformation test cannot establish facial landmark accuracy.
- Pose: {len(pose)} variants with 12 rig endpoint/direction proxies each. Pose intervention effect {effect(pose_effect)} percentage points. Endpoint and direction errors are in the JSON. Different rig definitions limit positional interpretation, and no joint rotation truth was recorded.
- Skinning: {len(components)} reports with per-case maximum absolute bone-length change and calibrated units. Measurements check mechanical consistency and do not establish contact or torsion accuracy.
- Texture: UV fractions use the same release coverage definition. Coverage is a count of observed UV texels, without a color, seam, or contamination accuracy claim.
- Garments: three native close-fitted shell prototypes per completed component case. Reports retain signed minimum sampled clearances, violations, changed sample counts and maximum pose motion. Sampled signed distances do not bound all geometric triangle intersections.
- Export: OpenUSD parsed the native USDZ package and reported mesh and skeleton counts. Blender {platform.python_version()} Python host metadata are tracked separately. The host Blender build has no USD import operator. Official LTS archive fetch returned HTTP 403. No Blender edit/save/reopen verification is claimed.
""".replace(f"Blender {platform.python_version()} Python host metadata are tracked separately. ", ""))
    report("FAILURE_ATLAS", "Q Blender comparative renders and failure atlas", "\n".join(blends) + """

Rows use actual Workbench renders with matched orthographic framing, height alignment, studio shading and camera azimuth. Ground truth, native neutral, calibrated four-view neutral and bounded direct 3D fits are followed by a raster overlay. Cyan marks missed truth and orange marks predicted excess. The pilot presentations are neutral meshes; the residual includes stance and rig-family differences. Full wireframe, radiometric texture comparison, vertex heatmaps and garment-intersection visuals are not available.

Historical report reproduces a near-basis calibrated control case with 99.6724% held-out IoU. The independent fixture images reveal differences around arms, profile and torso under common alignment. Per-variant JSON permits selection by lowest held-out IoU and largest surface error, including cases outside this visual sample.
""")
    report("FINAL_BENCHMARK_REPORT", "Human3D v0.2.0 Q benchmark", f"""
{len(completed)}/43 tasks completed, {len(blocked)} blocked. {len(success)}/{len(native)} controlled native runs completed. {len(evals)} calibrated independent geometry sweeps, {len(ablations)} matched factorial sweeps, {len(pose)} independent pose diagnostics and {len(components)} structural component sweeps. Each calibrated geometry sweep covers six view configurations and two direct 3D search schedules.

Release CI jobs scan, classify, Linux foundation, Windows foundation and Required summary passed in [run 45869017319](https://github.com/egenovese-de/Human3D-2.0/actions/runs/45869017319). Local release tests 69/69. The existing calibrated Lab runner, unchanged, reproduced 99.6724% held-out IoU and 3.7899 mm vertex RMSE. The original stabilization report records 75.669% native fitting IoU and 90.128% observed UV coverage on the historical four-view fixture. Source reports are [M5](M5_FINAL_BENCHMARK.md) and [stabilization](https://github.com/egenovese-de/Human3D-2.0/blob/{RELEASE}/DOCS/STABILIZATION_CANDIDATE.md). The raw historical photographic fixture was not rerun here. Agreement to detector masks with image and pose estimation differs from a fit to exact masks formed mostly by the solver morph basis on matching topology. The 99.67%-versus-75.67% historical difference cannot be assigned to one component. Held-out independent pilot results and matched interventions bound the contributions under the published protocol.

{table('Native fit reported IoU (%)', {f'{n} photo(s)': [v['fit']['fitted_iou'] for k,v in success.items() if k.endswith(f'-{n}')] for n in (1,4)}, 100)}

{table('Observed UV coverage (%)', {f'{n} photo(s)': [v['observed_uv_fraction'] for k,v in success.items() if k.endswith(f'-{n}')] for n in (1,4)}, 100)}

{table('Native elapsed runtime (s)', {f'{n} photo(s)': [v['elapsed_seconds'] for k,v in perf.items() if k.endswith(f'-{n}')] for n in (1,4)})}

Initial release detector launch failed on a missing system GLES shared object. Provisioning the stock Debian library locally fixed the error. A wrapper attempt with absent GNU time and a single retry due to the Lab clean-tree guard are recorded separately. Native peak RAM and texture/export stage breakdown were unavailable in the legacy runner. Geometry evaluator peak RSS and native artifact sizes are recorded.

## Outstanding evidence

""" + "\n".join(f"- **{key}** {value}" for key, value in blocked.items()) +
        "\n\nMachine-readable [measurements](q/measurements.json) and [dataset hashes](q/manifest.json).")
    report("M6_RECOMMENDATIONS", "Q evidence-based M6 recommendations", f"""
| Priority | Component and measured limitation | Technical intervention | Complexity, dependencies and regression risk | Verification |
|---|---|---|---|---|
| P1 | Limb pose. True-direction proxy substitution at fixed shape changed frontal overlap by {effect(pose_effect)} percentage points. Relative direction estimation or mapping contributes to error under the pilot stance. | Add calibrated reference joint mapping and test pose confidence and limb depth jointly before algorithm changes. | Medium. Independent articulated benchmark and fixed 3D joints. Risk to wrists, relative depth and limbs behind the torso. | Paired neutral and articulated holdout with independent joint rotations and report angle, contact and silhouette separately. |
| P1 | Camera and mask coupling. Substitution effects in pp: mask {effect(oracle_paired['mask_only'])}, camera {effect(oracle_paired['camera_only'])}, interaction {effect(oracle_paired['interaction'])}. Camera error and compensating pose/shape are suspected controls. | Validate view calibration and separate segmentation confidence from camera quality before modifying the solver. | Medium. Depends on repeatable camera models and detector-bound evidence. Risk of worse heavily cropped cases. | Repeat the four-way factorial with perspective, view-angle coverage and held-out validation. |
| P2 | Geometry capacity. Direct-fit and calibrated surface errors are measured in the geometry table. Basis insufficiency is suspected where errors persist, confounded by root and stance alignment. Population improvement cannot be estimated from two topology families. | Establish an articulated registration oracle and expand independent rest-shape coverage before adding bounded regional controls. | High. Correspondence, rig rebinding, UV and garment deformation are dependencies. Existing proportions and support-plane behavior can regress. | Same alignment protocol and held-out subjects with registered joints plus calibration. Measure the change at fixed objective and fixed bounds. |
| P2 | View utility. Front/profile and front/rear held-out deltas {effect(paired['front-profile'])} and {effect(paired['front-rear'])} pp. Appearance coverage benefits from extra views. | Evaluate view quality weighting and redundant-view rejection before making more photographs the default. | Medium. Requires matched exposure, camera metadata and contradictory/duplicate fixture families. Risk of dropping genuinely complementary evidence. | Paired held-out usage and UV coverage, with marginal latency and failure-rate reporting. |

The ranges in this table are observed pilot variation. No P0 classification is supported by the completed controlled comparisons. No M6 work is implemented.
""")
    report("REPRODUCIBILITY_MANIFEST", "Q reproducibility manifest", f"""
- Release commit `{RELEASE}`. Initial Lab `{LAB_BASE}`. Latest experimental scripts source commit `{experiment_commit}`.
- Read upstream asset digests from the release manifests and obtain the documented Pose Landmarker Lite v1. The Lab records the verified bytes in [manifest.json](q/manifest.json).
- MB-Lab commit `063bff04e60f3e7c651fda628c30f5d83f3f3078`. Use its local `data/humanoid_library.blend` and joint JSON files. Blender 4.3.2. Linux {platform.release()}, Python {platform.python_version()}, {platform.machine()}, NumPy {np.__version__}.
- Use a CPython 3.11 virtual environment with `--require-hashes --no-deps -r <release>/requirements-linux.lock`. Supply libEGL, libGL and libGLESv2. The host retry used Debian libgles2 from its upstream package path with LD_LIBRARY_PATH pointing to a local extraction.
- Commit Lab scripts before running the unchanged historical and native runners. Set `PYTHONPATH=<release>/src:<lab>/tools` and `OPENBLAS_NUM_THREADS=1`. Set `QT_QPA_PLATFORM=offscreen` for unittest discovery in the release.
- Seed 2471 for photographic variants and 2473 for area sampling; no stochastic production settings changed. Both held-out orientations are explicit in each manifest. Use distinct empty destinations for the native benchmark and historical baselines.
- `render.py`, `depth.py`, `stress_cameras.py` and `comparison.py` run inside Blender with `-b -P script -- arguments`. For `stress_cameras.py`, add the Lab script directory to Blender's sys.path before loading. Use `--python-exit-code 1`. Other scripts provide arguments via `--help`, except `photographic.py`, `stress_photographs.py` and `validate.py` which take the pilot path positionally, and `validate.py` also takes the JSON output path.
- Recommended execution sequence: provision pinned runtime, run existing `benchmark_geometry.py --regional --carve --independent`, build metric Blender fixtures, composite opaque photographs, validate, run native one and four view manifests, run `evaluate.py` and `ablate.py`, run detector stress and components, and build the comparative raster atlas. Use `evaluate.py --metrics-only` to attach native equivalent shape measurements after the independent calibration jobs. Run this consolidation script with scratch root and Lab directory.
- [Raw measurement summaries](q/measurements.json) retain per-view outcomes, failed preflights, directional measurements, deformation checks and instrument output. No large assets are included.
""")
    return {"done": len(completed), "blocked": len(blocked), "native": len(native), "pilot": len(manifests),
            "eval": len(evals), "ablations": len(ablations), "detector": sum(c[0] for c in photo_counts.values()),
            "atlas": len(atlas)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--lab", type=Path, required=True)
    print(json.dumps(write_docs(**vars(parser.parse_args())), sort_keys=True))

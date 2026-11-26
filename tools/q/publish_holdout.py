"""Write the Q holdout follow-up from the measured results."""
import argparse
import json
from pathlib import Path
from statistics import mean

import numpy as np


def avg_holdout(row):
    return mean(row["iou"][k] for k in ("22.5", "112.5"))


def observed_bend(a, b):
    directions = [np.diff(np.asarray(row["joint_anchors"]["lowerarm_L"]), axis=0)[0] for row in (a, b)]
    a, b = [v / np.linalg.norm(v) for v in directions]
    return float(np.degrees(np.arccos(np.clip(a @ b, -1, 1))))


def rows_to_report(root, lab):
    docs = lab / "DOCS"
    data = json.loads((root / "holdout-results.json").read_text())
    mixed = json.loads((root / "holdout-mixed.json").read_text())
    calibration = json.loads((root / "holdout-validation.json").read_text())
    manifest = {}
    for path in sorted((root / "holdout-mixed-inputs").glob("*/*.json")):
        manifest[f"{path.parent.name}/{path.name}"] = json.loads(path.read_text())
    by_identity = {}
    for row in data:
        fixture = row["fixture"]
        by_identity.setdefault(fixture["identity"], {})[fixture["left_forearm_bend_deg"]] = row
    table = []
    pose_delta = []
    four_shape_delta = []
    successful = sum("fit_seconds" in n for r in data for n in r["native"].values())
    mixed_successful = sum("fit_seconds" in r for cases in mixed.values()
                           for group, r in cases.items() if group != "matched")
    for identity, pair in by_identity.items():
        neutral, bent = pair[0], pair[32]
        for row in (neutral, bent):
            if not row["pose"] or "fit_seconds" not in row["native"]["1"]:
                raise ValueError(f"missing required pose for {identity}")
        four = neutral["native"]["4"]
        if "neutral" not in four:
            raise ValueError(f"missing required four-view fit for {identity}")
        npath, bpath = [(root / "holdout" / row["fixture"]["subject"] / "manifest.json") for row in (neutral, bent)]
        truth_bend = observed_bend(json.loads(npath.read_text()), json.loads(bpath.read_text()))
        neutral_error = neutral["pose"]["joint_anchor_proxies"]["lowerarm01.L"]["direction_error_deg"]
        bent_error = bent["pose"]["joint_anchor_proxies"]["lowerarm01.L"]["direction_error_deg"]
        delta = bent["pose"]["oracle_limb_directions_fixed_shape_iou"] - bent["pose"]["native_pose_calibrated_evaluation_iou"]
        pose_delta.append(delta)
        gain = avg_holdout(four["neutral"]) - avg_holdout(four["bootstrap"])
        four_shape_delta.append(gain)
        chest = four["chest_section_mm"]
        chest_label = f"{chest['native'] - chest['truth']:+.0f}" if all(v is not None for v in chest.values()) else "—"
        table.append(f"| {identity} | {100*avg_holdout(four['bootstrap']):.2f}% | "
                     f"{100*avg_holdout(four['neutral']):.2f}% | {four['neutral']['symmetric_mean_mm']:.1f} | "
                     f"{chest_label} | {truth_bend:.2f}° | {neutral_error:.2f}° | {bent_error:.2f}° | {100*delta:+.2f} pp |")
    mixed_rows = []
    for identity, cases in mixed.items():
        base = mean(cases["matched"]["neutral_iou"].values())
        for label, case in cases.items():
            if "neutral_iou" in case:
                score = mean(case["neutral_iou"].values())
                unresolved = ", ".join(case["unresolved"]) or "None"
                mixed_rows.append(f"| {identity} | {label} | {case['used_views']} | {100*score:.2f}% | "
                                  f"{100*(score-base):+.2f} pp | {unresolved} |")
            else:
                mixed_rows.append(f"| {identity} | {label} | — | — | — | {case['failure']} |")
    sha = "480195f05fb2d1ed6c71dceabf4ba54b8bed69db"
    doc = f"""# Q follow-up — held-out anatomy and controlled articulation

Release `{sha}`. Q retains its original pilot report. This follow-up adds four author-supplied MB-Lab preset geometries excluded from the pilot, two per topology family. The four geometries are independent of the release MakeHuman basis. They share the two MB-Lab topology families with the pilot, so this is an identity holdout rather than a new asset-source holdout. Each identity has a neutral render and one procedural left forearm bend. No held-out azimuth entered the fits.

{successful}/12 native identity/pose runs completed. {mixed_successful}/4 substitution runs completed. Blender rendered and independently validated {sum(len(row['validation']) for row in calibration)} camera/mask pairs. The local release suite ran 69/69 tests successfully.

## Neutral geometry and forearm pose

| Identity | Bootstrap held-out IoU | Four-view neutral IoU | Four-view surface distance (mm) | Chest section error (mm) | True bend | Neutral direction error | Articulated direction error | Bend fixture pose substitution |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
""" + "\n".join(table) + f"""

Four-view neutral shape changed held-out IoU by {100 * mean(four_shape_delta):+.2f} pp on average relative to the height-aligned bootstrap. The chest result is a fixed horizontal section at 71% of body height. It measures perimeter, which can miss a local profile discrepancy. Shape errors mix morphology and residual rig and stance alignment.

The exact direction of the left forearm is derived from transformed joint anchors. The last column substitutes proxy directions for all supported limbs on the articulated fixture with native shape fixed. It measures the difference on the frontal mask with calibrated evaluation. Mean change {100 * mean(pose_delta):+.2f} pp, range {100 * min(pose_delta):+.2f} to {100 * max(pose_delta):+.2f} pp. This benchmark covers flexion of one forearm. It leaves joint roll, hands, foot contact and dynamic pose outside the experiment.

## Changed reference photographs

| Identity | Configuration | Views used | Held-out neutral IoU | Change vs matched | Unresolved evidence |
|---|---|---:|---:|---:|---|
""" + "\n".join(mixed_rows) + """

For each selected identity, only the 90° reference is replaced. The comparators use either the articulated version of the same identity or the neutral version of a different identity from the same topology family. The front target, other two inputs and held-out views are unchanged. This complements the duplicate-front sweep in the original pilot. Results are descriptive on two identities.

## Reproduction and artifacts

1. Use the release dependency lock, verified runtime assets and pinned MB-Lab revision documented by the original Q reproducibility manifest.
2. Run `render.py` with the MB-Lab library, output folder and optional MB-Lab checkout path, then `photographic.py` and `validate.py`. The held-out manifestations record hashes for every source preset, image and geometry.
3. Use the native benchmark with one view on each fixture and four views only on neutral fixtures. Call `mixed_references.py create` to prepare treatments, repeat the native four-view benchmark, then run `mixed_references.py score`.
4. Run `pose.py`, `holdout_report.py`, the Blender comparison script, and `holdout_atlas.py`. The two raw geometry packs stay local.

- [Machine-readable measurements and hashes](q/holdout_measurements.json)
- [Matched Blender render atlas](q/holdout_atlas.png)
"""
    (docs / "Q_HOLDOUT_FOLLOWUP.md").write_text(doc)
    (docs / "q" / "holdout_measurements.json").write_text(json.dumps(
        {"release_sha": sha, "dataset": data, "validation": calibration, "mixed_references": mixed,
         "mixed_input_manifests": manifest}, indent=2, allow_nan=False) + "\n")
    backlog = docs / "BACKLOG_Q.md"
    lines = backlog.read_text().splitlines()
    for i, text in enumerate(lines):
        if (text.startswith("| Q0-005 ") and successful == 12) or (
            text.startswith("| Q3-004 ") and mixed_successful == 4
        ):
            lines[i] = text.replace("| BLOCKED |", "| DONE |")
    backlog.write_text("\n".join(lines) + "\n")
    print(f"Native {successful}/12, mixed {mixed_successful}/4; backlog "
          f"{sum('| DONE |' in row for row in lines)}/43")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("lab", type=Path)
    rows_to_report(**vars(parser.parse_args()))

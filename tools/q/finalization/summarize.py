"""Compute auditable finalization aggregates from the retained raw records."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
from statistics import mean, median


def summarize(path):
    def data(name):
        source = path / f"{name}.json"
        if source.exists():
            return json.loads(source.read_text())
        return json.loads(gzip.decompress(source.with_suffix(".json.gz").read_bytes()))

    rig = data("rig-landmarks")
    landmarks = [anchor for row in rig for view in row["views"] for anchor in view["anchors"]]
    ious = [v["silhouette_iou"] for row in rig for v in row["views"]
            if isinstance(v["silhouette_iou"].get("native"), float)
            and isinstance(v["silhouette_iou"].get("joint_proxy_xy"), float)]
    face = data("face-anchors")
    face_errors = [row["detector_to_pick_px"] for row in face if row["detector_to_pick_px"] is not None]
    garment = data("garment-pose")
    caps = [cap for row in garment for cap in row["caps"].values()]
    references = data("references")
    reference_sets = data("reference-sets")
    screening = data("fit-screen")["screening"]
    valid = [r for r in screening if "error" not in r]
    effect = lambda r: r["fitted_neutral_surface_mm"] - r["bootstrap_neutral_surface_mm"]

    def confusion(rows):
        return {f"{label}_{'accept' if accept else 'reject'}": sum(
            row["effect"] == label and row["accepted"] == accept for row in rows)
                for label in ("beneficial", "harmful", "tie") for accept in (True, False)}

    def conditions(name):
        result = {}
        for row in data(name):
            for cell in row["cells"]:
                condition = "/".join([cell["camera"], cell["pose"], cell["shape"]])
                iou = mean(v for k, v in cell["fixed_camera_iou"].items() if float(k) != 0)
                result.setdefault(condition, []).append((iou, cell["symmetric_mean_mm"]))
        return {key: dict(count=len(values), held_out_iou=mean(x[0] for x in values),
                          posed_surface_mm=mean(x[1] for x in values)) for key, values in result.items()}

    assert len(landmarks) == 576 and len(face) == 26
    assert len(caps) == 24 and len(screening) == 8 and len(reference_sets) == 16
    assert len(data("transfer-with-native")) == len(data("factorial")) == len(data("upstream")) == 4
    assert len(data("evidence")) == 16 and len(references) == 14 and len(data("garment")) == 18
    return {
        "release_commit": "480195f05fb2d1ed6c71dceabf4ba54b8bed69db",
        "lab_parent": "9cc1552b201d55e97eacbb1959b009e139ae85d8",
        "backlog": {"done": 39, "blocked": 9},
        "readiness": "CONDITIONALLY_READY_FOR_M6_PLANNING",
        "landmark_proxies": {"fixtures": len(rig), "views": len(ious), "anchors": len(landmarks),
                             "native_iou": mean(r["native"] for r in ious),
                             "proxy_iou": mean(r["joint_proxy_xy"] for r in ious),
                             "roundtrip_max_m": max(r["projection_roundtrip_m"] for r in landmarks),
                             "rig_chain_residual": max(b["parent_chain_max_abs_residual"]
                                                       for r in rig for b in r["rig"].values())},
        "face": {"picks": len(face), "surface_hits": sum(r["xyz_m"] is not None for r in face),
                 "matched_detector_count": len(face_errors), "min_detector_difference_px": min(face_errors),
                 "max_detector_difference_px": max(face_errors)},
        "factorial": conditions("factorial"),
        "raster_mask_oracle": conditions("upstream"),
        "garment": {"posed_shell_conditions": len(garment), "cap_screens": len(caps),
                    "cap_screen_passes": sum(r["cap_screen_pass"] for r in caps),
                    "false_clear_counts": Counter(r["triangle_pairs"] for r in garment
                                                  if r["sampled_violations"] == 0 and r["triangle_pairs"] > 0)},
        "motion_fit_screen": {
            "screened": len(screening), "scored": len(valid), "confusion_by_held_out_iou": confusion(valid),
            "mean_bootstrap_iou": mean(r["bootstrap_iou"] for r in valid),
            "mean_fitted_iou": mean(r["fitted_iou"] for r in valid),
            "mean_selected_iou": mean(r["selected_iou"] for r in valid),
            "mean_bootstrap_neutral_surface_mm": mean(r["bootstrap_neutral_surface_mm"] for r in valid),
            "mean_fitted_neutral_surface_mm": mean(r["fitted_neutral_surface_mm"] for r in valid),
            "mean_selected_neutral_surface_mm": mean(r["selected_neutral_surface_mm"] for r in valid),
            "min_neutral_surface_delta_mm": min(map(effect, valid)),
            "max_neutral_surface_delta_mm": max(map(effect, valid)),
            "iou_beneficial_but_surface_worse": sum(r["effect"] == "beneficial" and effect(r) > 0 for r in valid),
            "median_rule_overhead_seconds": median(r["overhead_seconds"] for r in valid),
        },
        "neutral_evaluation_confusion_by_held_out_iou": confusion(data("acceptance")["evaluation"]),
        "references": {"cases": len(references),
                       "invalid_cases": sum(r["reject_identity_ground_truth"] for r in references),
                       "invalid_geometry_accepted": sum(r["reject_identity_ground_truth"] and r["geometry_policy_accept"]
                                                        for r in references),
                       "invalid_appearance_accepted": sum(r["reject_identity_ground_truth"] and r["appearance_policy_accept"]
                                                          for r in references),
                       "bake_conditions": len(reference_sets),
                       "mean_uv_with_profile": mean(r["observed_uv_fraction"] for r in reference_sets
                                                    if r["appearance_set"] == "all"),
                       "mean_uv_profile_omitted": mean(r["observed_uv_fraction"] for r in reference_sets
                                                       if r["appearance_set"] == "omit_profile")},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("measurements", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(summarize(args.measurements), indent=2, allow_nan=False) + "\n")

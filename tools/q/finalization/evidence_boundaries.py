"""Probe v1 boundary behavior through release types."""
from dataclasses import dataclass, replace
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from human3d.anatomical_evidence import (
    AnatomicalEvidence, EvidenceAdapter, RegionVisibility, apply_visibility, yaw_conflicts,
)
from human3d.vision import Landmark


@dataclass(frozen=True)
class Detection:
    candidates: tuple
    anatomical: AnatomicalEvidence | None = None


def main(output):
    baseline = AnatomicalEvidence("fixture", "lab", "boundary-test", 0, yaw=0, yaw_confidence=.8)
    yaw = [
        {"provider_deg": provider, "detector_deg": detector, "confidence": confidence,
         "conflict": yaw_conflicts(replace(baseline, yaw=provider, yaw_confidence=confidence), detector)}
        for provider, detector in ((45, 0), (45.001, 0), (-179, 179), (90, None))
        for confidence in (.799, .8, 1)
    ]
    pose = (Landmark(.5, .5, 1, 1),) * 33
    visibility = []
    for confidence in (.799, .8, 1):
        for visible in (False, True):
            evidence = replace(baseline, regions=(RegionVisibility("left_arm", visible, confidence),))
            result = apply_visibility(pose, evidence)
            visibility.append({"confidence": confidence, "provider_visible": visible,
                               "suppressed_indices": [i for i, point in enumerate(result) if not point.observed]})
    binding = []
    for candidates in (0, 1, 2):
        for digest, candidate in (("fixture", 0), ("other", 0), ("fixture", 1)):
            native = Detection((pose,) * candidates)
            detector = SimpleNamespace(detect=lambda *_: native)
            provider = SimpleNamespace(observe=lambda *_: replace(baseline, photo_digest=digest, candidate=candidate))
            bound = EvidenceAdapter(detector, provider).detect(Path("fixture.png"), "fixture")
            binding.append({"candidates": candidates, "digest_matches": digest == "fixture",
                            "candidate_index": candidate, "attached": bound.anatomical is not None})
    assert sum(row["attached"] for row in binding) == 1
    assert [len(row["suppressed_indices"]) for row in visibility] == [0, 0, 5, 0, 5, 0]
    assert [row["conflict"] for row in yaw] == [False] * 4 + [True] * 2 + [False] * 6
    output.write_text(json.dumps({"binding": binding, "visibility": visibility, "yaw": yaw}, indent=2) + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]))

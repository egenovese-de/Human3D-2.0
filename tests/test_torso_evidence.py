from dataclasses import replace
from types import SimpleNamespace
import unittest

import numpy as np

from human3d.anatomical_evidence import QuantitativeObservation
from human3d.torso_evidence import torso_ratio_penalty


class TorsoEvidenceTests(unittest.TestCase):
    def fixture(self):
        corners = np.array([[-1., -1.], [1., -1.], [1., 1.], [-1., 1.]])
        vertices = [[x, y, z] for y in (0., 6.1, 7.1, 10.) for x, z in corners]
        faces = []
        for row in range(3):
            for i in range(4):
                j = (i + 1) % 4
                indices = [row * 4 + i, row * 4 + j, (row + 1) * 4 + j, (row + 1) * 4 + i]
                faces.append({"group": "body", "corners": [(k, k) for k in indices]})
        return {"mesh": {"vertices": vertices, "faces": faces}}

    def test_chest_change_reduces_penalty_and_duplicate_does_not_amplify_it(self):
        body = self.fixture()
        value = QuantitativeObservation("a" * 64, 0, "torso", "circumference",
                                        "torso.chest_to_waist_circumference@v1", "subject_local",
                                        "ratio", "calibrated-analytic", value=1.2,
                                        uncertainty=.01, visibility=1.)
        view = SimpleNamespace(ref=SimpleNamespace(photo_id="photo"), candidate=0, observed_regions=("torso",),
                               detection=SimpleNamespace(anatomical=SimpleNamespace(candidate=0, observations=(value,))))
        evidence = SimpleNamespace(views=(view,), unresolved=())
        penalty = torso_ratio_penalty(body, evidence, {"photo"})
        base = np.asarray(body["mesh"]["vertices"])
        chest = base.copy()
        chest[8:12, (0, 2)] *= 1.2
        self.assertGreater(penalty(base), 0)
        self.assertAlmostEqual(penalty(chest), 0.)
        view.detection.anatomical.observations = (value, value)
        self.assertEqual(torso_ratio_penalty(body, evidence, {"photo"})(base), penalty(base))
        view.detection.anatomical.observations = (value, replace(value, value=.8))
        self.assertIsNone(torso_ratio_penalty(body, evidence, {"photo"}))

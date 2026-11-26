import json
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from human3d.anatomical_evidence import AnatomicalEvidence, QuantitativeObservation
from human3d.observations import ObservationRef, ObservationStore
from human3d.vision import Landmark, SubjectEvidence


PHOTO_DIGEST = "a" * 64


class AnatomicalEvidenceV2Tests(unittest.TestCase):
    def observation(self):
        return QuantitativeObservation(PHOTO_DIGEST, 0, "torso", "proportion", "torso.depth_to_width@v1",
                                       "subject_local", "ratio", "fixture", interval=(.5, .65), uncertainty=.03)

    def test_roundtrip_preserves_typed_interval_and_photo_binding(self):
        field = self.observation()
        record = AnatomicalEvidence(PHOTO_DIGEST, "fixture", "model", 0, schema_version=2, observations=(field,))
        self.assertEqual(AnatomicalEvidence.from_record(json.loads(json.dumps(asdict(record)))), record)
        with self.assertRaisesRegex(ValueError, "provider_evidence_binding_mismatch"):
            replace(record, observations=(replace(field, candidate=1),))

    def test_metric_requires_traceable_scale_and_uncertainty(self):
        field = self.observation()
        with self.assertRaisesRegex(ValueError, "metric_evidence_requires_calibration"):
            replace(field, kind="circumference", units="m")
        metric = replace(field, kind="circumference", units="m", calibration_ref="independent-calibration")
        self.assertEqual(metric.calibration_ref, "independent-calibration")
        with self.assertRaisesRegex(ValueError, "metric_evidence_requires_calibration"):
            replace(metric, uncertainty=0)
        with self.assertRaisesRegex(ValueError, "invalid_quantitative_value"):
            replace(field, interval=(float("nan"), .6))
        with self.assertRaisesRegex(ValueError, "invalid_quantitative_range"):
            replace(field, interval=(-.2, .6))

    def test_v1_storage_bytes_remain_compatible_and_upgrade_is_opt_in(self):
        old = {"photo_digest": PHOTO_DIGEST, "provider": "fixture", "model": "legacy", "candidate": 0}
        legacy = AnatomicalEvidence.from_record(old)
        upgraded = legacy.as_v2()
        self.assertEqual(legacy.schema_version, 1)
        self.assertEqual(upgraded.schema_version, 2)
        self.assertEqual(upgraded.observations, ())
        detection = SubjectEvidence(PHOTO_DIGEST, "b" * 64, (40, 80),
                                    ((Landmark(.5, .5, 1., 1.),) * 33,), anatomical=legacy)
        with TemporaryDirectory() as temp:
            store = ObservationStore(Path(temp))
            digest = store.write_detection(detection)
            payload = store._read(digest, "subject_detection")
            self.assertNotIn("observations", payload["anatomical"])
            self.assertEqual(store.read_detection(ObservationRef("photo", PHOTO_DIGEST, digest)), detection)
            new = replace(detection, anatomical=replace(upgraded, observations=(self.observation(),)))
            new_digest = store.write_detection(new)
            self.assertNotEqual(new_digest, digest)
            self.assertEqual(store.read_detection(ObservationRef("photo", PHOTO_DIGEST, new_digest)), new)

    def test_supported_visibility_caps_detector_evidence_and_conflicts_fall_back(self):
        from human3d.anatomical_evidence import apply_visibility

        cap = replace(self.observation(), region="left_arm", kind="visibility",
                      definition="regional.landmark_visibility_cap@v1", frame="photo", units="fraction",
                      interval=(.4, .5), uncertainty=.05)
        native = (Landmark(.5, .5, .95, .99),) * 33
        evidence = AnatomicalEvidence(PHOTO_DIGEST, "fixture", "model", 0, schema_version=2,
                                      observations=(cap, self.observation()))
        adapted = apply_visibility(native, evidence)
        self.assertEqual(adapted[13].visibility, .55)
        self.assertFalse(adapted[13].observed)
        self.assertEqual(adapted[14], native[14])
        self.assertEqual(apply_visibility(native, replace(evidence, observations=(cap, cap))), adapted)
        conflict = replace(cap, interval=(.8, .9))
        self.assertEqual(apply_visibility(native, replace(evidence, observations=(cap, conflict))), native)
        high = replace(cap, interval=(.95, 1.))
        self.assertEqual(apply_visibility(native, replace(evidence, observations=(high,))), native)

    def test_arm_ratio_penalty_has_known_geometry_effect_and_conservative_fusion(self):
        from types import SimpleNamespace

        from human3d.proportions import forearm_ratio_penalty

        def view(records):
            supplied = AnatomicalEvidence(PHOTO_DIGEST, "fixture", "model", 0, schema_version=2,
                                          observations=records)
            return SimpleNamespace(candidate=0, detection=SimpleNamespace(anatomical=supplied),
                                   ref=SimpleNamespace(photo_id="fixture"), observed_regions=("left_arm",))

        def model(*photos):
            return forearm_ratio_penalty(body, SimpleNamespace(views=photos, unresolved=()), {"fixture"})

        bones = ("upperarm01.L", "lowerarm01.L", "wrist.L")
        body = {"rig": {"bones": {bone: {"head": bone} for bone in bones},
                        "joint_vertices": {bone: [i] for i, bone in enumerate(bones)}}}
        field = replace(self.observation(), region="left_arm", definition="arm.forearm_to_upperarm@v1",
                        interval=None, value=.75, visibility=.95, uncertainty=.01)
        in_range = [[0, 0, 0], [0, 0, 2], [0, 0, 3.5]]
        out_of_range = [[0, 0, 0], [0, 0, 2], [0, 0, 3.]]
        penalty = model(view((field,)))
        self.assertEqual(penalty(in_range), 0.)
        self.assertGreater(penalty(out_of_range), 0.)
        self.assertEqual(model(view((field, field)))(out_of_range), penalty(out_of_range))
        self.assertIsNone(model(view((replace(field, visibility=.7),))))
        self.assertIsNone(model(view((field,)), view((replace(field, value=1.1, source_family="other"),))))

        from unittest.mock import patch

        from human3d.fitting import _optimize

        def deform(_body, controls):
            length = 3. + 2 * controls.get("forearm_length", 0.)
            return [[0, 0, 0], [0, 0, 2], [0, 0, length]]

        with patch("human3d.fitting.deform_vertices", side_effect=deform), patch("human3d.fitting.validate_rebind"):
            score = lambda _vertices: {"fixture": .9}
            kwargs = dict(controls={}, supported=("forearm_length",), steps=(.25,))
            self.assertEqual(_optimize(body, score, **kwargs)[0], {})
            self.assertEqual(_optimize(body, score, **kwargs, measurement_penalty=penalty)[0],
                             {"forearm_length": .25})

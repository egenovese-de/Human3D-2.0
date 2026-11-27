import unittest

import numpy as np

from human3d.texture_bake import _projection_diagnostics


class ProjectionDiagnosticsTests(unittest.TestCase):
    def test_contour_distance_uses_source_pixel_units(self):
        mask = np.zeros((64, 64), dtype=bool)
        mask[16:48, 16:48] = True
        rows = [_projection_diagnostics(np.roll(mask, shift, axis=1), mask, (128, 64), .75)
                for shift in (0, 1, 3)]
        self.assertEqual([row.contour_p95_source_px for row in rows], [0., 2., 6.])
        self.assertEqual(rows[0].silhouette_iou, 1.)
        self.assertGreater(rows[1].silhouette_iou, rows[2].silhouette_iou)
        self.assertEqual(rows[2].observed_uv_fraction, .75)

    def test_empty_projection_has_no_contour_measurement(self):
        mask = np.ones((64, 64), dtype=bool)
        result = _projection_diagnostics(np.zeros_like(mask), mask, (64, 64), 0.)
        self.assertEqual(result.silhouette_iou, 0.)
        self.assertEqual(result.unprojected_foreground_fraction, 1.)
        self.assertIsNone(result.contour_p95_source_px)

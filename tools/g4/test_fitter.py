from dataclasses import replace
import unittest
import numpy as np

from evidence import State
from fitter import AnatomicalFitter, ImageLoss, RegisteredView, admitted
from projection import Camera


def view(key='v',source='calibrated',outer=None,excluded=None):
    mask=np.zeros((24,24),bool)
    mask[5:19,8:15]=True
    states=np.where(mask,State.FOREGROUND,State.BACKGROUND)
    if excluded is not None:
        states[excluded]=State.UNOBSERVED
    return RegisteredView(key,Camera(0),mask,states,np.ones(mask.shape),source,'unknown_relative',
                          outer_only=outer)


class FitContracts(unittest.TestCase):
    def test_reject_unresolved_and_deduplicate(self):
        accepted,removed=admitted([view('c'),view('b','automatic'),view('a')])
        self.assertEqual([v.key for v in accepted],['a'])
        self.assertEqual(removed,{'b':'unresolved_orientation','c':'duplicate_observation'})

    def test_entirely_unresolved_abstains_without_raster(self):
        canonical,result=AnatomicalFitter(None,None,None).fit([view(source='automatic')])
        self.assertIsNone(canonical)
        self.assertEqual(result['reason'],'no_resolved_observation')

    def test_unknown_pixels_do_not_penalize_iou(self):
        ignore=np.zeros((24,24),bool)
        ignore[10:14,8:15]=True
        instance=view(excluded=ignore)
        proposal=instance.mask.copy()
        proposal[ignore]=False
        self.assertEqual(ImageLoss(instance,24)(proposal,'iou'),0.)

    def test_outer_envelope_is_asymmetric(self):
        garment=np.zeros((24,24),bool)
        garment[8:16,7:16]=True
        instance=view(outer=garment)
        shrink=instance.mask.copy()
        shrink[garment]=False
        extended=instance.mask|garment
        loss=ImageLoss(instance,24)
        self.assertEqual(loss(shrink,'iou'),0.)
        self.assertGreater(loss(extended,'iou'),0.)

    def test_invalid_evidence_shapes_and_finite_values(self):
        seed=view()
        with self.assertRaises(ValueError):
            replace(seed,confidence=np.ones((10,10)))
        with self.assertRaises(ValueError):
            replace(seed,registration_sigma_px=float('nan'))


if __name__=='__main__':
    unittest.main()

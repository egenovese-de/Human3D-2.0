# Camera, pose and shape interactions

Four articulated preset identities each contributed all eight camera × direction × shape cells. Independent evaluation uses the same calibrated camera, fixed bootstrap height alignment and the same two held-out azimuths per subject. Camera and pose are applied in the one-view fitting objective. Fit starts from bootstrap and uses the same bounded coordinate steps in every cell. The direction substitute uses known source segments projected into the fitting camera plus a matched depth ratio. The native camera condition reuses the saved release camera.

| Camera | Pose | Shape | Frontal IoU | Held-out IoU | Symmetric surface error |
|---|---|---|---:|---:|---:|
| Native | Native | Bootstrap | 58.9% | 61.8% | 37.00 mm |
| Native | Native | Fitted | 57.1% | 60.7% | 38.89 mm |
| Native | Reference directions | Bootstrap | 62.9% | 68.8% | 23.50 mm |
| Native | Reference directions | Fitted | 64.9% | 68.9% | 23.43 mm |
| Calibrated | Native | Bootstrap | 57.0% | 62.0% | 31.93 mm |
| Calibrated | Native | Fitted | 54.7% | 60.1% | 34.34 mm |
| Calibrated | Reference directions | Bootstrap | 62.9% | 68.8% | 23.50 mm |
| Calibrated | Reference directions | Fitted | 59.5% | 66.3% | 26.03 mm |

The largest recurring gain is the intervention on segment directions. Under calibrated directions, changing the fitting camera changes the sign of the mean fitted-versus-bootstrap surface effect. With the native camera the difference is −0.07 mm. With the calibrated camera it is +2.53 mm. A more accurate camera still allows fitting to trade shape against residual upstream mismatch. The two identical reference-direction bootstrap rows are expected because the world direction is encoded consistently and the evaluation camera is fixed. Results favor validating pose before optimizing anatomy. They do not establish the effect of full rotations or a release redesign.

[Factorial rows and timings](q/followup/factorial.json) · [Articulated independent rig results](q/followup/rig.json) · [Comparative Blender atlas](q/followup/articulation-atlas.png)

A second alternating camera/shape pass with fixed native pose across the same four subjects changed mean held-out IoU from 60.7% to 60.5% and surface error from 38.88 to 39.11 mm. This sampled schedule did not improve the evaluation. Releasing the entire joint pose space would require an independent transform mapping beyond the tested segment directions.

[Alternating schedule results](q/followup/alternating.json) · [Calibrated mask + camera + direction subset](q/followup/upstream-partial.json)

In the calibrated camera cells, replacing only the native mask with the raster mask changed mean symmetric error by −0.11 mm with native pose and +0.08 mm with reference directions. Relative to those two individual outcomes, the estimated mask × direction interaction on the fitted shape is +0.18 mm. This four-subject subset quantifies one upstream interaction and retains the landmark and evidence-validation gaps.

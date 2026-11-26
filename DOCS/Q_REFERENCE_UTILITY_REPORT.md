# Reference consistency and utility

Two fixed neutral identities contributed seven reference treatments each. The tested policies use a single candidate, yaw novelty and two landmark-confidence counts. Each accepted 12/14 references, including every similar or strongly inconsistent other-identity treatment (4/4). Both rejected the two redundant valid references. Same-person changed pose, clothing and occlusion still passed these conditions. This is a direct negative test of yaw/visibility as an identity check. Pose novelty and identity compatibility require separate observations.

The historical matched reference experiment records two identity substitutions and two same-identity pose substitutions with neutral held-out IoU. The relative change ranged from −0.46 pp to +3.15 pp for different identities, and −0.27 pp to +3.15 pp for changed pose. The calibrated texture control independently shows why appearance benefits can persist when geometry utility is low. Adding a rear view increased observed UV coverage from 44.46% to 78.98% at nearly unchanged visible frontal color error. It also changes which surfaces are eligible for direct sampling.

A single ranking policy has not been validated against held-out geometry, pose and texture on the same treatment set. Geometry and appearance thresholds above remain experimental diagnostics.

[Reference cases](q/followup/references.json) · [Original mixed-reference measurements](q/holdout_measurements.json) · [Calibrated color and coverage](q/followup/texture.json)

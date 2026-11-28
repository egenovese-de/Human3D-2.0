# G6 · Experimental method

The 6 MakeHuman and 4 MB-Lab references reuse the G4/G5 family identities and the existing development/held-out split. Coordinates are the G5 fixed centimetre frame with Y up, frontal positive Z and fixed scale and floor. Optimization never performs candidate-specific evaluation alignment. Family C was reviewed for admission and is absent.

Direct fitting uses sampled surface correspondences and robust residuals. Same-topology known vertex correspondences are tested as a separate oracle. Geometry is evaluated in Blender using two independent seeded 12,000-sample area-weighted sets against actual closest triangles, with symmetric mean, median, RMS, P95, maximum and directional coverage. Constrained geometry is screened against M7 before final scoring. Historical candidates R0_D9, R0_long and R0_restart are logged with observed defects for comparability.

The fixed methods evaluate five deformation families after a shared R0_long initialization. R1 starts from the R0_long controls using a G1 dependency evaluator. Reciprocal coverage uses sampled-point matches in the optimizer. The final distance uses closest triangles. Fixed regularizers, displacement limits, solver budget contrasts and stress settings are recorded in code and configuration. No held-out fitting score selected a different hyperparameter for an individual subject.

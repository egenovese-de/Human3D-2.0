# Clothing, visibility and observation pose

| Known controlled condition | Mean symmetric error mm |
| --- | --- |
| body_control | 2.24 |
| loose_as_body | 9.00 |
| loose_outer_bound | 6.33 |
| pose_mismatch | 2.69 |
| pose_calibrated | 1.92 |

The clothing experiment uses 1.2 cm and 5.5 cm regional outer-envelope offsets, with a soft exclusion constraint in the loose case. It measures anatomy distortion due to a garment-like envelope. It does not simulate fabrics, clothing segmentation, drape, asymmetrical accessories or texture. The pose pair uses the same anatomy with an independent arm transform. Candidate controls are evaluated on canonical meshes. The photographic occluder is separately injected into the RGB image. Its known coverage is used only in the oracle-annotation ablation. Compare `occlusion_unmasked` and `occlusion_oracle_state` against E4 in the per-case results. Covered contours can offer soft upper bounds. A truly visible skin boundary carries both foreground and neighboring background information. Hair, loose garments and accessories should receive class-specific weighting once those classes can be established.

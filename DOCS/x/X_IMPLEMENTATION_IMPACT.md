# Human3D 2.0 implementation impact

| Component | Reuse | Additional work required for production |
|---|---|---|
| Evidence provenance | Existing observation identifiers, visibility, immutable hashes and project revisions | Versioned adapter for projected extents, viewpoint calibration and uncertainty |
| MakeHuman initialization | Pinned target manifests, native mesh and skinning | Anatomical control regularization, adverse-subject tests and proven regional safety |
| Regional deformation | Native deformation and joint rebinding | Local support, constraints and structural diagnosis under natural evidence |
| Pose interaction | Existing pose transformations and skinning | Map edits to the canonical body and reevaluate rig changes |
| Persistence/export | Frozen body loader and USDZ writer | Define regeneration rules for pose, texture and garments when the body digest changes |
| Recognition | Replay prompt and schema contracts | Independent image-conditioned evaluation and reviewed training data before distillation |

P3/P4 add Lab-only scripts, synthetic fixtures, workflow evidence and documentation. The production pipeline remains a separate implementation decision. External vision inference and model training are outside this implementation.

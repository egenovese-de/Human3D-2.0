# M1 redistribution and security clearance

Status: IN_PROGRESS. Default deny; no legacy component is cleared for copying by this document alone.

Original code: Apache-2.0, owner approved 2026-11-25.
Legacy inventory: 1063 tracked files; no history migration.

| Component | Disposition | Evidence / remaining gate |
|---|---|---|
| Original application modules | HOLD | Per-file authorship, dependency, secret and private-data review |
| MakeHuman v1.3.0 mesh and morph assets | HOLD | Legacy provenance declares CC0; verify upstream terms and exact hashes before acquisition |
| MakeHuman rig and weights | HOLD | Legacy provenance declares CC0; verify upstream terms and exact hashes |
| MakeHuman AGPL source | EXCLUDED | No vendoring |
| MediaPipe model assets | HOLD | Verify model-specific terms and digest |
| Other model weights and mesh bundles | EXCLUDED pending review | No implicit license inheritance |
| Legacy photographs and derivatives | EXCLUDED | Private local evaluation only |
| Legacy history, workflows and configuration | EXCLUDED by default | Recreate independently |
| New synthetic fixtures | Eligible after review | Procedural, no personal data, documented generator and license |

## Public admission rule
For every imported component record origin, immutable revision, path, digest, license, attribution, modification and reviewer disposition. Review content for secrets, personal data and incompatible code before any public write. Unknown provenance means deny. External assets are acquired from verified upstream rather than copied from private history where feasible. No private photos, derived human assets, credentials or local project data in CI, logs or artifacts.

## Outstanding
Upstream license and hash verification, individual module review, public repository scan, fixture manifest and validation evidence. No clearance PASS claimed.

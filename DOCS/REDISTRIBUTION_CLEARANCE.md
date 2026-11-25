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

## Upstream evidence
MakeHuman v1.3.0 LICENSE.ASSETS.md retrieved from https://raw.githubusercontent.com/makehumancommunity/makehuman/v1.3.0/LICENSE.ASSETS.md and inspected: CC0 1.0 Universal text. This confirms the upstream asset license document exists, not that every candidate file is covered or hash-verified. Acquisition remains on HOLD until exact file scope and digests are validated.

## Asset identity verification
Upstream immutable commit: 1f508f6083b2f823dab15de924b3bde72e08d77c. Legacy reference commit: e33c396ed7b17fd5503a8e2b9c9f137179f364bf. Compared Git blob identities for every legacy assets/makehuman/data/ file against the corresponding upstream makehuman/data/ path: 357/357 match, zero mismatches. Upstream LICENSE.md section C confirms CC0 for bundled graphical assets, including base mesh and targets; section B separately licenses program logic under AGPL. Git blob identity is not an independent SHA-256 verification. Runtime acquisition must verify expected SHA-256 before use. No asset bytes transferred. Prefer upstream acquisition at immutable revision; retain CC0 notice and attribution. Other asset directories remain excluded.

## Incremental admission register
All legacy source remains HOLD. Reviewed candidates: frozen_body, frozen_bootstrap, frozen_deform, frozen_rig, baseline_makehuman, morphology_body, makehuman_pose, mesh, errors. No source clearance inferred from docstrings. Bootstrap dependencies require independent implementation or explicit per-file provenance clearance. MORPH-02: nine data files and one license match upstream Git blobs; separate pinned manifest recorded. Public fixtures must be newly procedural or separately authorized. No legacy photos, models or history admitted. SHA-256 acquisition checks and public repository security scan remain outstanding. Incremental review does not waive M1-001 acceptance.

## Public tree screening
Scanned all 13 tracked files in development/m1 at 9c9db044b50a0da79d190892c35c93f556ea6186. All readable; no matches for private key headers, common GitHub/AWS/OpenAI token patterns or quoted credential assignments. Tree contains documentation, manifests and license only; no photographs or legacy source. PASS for limited current-tree screening only. Full history and specialist scanner not run. Runtime asset digest verification remains outstanding.

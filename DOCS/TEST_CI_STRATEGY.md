# Test and CI execution plan
| Trigger | Required checks | Environment |
|---|---|---|
| Documentation only | Markdown/link/schema checks if relevant | lightweight CI |
| Logical code change | syntax/import, Ruff, affected unit/contract/focused regression | local + lightweight CI Windows/Linux as applicable |
| Functional delivery | affected integration and downstream consumers, empirical procedure | CI + Windows local; Blender when relevant |
| Shared contract change | all consumers, migration/compatibility; full gate if critical | CI + local |
| Milestone or critical cross-cutting change | full applicable regression, GUI, real photos, Blender, recovery and quality | CI + local owner review |

Approved GitHub Actions policy: one required dispatcher on PR/push with path classifier, always emit explicit check summary; docs-only never runs Blender unless docs alter executable fixtures/config. Lightweight jobs on Windows/Linux; integration jobs selected by dependency graph (vision -> fit -> rig -> export; persistence/orchestration -> all consumers). Explicit workflow_dispatch full gate with commit SHA and milestone input; no duplicate push/PR suites for same SHA/config. Cache dependencies by OS/Python/lock hash and authorized model assets by digest/license; cache test results only for identical commit, environment, inputs and test selection, never substitute cached result for required fresh empirical gate. Cancel obsolete lightweight runs on same branch; do not cancel active milestone evidence collection or release gates. Limit expensive jobs by concurrency group; no parallel agents editing same branch. Blender headless CI uses authorized fixtures, local actual UI inspection required. Private photographs/derivatives stay local. Required checks report PASS/FAIL/NOT_RUN/BLOCKED separately; skipped is not PASS. Full suite on demand and mandatory for canonical geometry, shared artifacts, persistence/migration, skeleton/skinning, USD assembly, security and foundational orchestration changes.

Governance: one active task; proceed automatically after targeted checks except required delivery/gate failure or material approval. No automatic merge to main, destructive action, public private-data commit or unverified asset. Backlog only TODO, IN_PROGRESS, BLOCKED, TECHNICAL_PASS, EMPIRICAL_PASS, DONE. EMPIRICAL_PENDING/PARTIAL/FAIL are report outcomes, not backlog statuses. TECHNICAL_PASS remains until empirical evidence reviewed; failed required gate blocks dependent work; DONE after all applicable criteria. Handoff only current task/status, tests/outstanding gate, last commit, next task/blocker; include actionable empirical instruction at delivery. Architecture updated only at meaningful milestones or approved breaking decisions.

## Component trigger matrix
| Change | Level 1 | Level 2 | Level 3 |
|---|---|---|---|
| Docs/format | links or Ruff | none | no |
| GUI presentation | widgets | affected flow | no |
| GUI binding | contracts/widgets | app integration | foundational contract change |
| Ingestion | parser/hash | persistence/import | persistence contract change |
| Mask/landmarks | vision contracts | review/overlay/fit | shared contract change |
| Camera | numerical | overlay/fit | no unless critical contract |
| Native fit | numerical/geometry | rig/preview/export | canonical change |
| Canonical geometry | integrity | all consumers | required |
| Skeleton/skinning | rig/weights | deformation/export | required |
| Pose solver | numerical | articulation/garments | skeleton contract change |
| Texture | UV/projection | appearance/export | normally no |
| Garment fit/collision | geometry/contact | deformation/layering | shared geometry change |
| USD material | paths/materials | targeted Blender | normally no |
| USD assembly | schema | Blender | required |
| Persistence/migration | integrity/recovery | all consumers | required |
| Foundational orchestration | state/concurrency | full workflow | required |
| Security | security tests | trust boundaries | required |
| Milestone | all applicable | all applicable | required |

PR checks are authoritative once PR exists; suppress equivalent push jobs, evaluate actual merge candidate where applicable. Unknown executable changes select conservatively. Required summary always runs and fails if a required job fails, is blocked or not run; not-applicable is explicit. One writer is a governance rule, not a CI concurrency guarantee.
## M2 technical verification

The local software smoke used P01 and its P05 low-light derivative from the
synthetic bundle. It exercised per-photo detection, shared fitting, reopen,
target switching without changing the fit digest, reference exclusion and
reinclusion, a semantic edit, restoration, and rigged USDA export. Average
silhouette IoU was 0.35490 at bootstrap and 0.35528 after fitting. The two
inputs share a source, so this is a software smoke result. The local
empirical test uses separate inputs under the empirical test plan.

Blender 4.5.3 imported the resulting USDA through its Python runtime. The
import had 13,380 vertices, 13,378 faces, UVs, 163 bones, normalized skin
weights and a bound armature. Editing a limb bone changed the evaluated mesh.

A separate procedural smoke with two distinct camera yaws exercised the
shared objective independently of the brightness-variant photos. Both camera
directions were recovered and average mask overlap increased from 0.96015
to 0.96321. Required checks passed on Windows and Linux in run 45655613911.

## M3 technical verification

Spatial pose was exercised with the synthetic frontal fixture and two
procedural articulation configurations. Native mesh and rig checks passed.
The M3 appearance smoke used P01 and its low-light P05 derivative. At 512
pixels, 41.2% of UV domain texels were observed. The coverage view identified
nearby padding and unobserved texels separately. A procedural overlap test
verified that an occluded triangle received no observed color. Blender 4.5.3
imported the resulting USDZ with the packed 512 × 512 albedo, editable
material, UVs, armature binding and 163 bones. Local empirical evaluation
remains in the test plan.


## M4 technical verification

The synthetic frontal smoke fit a top, shorts and trousers, projected a
separate garment UV map and packaged the independent garment with the body.
Each tested shell passed the 1 mm sampled penetration tolerance after
bounded correction. A neutral inner/outer pair passed the sampled layer
check and coincident layers were rejected. Qt offscreen checks exercised
the 1024 × 720 and 1440 × 900 layouts, fitting, removal and 3D outfit orbit.

Blender 4.5.3 imported separate body and top meshes with packed materials
and the same 163-bone rig. Editing an armature joint changed the evaluated
garment. The scene was saved, reopened, re-exported and reimported, and
removing the top preserved the body mesh. The smoke and regressions are
technical checks. Empirical validation is performed locally.

The 150% scaling probe verified the keyboard focus order in the garment
workspace. The installed application passed 20 tests locally. Required
Windows and Linux checks, including the source pattern scan, passed in
run 45662318139 on the M4 implementation commit.

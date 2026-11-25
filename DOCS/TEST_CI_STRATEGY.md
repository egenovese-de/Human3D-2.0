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
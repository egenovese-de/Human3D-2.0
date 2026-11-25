# Human3D 2.0 — Approved delivery baseline v0.2
Product owner approved the plan and required corrections on 2026-11-25. The independent public repository has been created by the owner. Implementation remains paused pending explicit authorization. All 59 tasks TODO; 94 source mappings (54 engineering + 40 UX), 23 deliveries, four milestones, three verification levels. This supersedes v0.1.

BACKLOG is the sole task/status record. ARCHITECTURE, DEPENDENCIES, TEST_CI_STRATEGY, EMPIRICAL_TEST_PLAN, MILESTONE_ACCEPTANCE, DECISIONS and TRACEABILITY govern execution. Sources: integrated delivery analysis v0.1 and final readiness audit, reconstruction and UX audits. No runtime, license or photographic certification implied.

## Start checklist
- [x] Plan corrections and foundational recommendations approved.
- [x] Owner creates independent public repository and supplies URL/branch; no fork or private history.
- [ ] M1-001: establish repository license, component clearance, attribution, secret/private-data exclusion and public fixture policy before copying anything.
- [ ] M1-002: record supported M1 envelope and evaluation protocol; identify authorized private datasets and owner review availability.
- [ ] M1-003: pin tested runtime, Windows/Blender versions and validation commands; establish one branch writer and required checks.
- [ ] Resolve remaining deferred decisions by deadlines in DECISIONS.

Only planning documentation has been published. No implementation or CI workflow has been initiated. First task after explicit authorization: H3D2-M1-001.

## Product vision

Human3D reconstructs editable, reusable 3D human assets from one or more photographs of the same person. A selected target determines pose and appearance; other views inform shared neutral anatomy. Planned outputs include independent clothing geometry, UVs, materials, skeleton, skin weights and editable OpenUSD for Blender.

## Documentation

- [ARCHITECTURE](DOCS/ARCHITECTURE.md)
- [BACKLOG](DOCS/BACKLOG.md)
- [TRACEABILITY](DOCS/TRACEABILITY.md)
- [DEPENDENCIES](DOCS/DEPENDENCIES.md)
- [TEST_CI_STRATEGY](DOCS/TEST_CI_STRATEGY.md)
- [MILESTONE_ACCEPTANCE](DOCS/MILESTONE_ACCEPTANCE.md)
- [EMPIRICAL_TEST_PLAN](DOCS/EMPIRICAL_TEST_PLAN.md)
- [DECISIONS](DOCS/DECISIONS.md)

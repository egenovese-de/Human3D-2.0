# Decisions — approved baseline v0.2
Owner approval of plan recorded 2026-11-25. Foundational recommendations adopted; deferred implementation details are not silently certified.

| ID | Approved direction | Alternative / risk |
|---|---|---|
| ADR-001/003 | Native frozen fixed topology | Legacy coupling/dynamic topology risks rig and UV stability |
| ADR-002 | Modular local Python, isolated workers as needed | Distributed architecture adds complexity |
| UXD-001/002/003/007 | Hybrid shell, automatic except blockers, one-click target, incremental integration | Wizard or premature polish adds friction/rework |
| UXD-005/008 | Project-owned local copies, explicit provider opt-in, offline core | References reduce disk but risk reproducibility; mandatory cloud risks privacy |
| Distribution | Independent public history, component clearance before copying | Fork/history migration prohibited |

## Deferred details
| ID | Recommended direction / remaining detail | Deadline | Risk of delay |
|---|---|---|---|
| ADR-005 | Native camera first; learned alternative only on evidence | Before M1-011 | Blocks alignment |
| ADR-007 | Explicit scale uncertainty, optional measurements; calibrate metrics | Before M1 fitting evaluation | Misleading anatomy |
| ADR-008/UXD-004 | Portable editable USD, honest partial export; pin Blender composition | Before M1-014 | Export rework |
| ADR-004 | External VLM provider deferred. M2 uses project-local detection and mask evidence. | M2 | External provider branch |
| UXD-006 | Limited semantic edits; define controls | Before M2-012 | Revision ambiguity |
| Pose scope | Expand supported poses from evidence | Before M3-001 | Unbounded validation |
| Face scope | Supported visible features, no unsupported likeness claims | Before M3-004 | Unbounded refinement |
| ADR-006 | Close-fitting tops/trousers/shorts; define layering and collision tolerance | Before M4-001 | Fit ambiguity |
| UX study | 12-person formative protocol; define scoring | Before M4-014 | Invalid usability evidence |
| Runtime/dataset/license | Pin versions, authorized inputs, rights and fixture manifest | M1-001–003 before affected work | Blocks migration or testing |

No new irreversible decision beyond approved recommendations. Owner resolves material deviations; unrelated eligible work continues.
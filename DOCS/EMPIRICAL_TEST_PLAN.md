# Empirical test plan

Proposed procedures for future implementation; no tests executed. All inputs require documented consent/rights; private photos and derivatives stay local. Each delivery uses exact candidate commit, recorded Windows/Blender/dependency versions, clean test project or previous accepted checkpoint, authorized dataset and applicable dependency PASS (see DEPENDENCIES). Controls named below are required proposed interfaces; if absent, delivery is BLOCKED, not deferred. For foundation CLI, exact package command is to be established by M1-003 and recorded before execution.

Common measurement: application-generated quality report compares projected landmarks/contours with independently annotated visible regions; normalize by subject box diagonal; IoU intersection/union; compare bootstrap vs fitted and held-out metrics. Record hashes, job/stage counts, elapsed time, topology/weight/collision reports where applicable. No manual internal JSON editing.

Common acceptance: PASS only if all listed expected outcomes and applicable approved metrics met and visual review accepted; PARTIAL if some outcomes met but not all; FAIL for incorrect result or violated invariant; BLOCKED for missing access, input, runtime or integration. PARTIAL/FAIL/BLOCKED stop dependent work. Retain local screenshots of named screens, logs, quality reports, output artifacts, input IDs/permissions, environment and Git SHA; Blender screenshots and .blend/USD where applicable. Never publish private evidence. Current status for every delivery: not run (master tasks TODO).

## D1-01 — Foundation

Tasks: H3D2-M1-001 through H3D2-M1-003.

Validation objective: demonstrate foundation on actual inputs.

Where to test: Windows and Linux CLI; owner approved equivalent GitHub Actions evidence for D1-01 only on 2026-11-25.

Test input: Actual candidate source inventory, license texts and authorized fixture manifest.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Inspect inventory and rights

2. run package import and targeted baseline

3. inspect dependency lock and scan report

Expected output / pass criteria: Every migrated candidate explicitly authorized; no secrets/private assets; clean imports.

Measurements and visual inspection: Inspect clearance per candidate, lock and import results; zero prohibited files.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Recheck rejected items without copying them.

Current status: PASS under owner-approved CI equivalence for D1-01 only. Evidence: foundation and security dispatcher run 45642499455 at 39ee9badb133bddfad7a3377892adba1668f49bb; hash-enforced runtime run 45641848574; asset integrity run 45638877256; clearance and fixture policy documents. No legacy source admitted; no public photo fixtures admitted. Local screenshots waived for this delivery only. Branch protection remains a manual administrative action; later empirical gates unchanged.

## D1-02 — Project and orchestration

Tasks: H3D2-M1-004 through H3D2-M1-006.

Validation objective: demonstrate project and orchestration on actual inputs.

Where to test: Windows Photos / Welcome.

Test input: 3 authorized photos, duplicate, damaged file and unsupported file.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. New project

2. Add folder

3. click another thumbnail

4. save and reopen

5. verify capability state; actual cancellation/recovery is mandatory at D1-07

Expected output / pass criteria: Correct counts and target; one click; original hashes unchanged; durable state survives restart; unavailable reconstruction clearly labeled.

Measurements and visual inspection: Count 3 unique imports and rejected/duplicate cases; compare hashes and reopened target.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Reopen last saved project; retry import or resume.

Current status: empirical D1-02 NOT_RUN. M1-006 technical verification covers the in-memory coordinator and application snapshots with automated tests. Actual reconstruction cancellation and recovery remain D1-07 checks.

## D1-03 — Vision and mask recovery

Technical smoke, Linux CPython 3.11.9 with locked dependencies and MediaPipe Lite v1.
Synthetic fixtures v0.1. Nine imports reopened with matching original hashes.
P01–P06 yielded one candidate each. N01 and N03 yielded zero, N02 yielded one
false-positive candidate. Detection confidence probes at 0.50, 0.65, 0.75 and
0.85 reproduced the same counts. Candidate output requires review before
fitting. Full-body readiness requires in-frame nose, shoulders, hips, knees and
ankles with visibility and presence at least 0.8. This provisional development
rule kept the N02 false positive and P04 crop in review and passed P01–P03 and
P05–P06. Detection candidates are preserved for correction. Real-photo
empirical validation remains NOT_RUN.

Run target analysis on a saved project with
`human3d detect-target PROJECT --model POSE_LANDMARKER_LITE_TASK`.


Tasks: H3D2-M1-007 through H3D2-M1-008.

Validation objective: demonstrate vision and mask recovery on actual inputs.

Where to test: Windows Photos / Review.

Test input: 3 real photos: frontal, multiple people, fragmented foreground.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Import each

2. Reconstruct

3. inspect subject and landmark overlay

4. select intended person

5. paint add/remove mask

6. Undo

7. Apply correction

8. Retry

Expected output / pass criteria: Correct subject; visible landmarks and annotated mask agreement reported; disconnected valid limbs retained or actionable blocker; original unchanged.

Measurements and visual inspection: Compare selected subject and visible annotated regions; retain before/after mask and regional IoU.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Undo correction or retry/exclude affected photo.

Current status: D1-03 empirical NOT_RUN. M1-008 technical smoke passed on Linux Qt offscreen with the synthetic frontal fixture: segmentation, brush gesture, undo and application to the current session. Corrections are session-local until persistent artifact storage is integrated.

## D1-04 — Freeze independence

Tasks: H3D2-M1-009 through H3D2-M1-010.

Validation objective: demonstrate freeze independence on actual inputs.

Where to test: Windows Character / bootstrap inspection and local CLI.

Test input: One authorized frontal photo and licensed bootstrap asset.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Run bootstrap through Reconstruct

2. inspect neutral preview

3. close project

4. disable MakeHuman access in isolated test environment

5. reopen and run native preview operation

Expected output / pass criteria: Topology/UV/rig preserved; zero post-freeze access in trace; reopen works.

Measurements and visual inspection: Compare topology/UV/rig hashes and access trace; inspect actual neutral mesh.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Restore test environment and reopen last valid frozen revision.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D1-05 — Automatic alignment

Tasks: H3D2-M1-011 through H3D2-M1-012.

Validation objective: demonstrate automatic alignment on actual inputs.

Where to test: Windows Photos / Review alignment.

Test input: 3 real frontal, side and partial/rotated photos.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Reconstruct each

2. open alignment overlay

3. compare landmarks

4. use supported visual correction or Retry

5. inspect unsupported reason

Expected output / pass criteria: Automatic initial overlay without JSON; reliable landmark error <=3% diagonal on supported cases; unsupported cases actionable.

Measurements and visual inspection: Measure visible annotated landmark error by region; inspect alignment and unsupported reason.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Reset alignment proposal and retry affected view.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D1-06 — Native fit and editable export

Tasks: H3D2-M1-013 through H3D2-M1-015.

Validation objective: demonstrate native fit and editable export on actual inputs.

Where to test: Windows Character / Export and Blender.

Test input: 2 authorized full-body photos of different subjects in close-fitting clothing.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Reconstruct

2. compare bootstrap and fitted neutral/posed views

3. export OpenUSD

4. Blender File > Import > Universal Scene Description

5. inspect mesh Edit Mode, armature Pose Mode and UV Editing

Expected output / pass criteria: Fit changes native geometry and improves supported anatomical metric over bootstrap under fixed evaluation conditions; IoU >=0.85 where comparable; valid mesh/rig/UV; editable import; no MakeHuman access.

Measurements and visual inspection: Compare bootstrap/fitted with fixed evaluation camera and pose; measure regional contour/landmark improvement and geometry change; inspect Blender mesh/rig/UV.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Restore previous body revision; retry fit/export to new folder.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D1-07 — M1 gate

Tasks: H3D2-M1-016 through H3D2-M1-017.

Validation objective: demonstrate m1 gate on actual inputs.

Where to test: Windows full journey and Blender.

Test input: R01 frontal plus R02 three-quarter and R08 fragmented, authorized.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Repeat full workflow from New project

2. correct fragmented case

3. export

4. import in Blender and edit mesh/pose

5. save and reopen blend

6. run full applicable regression

Expected output / pass criteria: All M1 acceptance criteria and recovery; no JSON; actual fitted body not template.

Measurements and visual inspection: Record interruption/recovery and full workflow results; verify edited mesh/pose survives save/reopen.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Retain failed evidence, restore valid revision, fix and rerun gate.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D2-08 — Evidence binding and fusion

Tasks: H3D2-M2-001 through H3D2-M2-003.

Validation objective: demonstrate evidence binding and fusion on actual inputs.

Where to test: Windows Photos / evidence summary.

Test input: 3 views same person plus different-person distractor; optional authorized provider response.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Import folder

2. inspect photo IDs and evidence

3. run local fusion

4. if approved enable provider and import bound response

5. attempt mismatched response

Expected output / pass criteria: Immutable binding; mismatched evidence rejected; local fusion works without provider; ambiguity requires review.

Measurements and visual inspection: Compare evidence photo IDs/hashes; exclude distractor; disable provider and verify local fusion.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Disable provider, reject response, retry only affected photo.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D2-09 — Native anatomy and rig

Tasks: H3D2-M2-004 through H3D2-M2-006.

Validation objective: demonstrate native anatomy and rig on actual inputs.

Where to test: Windows Character / neutral preview and Blender.

Test input: 2 authorized subjects with differing torso and limb proportions.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Reconstruct each

2. compare bootstrap and native torso/limb revisions

3. export current rig

4. inspect joint bends in Blender

Expected output / pass criteria: Supported proportions change in correct direction; topology 100%; weight error <=0.0001; no invalid faces or implausible bends.

Measurements and visual inspection: Compare torso/limb changes against supported measurements; inspect joint deformation and weight sums.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Restore prior body/rig revision and retry fit.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D2-10 — Multi-view optimization

Tasks: H3D2-M2-007 through H3D2-M2-010.

Validation objective: demonstrate multi-view optimization on actual inputs.

Where to test: Windows Character / comparison.

Test input: 3 views of one subject in different poses, one additional held-out view.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Import three training views

2. Reconstruct

3. inspect per-view overlays, shared neutral body and uncertainty

4. evaluate held-out view without including it

Expected output / pass criteria: Independent cameras/poses; bounded convergence; per-view metrics and uncertainty; no hidden anatomy claims.

Measurements and visual inspection: Reserve fourth view; inspect independent cameras/poses, shared revision and convergence/rollback logs.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Restore previous fit; retry problematic view.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D2-11 — Selective recomputation and revisions

Tasks: H3D2-M2-011 through H3D2-M2-012.

Validation objective: demonstrate selective recomputation and revisions on actual inputs.

Where to test: Windows Photos / Character history.

Test input: 3 included views of same person.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Switch target among all three

2. exclude/reinclude reference

3. retry one photo

4. restore previous revision

5. inspect job history

Expected output / pass criteria: Zero body digest changes for target-only switch; unchanged evidence hashes; only affected stages rerun; restore succeeds.

Measurements and visual inspection: Record body digests and stage counts before/after target switch, exclusion, correction, edit and restore.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Restore prior revision and reinclude reference.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D2-12 — M2 gate

Tasks: H3D2-M2-013 through H3D2-M2-014.

Validation objective: demonstrate m2 gate on actual inputs.

Where to test: Windows comparison and Blender.

Test input: At least 3 subjects, each 3 training views and 1 held-out view.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Run single-photo baseline then multi-photo fit using same bootstrap

2. compare held-out reports

3. switch targets

4. export/import and inspect rig

5. full regression

Expected output / pass criteria: Held-out improvement under approved protocol, no unacceptable regression; M2 invariants and Blender checks.

Measurements and visual inspection: At least three subjects, three training views and one withheld per subject; identical baseline/evaluation rules; report paired regional errors.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Retain both reports; restore baseline; fix and rerun.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D3-13 — Target pose and deformation

Tasks: H3D2-M3-001 through H3D2-M3-003.

Validation objective: demonstrate target pose and deformation on actual inputs.

Where to test: Windows Character / pose comparison and Blender.

Test input: 3 real supported poses including bent limb and seated if approved.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Select target

2. Reconstruct

3. inspect overlay

4. use visual pose correction

5. export and inspect armature bends/contact in Blender

Expected output / pass criteria: Landmark threshold on supported views; no implausible deformation or invalid geometry; neutral digest unchanged.

Measurements and visual inspection: Record neutral digest, landmark/contact error and joint deformation across three supported poses.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Restore prior pose and retry.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D3-14 — Facial refinement

Tasks: H3D2-M3-004 through H3D2-M3-004.

Validation objective: demonstrate facial refinement on actual inputs.

Where to test: Windows Character / face comparison.

Test input: 2 authorized clear face photos with distinct features.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Reconstruct

2. inspect head before/after and photo comparison

3. inspect profile and uncertainty

Expected output / pass criteria: Visible supported features improve against annotated landmarks; no identity claim; unsupported regions labeled.

Measurements and visual inspection: Compare independent facial landmarks for two subjects; inspect neck and additional angles; verify affected rig.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Restore previous head revision.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D3-15 — Skin projection and seams

Tasks: H3D2-M3-005 through H3D2-M3-007.

Validation objective: demonstrate skin projection and seams on actual inputs.

Where to test: Windows Appearance / texture preview.

Test input: 3 authorized views with exposed skin, occlusion and differing lighting.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Reconstruct appearance

2. inspect skin mask, UV bake, visible coverage and seams

3. compare source views

Expected output / pass criteria: No garment pixels baked as skin in annotated regions; valid UVs; visible seams reviewed; coverage provenance present.

Measurements and visual inspection: Measure annotated skin contamination, UV validity and texel provenance; inspect seams and occlusion.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Retry mask or bake; restore prior atlas.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D3-16 — Materials and textured export

Tasks: H3D2-M3-008 through H3D2-M3-010.

Validation objective: demonstrate materials and textured export on actual inputs.

Where to test: Windows Appearance / Export and Blender.

Test input: 2 authorized subjects with visible and unseen skin regions.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Inspect material and observed/estimated views

2. export textured USD

3. move bundle

4. import in Blender Material Preview and UV Editing

Expected output / pass criteria: Relative paths resolve; material and UV editable; unseen texels labeled; lighting artifacts reviewed.

Measurements and visual inspection: Verify relocated paths, editable material/UV and observed/inferred coverage; inspect lighting artifacts.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Restore atlas; export to new folder.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D3-17 — M3 gate

Tasks: H3D2-M3-011 through H3D2-M3-012.

Validation objective: demonstrate m3 gate on actual inputs.

Where to test: Windows and Blender.

Test input: Expanded supported pose/face/lighting set, at least 3 subjects.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Repeat pose and appearance journey

2. compare source overlays

3. import, articulate, edit materials and save/reopen

4. full regression

Expected output / pass criteria: M3 criteria, structural and photographic outcomes separately accepted.

Measurements and visual inspection: Report structural and photographic results separately; inspect textured articulation and saved/reopened asset.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Retain reports; restore valid revision; rerun gate.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D4-18 — Garment scope and independent geometry

Tasks: H3D2-M4-001 through H3D2-M4-003.

Validation objective: demonstrate garment scope and independent geometry on actual inputs.

Where to test: Windows Appearance / object hierarchy.

Test input: 3 authorized photos: supported top, trousers/shorts, unsupported loose garment.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Reconstruct

2. inspect garment mask and separate objects

3. toggle visibility

4. inspect unsupported warning

Expected output / pass criteria: Supported garment separate from body; visibility not export inclusion; unsupported clearly labeled.

Measurements and visual inspection: Count independent mesh objects and compare body digest after visibility toggle; inspect unsupported warning.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Retry mask or omit unsupported garment explicitly.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D4-19 — Garment fit and materials

Tasks: H3D2-M4-005 → H3D2-M4-004 → H3D2-M4-006.

Validation objective: demonstrate garment fit and materials on actual inputs.

Where to test: Windows Appearance / fit inspector; Blender required at D4-21.

Test input: 2 supported garment photos with different fit and texture.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Inspect fitted garment

2. apply supported adjustment

3. inspect rest geometry, UV and material preview

4. compare photo

Expected output / pass criteria: Independent rest mesh, valid UVs/materials, visible contour agreement under approved tolerance.

Measurements and visual inspection: Compare rest/fitted mesh and annotated garment contour; validate UVs; adjust and undo.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Undo edit or restore garment revision.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D4-20 — Garment deformation and collisions

Tasks: H3D2-M4-007 through H3D2-M4-009.

Validation objective: demonstrate garment deformation and collisions on actual inputs.

Where to test: Windows Character / garment fit.

Test input: 2 supported garments in 3 poses, one supported layered case.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Switch pose

2. inspect garment deformation and collision feedback

3. apply supported correction

4. inspect clearance report

Expected output / pass criteria: Normalized weights, no unresolved intersections within approved tolerance; unsupported layering flagged.

Measurements and visual inspection: Record penetration depth/count, weight sums and clearance across three poses and supported layer.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Restore previous garment/pose; retry correction.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D4-21 — Complete assembly and workflow

Tasks: H3D2-M4-010 through H3D2-M4-011.

Validation objective: demonstrate complete assembly and workflow on actual inputs.

Where to test: Windows Export and Blender.

Test input: One complete authorized character with top and trousers.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Export full bundle

2. inspect manifest

3. move bundle

4. import in Blender

5. hide/remove garment, edit mesh, pose, material

6. save/reopen and re-export/reimport

Expected output / pass criteria: Separate editable objects, armature, UVs, portable textures, correct axes/units; manifest truthful; no missing required components.

Measurements and visual inspection: Verify manifest against objects; edit/remove garment, mesh, pose/material; save/reopen and supported roundtrip.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Keep prior bundle; retry export to new folder.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D4-22 — Accessibility and usability

Tasks: H3D2-M4-012 through H3D2-M4-014.

Validation objective: demonstrate accessibility and usability on actual inputs.

Where to test: Windows production application and Blender.

Test input: 12 consenting participants (formative target; protocol due before M4-014); authorized mixed folder, fragmented mask, unsupported garment, multi-view set.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Run UT01–12 from UX pp.15–16

2. test keyboard, scaling, interruption/recovery and full export

3. record actions and comprehension

Expected output / pass criteria: UX targets in milestone criteria; zero loss of work or misleading status; actual Blender import.

Measurements and visual inspection: Score UT01–12 using predefined denominators; 11/12 for each 90% or 85% participant-level target; count actions and losses.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Restore project checkpoint; record issue and repeat affected scenario after fix.

Current status: NOT_RUN; no empirical or technical PASS claimed.

## D4-23 — Release and final gate

Tasks: H3D2-M4-015 through H3D2-M4-016.

Validation objective: demonstrate release and final gate on actual inputs.

Where to test: Local audit, GitHub Actions and Windows/Blender.

Test input: Authorized public fixture manifest and private expanded benchmark R01–R12.

Preconditions: common baseline above; required dependency deliveries accepted; relevant controls and dependencies available.

Steps:

1. Inspect release candidate inventory, licenses, attribution and secret scan

2. run full gate on exact SHA

3. repeat full reconstruction and Blender checks

4. owner reviews evidence

Expected output / pass criteria: No prohibited content; all applicable gates executed and passed; owner approval recorded.

Measurements and visual inspection: Verify exact SHA, cumulative clearance and all required gate results; retain owner approval.

Evidence: common evidence bundle plus screenshots of each named inspection and resulting saved artifacts.

Failure recovery: Quarantine offending files; fix candidate and rerun affected/full gate.

Current status: NOT_RUN; no empirical or technical PASS claimed.
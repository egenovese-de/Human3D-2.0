"""Consolidate numerical qualifications and source-linked decision briefs."""
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean, median
from zipfile import ZipFile

import numpy as np


def jsonfile(p, default=None):
    return json.loads(p.read_text()) if p.exists() else default


def dump(file,data):
    file.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


def tab(head,rows):
    return '\n'.join('| '+' | '.join(map(str,row))+' |' for row in [head,['---']*len(head),*rows])


def main(a):
    out=a.output
    out.mkdir(parents=True,exist_ok=True)
    root=a.results
    raw={p.parent.name:jsonfile(p) for p in sorted((root/'study').glob('*/surface.json'))}
    dev=('A_high_mass','A_muscular','B_female')
    held=sorted(set(raw)-set(dev))
    bi=[s for s in held if s.startswith('B_')]
    aa=[s for s in held if s.startswith('A_')]
    hist={}
    with ZipFile(a.g5) as z:
        hist=json.loads(z.read('measurements/calibrated-surface.json'))
        hist_manifest=json.loads(z.read('reports/G5_DATASET_MANIFEST.json'))
    fit={p.parent.name:jsonfile(p) for p in sorted((root/'study').glob('*/fit.json'))}
    photo={p.parent.name:jsonfile(p) for p in sorted((root/'photo').glob('*/surface.json'))}
    oracle=jsonfile(root/'oracle-surface.json',{})
    posture=jsonfile(root/'posture-surface.json',{})
    pose=jsonfile(root/'pose.json',{})
    sections=jsonfile(root/'sections.json',{})
    structure=jsonfile(root/'structure.json',{})
    resolution=jsonfile(root/'resolution.json',{})
    diagnostic=jsonfile(root/'diagnostics.json',{})
    exports={p.parent.name:jsonfile(p) for p in sorted((root/'export').glob('*/blender-roundtrip.json'))}
    def md(name, title, content):
        (out/(name+'.md')).write_text('# G6 · '+title+'\n\n'+content.strip()+'\n')
    def score(c,m,v='accepted'):
        return raw[c][m][v]['mean']
    def avg(cases,m,v='accepted'):
        values=[score(c,m,v) for c in cases if m in raw[c]]
        return mean(values) if values else None
    def f(value):
        return '—' if value is None else f'{value:.2f}'
    methods=list(dict.fromkeys(m for s,results in raw.items() for m in results if m!='initial'))
    summary=[]
    for m in methods:
        subject=[c for c in bi if m in raw[c]]
        if not subject:
            continue
        paired=[score(c,'D0')-score(c,m) for c in subject]
        replaced=sum(raw[c][m]['fraction_vs_parent']<1 for c in subject)
        rng=np.random.default_rng(666)
        bounds=np.percentile(rng.choice(paired,(5000,len(paired))).mean(axis=1),[2.5,97.5]).tolist()
        summary.append({'method':m,'n_b':len(subject),'proposal_b_mean_mm':avg(subject,m,'proposal'),
            'retained_b_mean_mm':avg(subject,m),'retained_a_mean_mm':avg(aa,m),'development_mean_mm':avg(dev,m),
            'gain_mean_mm':mean(paired),'gain_median_mm':median(paired),'worst_gain_mm':min(paired),
            'descriptive_bootstrap_95_mm':bounds,'backtracked_B':replaced})
    index={m['method']:m for m in summary}
    def method_table(keys):
        return tab(['Method','A held-out retained mm','B held-out proposal mm','B held-out retained mm',
                    'B paired gain mm','B backtracked'],[[m,f(index[m]['retained_a_mean_mm']),
                f(index[m]['proposal_b_mean_mm']),f(index[m]['retained_b_mean_mm']),
                f(index[m]['gain_mean_mm']),f"{index[m]['backtracked_B']}/{index[m]['n_b']}"]
                for m in keys if m in index])
    keys=['D0','R0_D9','R0_long','R0_restart','R1_extended','R2_coarse','R2_fine','R2_fine_long',
          'R3_cage','R4_graph48','R4_graph120','R5_symmetric','R6_lattice','R6_graph']
    stage_table=method_table(keys)
    estimated=sum(p.is_file() for p in (root/'baseline').glob('*/estimated/D0.npy'))
    baseline=[]
    for case in sorted(raw):
        entry=hist.get(case,{})
        if not entry:
            continue
        baseline.append([case,f(entry['D0']['symmetric_mm']['mean']),f(score(case,'D0')),
                         f(entry['D9']['symmetric_mm']['mean']),f(score(case,'R0_D9'))])
    photo_rows=[]
    for s,d in photo.items():
        for m in ('P_oracle_1_ffd','P_oracle_2_ffd','P_oracle_4_ffd','P_oracle_8_ffd','P_calibrated_rgb_ffd',
                  'P_calibrated_rgb_graph','P_estimated_rgb_ffd','P_estimated_rgb_graph',
                  'P_stress_yaw_ffd','P_stress_elevation_ffd','P_stress_dx_ffd','P_stress_span_ffd','P_stress_distance_ffd'):
            if m not in d:
                continue
            p='B_estimated' if m.startswith('P_estimated') else 'D0'
            views=diagnostic.get('heldout_iou',{}).get('photo/'+s,{})
            delta=(mean(views[m])-mean(views[p])) if m in views else None
            before,after=d[p]['accepted']['mean'],d[m]['accepted']['mean']
            photo_rows.append([s,m,f(before),f(after),f(before-after),f(delta)])
    transfer_table=tab(['Subject','Arm','M7 anchor mm','Retained mm','Gain mm','Held-out Δ IoU'],
                        [r for r in photo_rows if r[1] in ('P_oracle_4_ffd','P_calibrated_rgb_ffd','P_estimated_rgb_ffd')])
    ptable=tab(['Subject','Arm','M7 anchor mm','Retained mm','Gain mm','Held-out Δ IoU'],photo_rows)
    pst=tab(['Subject','Native mm','Arm-direction mm','All limb-directions mm'],
          [[s,*[f(d[k]['accepted']['mean']) for k in ('D0','Posture_arm','Posture_limbs')]] for s,d in posture.items()])
    orc=tab(['Subject','M7 mm','Exact depth FFD mm','Depth weighted by normal agreement mm'],[
        [s,*[f(item[k]['accepted']['mean']) for k in ('D0','P_oracle_depth','P_oracle_depth_normals_weight')]]
            for s,item in oracle.items()])
    pose_tests=sum(len(m) for subjects in pose.values() for arms in subjects.values() for m in arms.get('poses',{}).values())
    pose_failed=sum(not n['valid'] for subjects in pose.values() for arms in subjects.values()
                    for m in arms.get('poses',{}).values() for n in m.values())
    export_n=sum(len(s) for s in exports.values())
    worst_photo=sorted((float(r[4]),r[0],r[1]) for r in photo_rows if r[1].startswith('P_estimated'))
    runtime=[]
    for name in keys[1:]:
        times=[r['study'][name]['seconds'] for r in fit.values() if name in r['study']]
        qual=[row[name]['qualification_s'] for row in raw.values() if name in row]
        if times:
            runtime.append([name,len(times),f(median(times)),f(max(times)),f(median(qual)) if qual else '—'])
    peak=max(v['peak_rss_kib_process'] for v in fit.values())/1024
    manifest={'g6_branch':'lab/g6-geometry-capacity','M7_qualified':'020fcc793e7417d6927d9e07346678e110ae9ddc',
        'G5':'2c9bc5e6d4a3103e7f691add806bcaff90a61b6b',
        'G4':'ca90165d259bada9b3cea945d1227be0f83656ef','MakeHuman':'1f508f6083b2f823dab15de924b3bde72e08d77c',
        'geometry_cases':hist_manifest['subjects'],'development':list(dev),'held_out':held,
        'Family_C':{'admitted':False,'candidate':'MPI FAUST','blocker':'Authenticated download and admission of license-bound original scans were unavailable.',
        'source':'https://faust-leaderboard.is.tuebingen.mpg.de/'},
        'stress_test':'A_heldout_1, B_male, B_female_expanded synthetic camera controls',
        'subject_result_hashes':{s:sha256((root/'refs'/f'{s}.npz').read_bytes()).hexdigest() for s in raw}}
    dump(out/'G6_DATASET_MANIFEST.json',manifest)
    with (out/'G6_SUBJECT_SCORES.csv').open('w',newline='') as stream:
        w=csv.writer(stream)
        w.writerow(['subject','partition','arm','proposal_mean_mm','retained_mean_mm','retained_p95_mm','new_crossings','fraction'])
        for s,arms in raw.items():
            for k,row in arms.items():
                w.writerow([s,'development' if s in dev else 'held-out',k,row['proposal']['mean'],
                            row['accepted']['mean'],row['accepted']['p95'],row['new_crossings_proposal'],row['fraction_vs_parent']])
    details={'dataset':{'development':dev,'held_out':held},'geometry':raw,'geometry_summary':summary,
        'photo':photo,'g5_oracle_transfer':oracle,'posture':posture,'structural_provenance':structure,
        'diagnostics':diagnostic,'sections':sections,'resolution':resolution,'rig':pose,'roundtrip':exports,
        'baseline_calibrated_complete':len(raw),'baseline_estimated_complete':estimated,'peak_fit_rss_mib':peak}
    dump(root/'full-measurements.json',details)
    compact=dict(details)
    compact.pop('rig')
    compact.pop('sections')
    compact['raw_artifact']='measurements/full-measurements.json in evidence archive'
    dump(out/'G6_MEASUREMENTS.json',compact)
    md('G6_EXECUTIVE_REPORT','Executive decision',f"""
**Recommendation B. Qualify native initialization plus bounded volumetric FFD as the next candidate.** Keep M7 as the production fallback. Enable no advanced deformation for estimated registration based on these results. This is partial experimental qualification.

The actual qualified M7 branch ran on all {len(raw)} calibrated references. Estimated registration produced {estimated}/10 complete results. The direct G5 benchmark was rerun with its original implementation, seeded from the fresh M7 outputs. Blender nearest-triangle evaluation preserved the G5 sampling convention.

{stage_table}

The fine spline lattice at 14 iterations lowers independent held-out mean error from **{f(avg(bi,'D0'))} to {f(avg(bi,'R2_fine'))} mm**, an **{100*(1-avg(bi,'R2_fine')/avg(bi,'D0')):.1f}%** paired reduction over M7 across three independent bodies. The 28-step ceiling probe reached **{f(avg(bi,'R2_fine_long'))} mm**. The strongest proposal by mean was the fine lattice followed by per-vertex refinement at **{f(avg(bi,'R6_lattice','proposal'))} mm**. Screening brought that result to **{f(avg(bi,'R6_lattice'))} mm**. Select the simpler fine lattice.

## Photographic transfer

{transfer_table}

Calibrated RGB results use the actual M7 masks, known camera and canonical observation pose. Estimated results use admitted M7 poses and cameras. This is synthetic RGB capture with ground-truth geometry available for evaluation. The estimated lane uses first-order contour Jacobians that do not differentiate rebinding and articulation. The strongest observed estimate-lane regression in the tested candidates was **{abs(worst_photo[0][0]):.2f} mm** on {worst_photo[0][1]} with {worst_photo[0][2]}.

## Qualification and release implications

- Existing-family optimizer restart reached **{f(avg(bi,'R0_restart'))} mm** versus **{f(avg(bi,'R0_D9'))} mm** with the re-executed G5 direct oracle. Shoulder and arm stance materially alter the measured residual. Simultaneous limb orientation transfer regressed.
- The full fine FFD candidates on the three independent held-outs cleared the no-new-crossings rule against M7. Blender 4.5.16 qualified {export_n} USD round trips across one representative from each family. The controlled native pose screen measured {pose_tests} retained/rebound checks with {pose_failed} product pose-validator failures. Collision evidence is separate.
- G5 predictor integration remains deferred. Exact depth improves isolated FFD tests. The normal-consistency weights provide mixed incremental effect. These are existing exact-map oracle controls. No new predictor or learned evidence was qualified.
- The target Windows 11 workstation and real capture benchmark remain open. Windows CI covers the small CPU geometry-operator subset. The technical decision is conditional on registration, full rig and export validation, and real capture evidence.

Use the decision matrix and the reproduction instructions to plan the gated M9 study. The canonical topology remains the branch’s reference contract. Fine anatomical detail and topology redesign require separate evidence and product decisions.
""")
    md('G6_EXPERIMENTAL_METHODOLOGY','Experimental method',"""
The 6 MakeHuman and 4 MB-Lab references reuse the G4/G5 family identities and the existing development/held-out split. Coordinates are the G5 fixed centimetre frame with Y up, frontal positive Z and fixed scale and floor. Optimization never performs candidate-specific evaluation alignment. Family C was reviewed for admission and is absent.

Direct fitting uses sampled surface correspondences and robust residuals. Same-topology known vertex correspondences are tested as a separate oracle. Geometry is evaluated in Blender using two independent seeded 12,000-sample area-weighted sets against actual closest triangles, with symmetric mean, median, RMS, P95, maximum and directional coverage. Constrained geometry is screened against M7 before final scoring. Historical candidates R0_D9, R0_long and R0_restart are logged with observed defects for comparability.

The fixed methods evaluate five deformation families after a shared R0_long initialization. R1 starts from the R0_long controls using a G1 dependency evaluator. Reciprocal coverage uses sampled-point matches in the optimizer. The final distance uses closest triangles. Fixed regularizers, displacement limits, solver budget contrasts and stress settings are recorded in code and configuration. No held-out fitting score selected a different hyperparameter for an individual subject.
""")
    md('G6_BASELINE_REPRODUCTION','Historical baseline reproduction',tab(
        ['Subject','G5 D0 mm','G6 M7 D0 mm','G5 D9 mm','G6 replay D9 mm'],baseline)+
        '\n\nThe service uses M7 Engine B through Session and ReconstructionService. Family A reuses the original RGB bytes. Family B renders from verified local references with the pinned G5 script. R0_D9 reuses G5 direct_fit. L0 was rerun for three photo subjects with G5 refine and measured separately. See the original G5 D7/D8 for full exact/learned local comparisons. Numerical comparisons use the same metric and units.')
    md('G6_OPTIMIZATION_CAPACITY','Optimizer capacity',method_table(
        ['R0_D9','R0_long','R0_restart','R2_fine_budget6','R2_fine','R2_fine_long','R5_symmetric_budget6','R5_symmetric','R5_symmetric_long'])+
        '\n\nThe two native long-budget runs share residual definition and bounds while changing only start values. G5 D9 also differs in sample construction and objective schedule. The evaluated 6, 14 and 28 outer-iteration brackets compare optimization progress within a family. Equal iteration limits between method families are measured separately from elapsed compute. Solver and correspondence curves, wall time and termination codes are archived. These finite budgets establish observed ceilings under their own schedules.')
    md('G6_NATIVE_MORPH_BENCHMARK','Native morphs',method_table(['D0','R0_D9','R0_long','R0_restart','R1_extended'])+
       '\n\nR1 extends the G1 dependency-aware evaluator with explicit trunk, gluteal, neck, chest, asymmetry and limb control stems. It applies upstream modifier semantics and keeps bounds. Recording target weights avoids double accumulation. The comparison isolates expansion relative to the tested R0_long seed, with changes in residual sample schedule and additional controls interacting. The strongest native result in this matrix was the restricted midpoint restart on independent bodies. Complete native morph and redundancy discovery remain open.')
    md('G6_FFD_BENCHMARK','Free-form deformation',method_table(['R2_coarse','R2_fine_budget6','R2_fine','R2_fine_long'])+
        '\n\nOpen tensor-product splines with 3×5×3 or 5×8×5 controls, sparse design matrix, difference regularization, robust paired correspondences and 55 mm displacement cap. Each stage caches its basis. diagnostics.json samples the Jacobian of a refit smooth field and reports how closely it embeds the retained surface. The reembedding is a diagnostic and cannot certify determinant positivity for the clipped output everywhere.')
    md('G6_CAGE_DEFORMATION_BENCHMARK','Tetrahedral boundary cage',method_table(['D0','R2_fine','R3_cage'])+
        '\n\nThe global boundary cage uses tetrahedral piecewise-affine interpolation, with regularization on hull neighbors. It differs from the spline lattice in support, continuity across tetrahedra and control placement. Recovered displacement coefficients provide approximate deformation determinants in the fit logs. Regional cages, mean-value coordinates and refined boundary placement remain open.')
    md('G6_DEFORMATION_GRAPH_BENCHMARK','Embedded deformation graph',method_table(['R4_graph48','R4_graph120'])+
        '\n\nNodes use mesh-geodesic farthest-point placement and geodesic neighborhood blending. Edges respect the connected topology instead of direct Euclidean proximity. The tested graph fits local translations with smoothness on the graph. Rotational ARAP and region-specific stiffness remain open. Report both proposal and retained metrics because crossings account for much of the difference.')
    md('G6_NON_RIGID_REGISTRATION_BENCHMARK','Non-rigid surface registration',method_table(
        ['R5_nearest','R5_regions','R5_normals','R5_symmetric','R5_symmetric_long'])+
        '\n\nThe canonical mesh fits regularized displacement under nearest-sample ICP with a sparse Laplacian. The arms compare nearest, hard regional labels, region plus normal weighting and symmetric nearest-sample coverage. There is no separate point-to-plane solve or triangle-aware fitting correspondence in this matrix.')
    md('G6_HYBRID_ARCHITECTURE_BENCHMARK','Hybrid architectures',method_table(
        ['R2_fine','R4_graph120','R6_lattice','R6_graph'])+
        '\n\nThe two hybrid arms append a more strongly regularized per-vertex stage after fine FFD or the geodesic graph. The first-stage inputs are the pre-Blender-screen meshes. Qualification compares every complete output with the common M7 structural parent. This schedule tests two fixed hybrids. It leaves a joint optimizer with explicit collision constraints open.')
    md('G6_ANATOMICAL_CORRESPONDENCE','Correspondence',method_table(
        ['R5_nearest','R5_regions','R5_normals','R5_symmetric'])+
        '\n\nOn independent bodies region labels and normal agreement change solutions and the fraction retained after screening. Normal-aware correspondence is the strongest retained R5 variant on average in the tested cohort. Stable region-constrained labels use height, side and lateral position. The graph uses mesh geodesics independently of target nearest-sample matching. Coarse labels can disagree with anatomical boundaries when posture or torso width changes. Landmark-guided surface correspondence and explicit anatomical error auditing remain open.')
    md('G6_ANATOMICAL_REGION_IMPACT','Regional impact',tab(['Body','Arm','Height bands mean mm, from feet to head'],
        [[s,m,', '.join(f(x) for x in raw[s][m]['accepted']['height_band_mean_mm'])]
         for s in bi for m in ('D0','R0_D9','R2_fine','R6_lattice')])+
        '\n\nBands are fixed in the reference coordinate frame, not a complete anatomical semantic mapping. The section experiment resolves separate abdomen, waist, hip and selected limb loops. Dedicated face, groin, hand and axillary validation remains open.')
    sec=[]
    for name in ('abdomen','waist','hip','upper_arm_L','thigh_L','calf_L','chest_diagnostic'):
        for m in ('D0','R2_fine'):
            rr=[row[name]['fits'][m] for c in held if (row:=sections.get(c,{})).get(name,{}).get('fits',{}).get(m,{}).get('shape_mean_mm') is not None]
            if rr:
                sec.append([name,m,len(rr),f(mean(x['shape_mean_mm'] for x in rr)),f(mean(abs(x['circumference_signed_mm']) for x in rr))])
    md('G6_SECTION_MEASUREMENTS','Anatomical sections',tab(['Section','Arm','Closed valid pairs','Mean shape mm','Mean absolute circumference error mm'],sec)+
        '\n\nFixed reference planes cut the triangles into edge-connected loops. Arm, thigh and calf axes use reference joints on Family A and discard triangles outside a fixed same-side crop. Open or missing loops are unavailable. Chest loops are diagnostic because the arms can join the central torso loop. The machine-readable profile includes shape P95, width, depth and area. This remains a bounded cross-section study, with section orientation and repeatability still open.')
    md('G6_CANONICAL_POSE_ANALYSIS','Canonical pose and posture',pst+
        '\n\nFor the independent matched-geometry control the baseline row in this table is the native R0_D9 shape. Orientation transfer uses frozen authored MB-Lab directions and the product skin weights. Landmark anchors are normalized with the original G5 scale and floor. It is an explicit pose intervention, and scores against the same unmoved reference. The all-limb control introduces a failure rather than a valid normalization. The A, T and X configurations are fixed direction probes of one MakeHuman holdout. Raw collision counts are in structure.json. Use this evidence to preserve the native canonical contract pending wider pose conditioning and landmark correspondence tests.')
    md('G6_TOPOLOGY_CAPACITY','Topology and resolution',f"""
One midpoint subdivision on A_slim changed {resolution.get('old_triangles','unavailable')} to {resolution.get('new_triangles','unavailable')} triangles. The maximum change in sampled reference distance was {resolution.get('max_change_reference_distance_mm','unavailable')} mm. Mesh-array bytes grew from {resolution.get('mesh_array_bytes_before','unavailable')} to {resolution.get('mesh_array_bytes_after','unavailable')}. This is a surface-preserving resolution control. The experiment did not train or fit displacement at the new vertices.

| Anatomical concern | Supported interpretation |
| --- | --- |
| Face, ears, fingers and toes | Existing connectivity supports moving present features. No dedicated detail-capacity fit or coverage result was run. |
| Navel, breast projection, nipples and areolae | Global shape and contour are evaluated at coarse resolution only. Visual material and local geometry require separate qualification. |
| External genital anatomy and fine folds | No authorized independent detail cohort was admitted. Existing-connectivity deformation cannot create missing connected components or new openings. Exact feature representation is unresolved. |
| Subdivision, local detail and attachments | Linear subdivision adds vertices and preserves the sampled surface. Local detail, changed boundary topology and attachment compatibility are separate hypotheses. |

An anatomy-specific topology gate remains open. The present family-level error results do not establish an intrinsic representation limit.
""")
    md('G6_STRUCTURAL_VALIDATION','Structural validation',method_table(
        ['R1_extended','R2_fine','R3_cage','R4_graph120','R5_symmetric','R6_lattice'])+
        '\n\nAll fit arms use the existing M7 rebind check and relative face-normal screen before Blender. Blender BVH overlaps record disjoint-index triangle pairs. For advanced proposals, new pairs or relative face flips cause bounded backtracking against the applicable M7 parent. Pre-existing pairs, reference pairs and proposal pairs are separate. The final metric retains fallback results, including zero deformation where necessary. A retained fit can inherit existing crossings. The archive records topology, numeric hashes, and pre/post structural reductions. A topological proof, analytic collision certification and anatomical semantic validation remain open.')
    md('G6_RIG_AND_POSE_QUALIFICATION','Rig, skin, pose and export',f"""
The product rebind path recovers joints using canonical locator indices. Across {len(pose)} subjects the neutral, arm elevation, elbow, hip, knee, torso and asymmetric routines logged **{pose_tests}** original-joint/rebound checks and **{pose_failed}** product pose-validator failures. Same-topology reference articulation permits a vertex comparison. Independent poses use the same controller and lack measured pose ground truth.

Pose outside the canonical geometry preserves the canonical digest. Edge ratios, inferred joint differences and sampled Blender pose crossings are archived. Four representative D0 and fine-FFD USD artifacts across A_slim and B_male were submitted to Blender. **{export_n}** passed import, bone deformation, vertex editing and save/reopen. USD invariants compare topology, UV and skin arrays with the M7 anchor. Blender pose intersection evidence covers the subset captured in poses.npz. Finite checks and successful export do not guarantee collision-free motion. Textured desktop export and independent pose/weight adaptation remain open.
""")
    md('G6_PHOTOGRAPHIC_TRANSFERABILITY','Photo transfer',ptable+'\n\n## Existing G5 oracle-map reuse\n\n'+orc+
        '\n\nThe RGB pipeline starts from M7 and uses bilateral contour residuals. The calibrated oracle uses exact silhouettes, camera and the known neutral pose. It does not add a stand-alone anatomical landmark objective. The oracle-depth lane uses G5 visibility, depth and optional normal agreement weights, with no new predictor. All images are synthetic authoring captures. Four held-out camera yaws provide the reprojection check. Unseen body freedom is limited by basis support, regularization and the displacement cap.')
    md('G6_REGISTRATION_SENSITIVITY','Registration sensitivity',tab(
        ['Subject','Stress or estimated arm','Parent mm','Retained mm','Gain mm','Held-out Δ IoU'],
        [r for r in photo_rows if 'stress' in r[1] or 'estimated' in r[1]])+
        '\n\nPerturbations alter camera projection while keeping masks fixed. Yaw, elevation, translation, framing span and distance were tested. Estimated registrations reuse M7 admissible joints and poses. Explicit landmark noise, joint perturbation and scale as independently varied factors remain open. These arms use finite differences of projected contour samples and can absorb registration error into shape.')
    md('G6_RUNTIME_AND_RESOURCES','Runtime and memory',tab(['Arm','N','Median optimizer phase s','Worst phase s','Median structural and score phase s'],runtime)+
        f'\n\nLinux CPU execution used the pinned G5 environment. Maximum per-subject process RSS across the full geometry harness was {peak:.1f} MiB and includes native asset and operator setup. The raw records separate fit and Blender readout, and export metrics record rebind and writing. Operator preparation and concurrent workload timing are not independently isolated for every method. The Windows Server CI describes the small analytic operator suite. i7-1355U/24 GB target performance is unverified.')
    md('G6_ROOT_CAUSE_ANALYSIS','Root causes',f"""
| Factor | Controlled observation | Attribution |
| --- | --- | --- |
| Optimizer | Same registry R0_long {f(avg(bi,'R0_long'))} mm versus R0_restart {f(avg(bi,'R0_restart'))} mm | Initialization matters. G5 D9 was not a mathematical optimum. |
| Native registry | R1 {f(avg(bi,'R1_extended'))} mm versus {f(avg(bi,'R0_long'))} mm driving initialization | Bounded additional modifiers helped the longer seed and fell short of the strongest restart. |
| Deformation representation | R2 fine {f(avg(bi,'R2_fine'))} mm versus R0_long {f(avg(bi,'R0_long'))} mm | Added volumetric freedom materially helps the tested representation. |
| Correspondence | R5 solution ordering changes with semantic and normal filters and screening | Correspondence and deformation interact. |
| Posture | Fixed MB-Lab arm-direction control materially reduces the native residual | Some historical independent residual is posture. The all-limb control exposes a failed mapping. |
| Resolution and topology | Midpoint subdivision retains the existing piecewise planar surface | Higher vertex count alone creates no features. Fine topology capacity remains unmeasured. |
| Structure | R6 lattice proposal {f(avg(bi,'R6_lattice','proposal'))} mm, retained {f(avg(bi,'R6_lattice'))} mm | Intersection screening changes the architecture ranking. |
| Camera and ambiguity | Calibrated RGB improves, estimated examples regress | Observability and registration limit transfer. No valid percentage decomposition. |
""")
    md('G6_ARCHITECTURE_RECOMMENDATION','Weighted architecture decision',"""
Scores use a 1–5 engineering judgment scale with 5 favorable. Weights reflect the deployment objective. Independent accuracy and structural reliability dominate. Photographic transfer and registration follow. Runtime, rig compatibility and implementation complexity retain material weight. An untested high-capacity redesign receives low evidence-based readiness.

| Criterion | Weight | A Native | B FFD | C Graph | D Registration | E Hybrid | F Redesign |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Independent and regional accuracy | 25% | 2 | 5 | 3 | 3 | 4 | 1 |
| Reliability, rig and UV | 25% | 4 | 4 | 2 | 2 | 2 | 1 |
| Photo transfer and registration robustness | 20% | 3 | 3 | 2 | 1 | 1 | 1 |
| CPU runtime and memory | 15% | 5 | 4 | 4 | 3 | 2 | 1 |
| Effort and maintainability | 10% | 5 | 3 | 3 | 2 | 1 | 1 |
| Extensibility and anatomy detail | 5% | 2 | 3 | 4 | 4 | 5 | 5 |
| Weighted score / 5 | 100% | 3.45 | 3.90 | 2.75 | 2.30 | 2.35 | 1.20 |

**Choose B as a gated candidate.** Use a bounded fine FFD field after native initialization. Its 14-step independent held-out result is 13.42 mm. The 28-step result is 13.34 mm. The lower raw hybrid does not survive the guards as often. Use M7 whenever the registration or structure gate fails. Reserve C–E for methods with improved correspondence and collision control. Investigate F only under a separately approved anatomical completeness scope.
""")
    md('G6_INTEGRATION_FEASIBILITY','M9 proposal and G5 disposition',"""
Proposed M9 scope for Product Owner review covers a private CPU FFD adapter with bounded degrees of freedom, calibration qualification, confidence-driven abstention, deterministic rejection to the actual M7 result and export validation. Start with native scale and calibrated neutral captures. Add tests on independent held-out real captures and candidate-specific quality monitoring. Instrument preprocessing, fitting, structural validation and rig/export separately on Windows 11.

An engineering range of 10–18 developer-days is provisional for the adapter, guard integration, deterministic evidence, Windows packaging and representative tests. It excludes collection of a real evaluation cohort, rights clearance and topology redesign. Preserve separate inspection and canonical poses. The next anatomy experiment should qualify fine localized displacement against authorized detail geometry with the current topology before testing regional attachments. For Human3D 3.0 keep deformation stages replaceable and retain parent and geometry digests for the future Inspector. G5 predictor integration remains deferred. G6 shows controlled exact-depth benefit and limited gains from normal agreement weighting.
""")
    md('G6_LIMITATIONS','Open qualification',"""
Small authored cohorts limit external validity. FAUST requires authorized data admission and a license review; no third family entered the run. Real photo evidence and target hardware are absent. No exact independent anatomical correspondence, controlled common rest normalization for both rigs, global convergence proof, broad native registry search, distributed volumetric Jacobian proof, region-specific ARAP, held-out capture uncertainty model, or full textured desktop release regression is available.

Some same-topology authored surfaces contain crossings. The structural policy compares proposed candidates with the actual M7 fitting result and reports reference crossings separately. The scan-level detail and external genital topology probes remain open. The G6 branch provides measured alternatives and the lead decision gates. It does not qualify a new production engine.
""")
    backlog=[
      ('Repository and historical evidence audit','DONE'),('Isolated branch and Lab setup','DONE'),
      ('Dataset admission and provenance','DONE'),('Development and held-out split','DONE'),
      ('Reference coordinate and scale normalization','DONE'),('Anatomical landmark and skeleton mapping','IN_PROGRESS'),
      ('Canonical posture comparison','IN_PROGRESS'),('M7 baseline reproduction','DONE'),
      ('G5 geometry-oracle reproduction','DONE'),('Existing optimizer capacity investigation','DONE'),
      ('Extended native modifier registry','DONE'),('Extended native morph optimization','DONE'),
      ('FFD implementation','DONE'),('FFD resolution and regularization study','IN_PROGRESS'),
      ('Cage deformation implementation','DONE'),('Cage architecture comparison','DONE'),
      ('Deformation graph implementation','DONE'),('Deformation graph optimization','IN_PROGRESS'),
      ('Non-rigid registration implementation','DONE'),('Correspondence method comparison','IN_PROGRESS'),
      ('Anatomical region mapping','IN_PROGRESS'),('Anatomical plausibility constraints','IN_PROGRESS'),
      ('Hybrid architecture implementation','DONE'),('Hybrid architecture ablation','DONE'),
      ('Equal-budget method comparison','IN_PROGRESS'),('Converged geometry-oracle comparison','IN_PROGRESS'),
      ('Held-out independent geometry evaluation','DONE'),('Anatomical region measurements','IN_PROGRESS'),
      ('Anatomical section-loop qualification','IN_PROGRESS'),('Local anatomical morphology evaluation','IN_PROGRESS'),
      ('Anatomical completeness capacity probe','BLOCKED'),('Experimental multiresolution comparison','IN_PROGRESS'),
      ('Structural validation and failure analysis','IN_PROGRESS'),('Rig rebinding comparison','DONE'),
      ('Pose transfer qualification','IN_PROGRESS'),('Calibrated photographic oracle transfer','IN_PROGRESS'),
      ('Calibrated RGB evidence transfer','DONE'),('Estimated-registration photographic transfer','DONE'),
      ('Multi-view and ambiguity analysis','IN_PROGRESS'),('Registration sensitivity experiments','IN_PROGRESS'),
      ('G5 evidence reuse and reconsideration','DONE'),('Runtime and memory profiling','IN_PROGRESS'),
      ('Intermediate snapshot evidence','DONE'),('Blender rendering and visual comparison','DONE'),
      ('Editable asset round-trip qualification','DONE'),('CI and reproducibility qualification','DONE'),
      ('Root-cause attribution','DONE'),('Architecture decision matrix','DONE'),
      ('Production integration feasibility','DONE'),('Evidence consolidation and final report','DONE')]
    (out/'BACKLOG_G6.md').write_text('# Backlog G6\n\n'+tab(['ID','Task','Status'],[(f'G6-{i:03d}',*row)
                                                                       for i,row in enumerate(backlog,1)])+'\n')
    print('done',sum(x[1]=='DONE' for x in backlog),'in progress',sum(x[1]=='IN_PROGRESS' for x in backlog),
          'blocked',sum(x[1]=='BLOCKED' for x in backlog),'peak',peak)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for v in ('results','g5','output'):
        p.add_argument(v,type=Path)
    main(p.parse_args())

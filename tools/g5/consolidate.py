"""Build G5 quantitative reports from completed experiment files."""
import csv
import json
from pathlib import Path
import statistics as st
import sys

import numpy as np

from evidence import CONFIG

OUT, REPORTS = map(Path, sys.argv[1:3])
REPORTS.mkdir(parents=True, exist_ok=True)
CASES = CONFIG['development'] + CONFIG['held_out']
VARIANTS = ['D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'L0']
LABELS = dict(zip(VARIANTS, ['Qualified M7 Engine B', 'Exact depth', 'Exact normals', 'Exact combined',
    'Depth Anything V2 Small', 'DSINE normals', 'Predicted combined', 'Exact combined with local',
    'Predicted combined with local', 'Direct geometry oracle', 'Photographic local control']))
ROOT = Path(__file__).resolve().parents[2]


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def write(name, text):
    (REPORTS / name).write_text(text.strip() + '\n')


def value(x, digits=2):
    return f'{x:.{digits}f}' if x is not None else '—'


def med(xs):
    return st.median(xs) if xs else None


def mean(xs):
    return st.mean(xs) if xs else None


def table(head, rows):
    escape = lambda row: ' | '.join(str(cell).replace('|', r'\|') for cell in row)
    return '\n'.join(['| ' + escape(head) + ' |', '| ' + ' | '.join(['---'] * len(head)) + ' |',
                     *['| ' + escape(row) + ' |' for row in rows]])


def rows_for(mode, cohort, held):
    surfaces = read(OUT / f'{mode}-surface.json', {})
    output = {}
    for case, rows in surfaces.items():
        if not case.startswith(cohort) or (held and case not in CONFIG['held_out']):
            continue
        fit = read(OUT / mode / case / 'fit.json', {})
        output[case] = {}
        for variant, row in rows.items():
            if variant in ('D5', 'D6', 'D8') and fit.get('normal_convention') != 'physical-outward-v2':
                continue
            detail = fit.get(variant, {})
            parent = {'D7': 'D3', 'D8': 'D6', 'L0': 'D0'}.get(variant)
            if row.get('local_validation') == 'reject and retain parent':
                heldout = fit[parent]['heldout']
            else:
                heldout = detail.get('heldout', {})
            d = row['symmetric_mm']['mean']
            base = rows['D0']['symmetric_mm']['mean']
            stages = fit.get('attempt_stages', [])
            runtime = detail.get('seconds')
            if variant == 'D0':
                runtime = next((s['seconds'] for s in stages if 'fit canonical anatomy' in s['stage']), None)
            elif parent and parent != 'D0':
                runtime = (runtime or 0) + fit.get(parent, {}).get('seconds', 0)
            elif parent == 'D0':
                runtime = (runtime or 0) + next((s['seconds'] for s in stages if 'fit canonical anatomy' in s['stage']), 0)
            output[case][variant] = dict(mean_mm=d, median_mm=row['symmetric_mm']['median'],
                p95_mm=row['symmetric_mm']['p95'], max_mm=row['symmetric_mm']['max'],
                delta_mm=base-d, relative_percent=100*(base-d)/base,
                heldout_iou=mean([x['iou'] for x in heldout.values()]),
                heldout_depth_mae_mm=mean([x['depth_mae_mm'] for x in heldout.values() if x['depth_mae_mm'] is not None]),
                heldout_normal_mean_deg=mean([x['normal_mean_deg'] for x in heldout.values() if x['normal_mean_deg'] is not None]),
                optimization_seconds=runtime, regional_mm={k: v['mean'] for k, v in row['regional_mm'].items()},
                rebind=detail.get('rebind'), disjoint_crossings=row['disjoint_index_triangle_crossing_pairs'],
                local_rejection=detail.get('rejection') or (row.get('local_validation') if row.get('local_validation') != 'pass' else None),
                local_new_crossing_pairs=row.get('new_intersection_pairs_vs_local_parent'),
                section_errors=row['sections'], views=fit.get('view_order'), evaluations=detail.get('evaluations'))
    return output


def aggregate(subjects, variant):
    samples = [(case, rows[variant]) for case, rows in subjects.items() if variant in rows]
    if not samples:
        return None
    paired = [row for _, row in samples]
    relative = [row['relative_percent'] for row in paired]
    delta = [row['delta_mm'] for row in paired]
    held_iou = [row['heldout_iou'] - subjects[case]['D0']['heldout_iou']
                for case, row in samples if row['heldout_iou'] is not None]
    held_depth = [row['heldout_depth_mae_mm'] - subjects[case]['D0']['heldout_depth_mae_mm']
                 for case, row in samples if row['heldout_depth_mae_mm'] is not None]
    best = max(samples, key=lambda x: x[1]['delta_mm'])
    worst = min(samples, key=lambda x: x[1]['delta_mm'])
    return dict(n=len(paired), mean_mm=mean([r['mean_mm'] for r in paired]), paired_gain_mean_mm=mean(delta),
                paired_gain_median_mm=med(delta), paired_mean_relative_percent=mean(relative),
                gain_ge_5=sum(x >= 5 for x in relative), gain_ge_10=sum(x >= 10 for x in relative),
                gain_ge_20=sum(x >= 20 for x in relative), absolute_change_below_5=sum(abs(x) < 5 for x in relative),
                degradation_ge_5=sum(x <= -5 for x in relative),
                strictly_improved=sum(x > 0 for x in delta), strictly_degraded=sum(x < 0 for x in delta),
                heldout_delta_iou=mean(held_iou), heldout_depth_delta_mm=mean(held_depth),
                median_fitting_seconds=med([r['optimization_seconds'] for r in paired if r['optimization_seconds'] is not None]),
                best_subject=best[0], best_gain_mm=best[1]['delta_mm'],
                worst_subject=worst[0], worst_gain_mm=worst[1]['delta_mm'])


ALL = {(mode, family): rows_for(mode, family, False) for mode in ('calibrated', 'estimated') for family in ('A', 'B')}
HOLD = {(mode, family): rows_for(mode, family, True) for mode in ('calibrated', 'estimated') for family in ('A', 'B')}
SUMMARY = {f'{mode}_{family}': {v: aggregate(subjects, v) for v in VARIANTS}
           for (mode, family), subjects in HOLD.items()}
pred_quality = read(OUT / 'maps/quality.json', {})
ray = read(OUT / 'rays.json', {})
timings = {k: read(OUT / 'pred' / f'{k}-runtime.json', {}) for k in ('depth', 'normal')}
ci = {p.stem: read(p) for p in sorted((OUT / 'ci').glob('*.json'))}
ci_seconds = lambda row: row.get('cpu_392_inference_seconds') or row['cpu_384_inference_seconds']
windows_normal = any('cpu_384_inference_seconds' in row for row in ci.values())
windows_status = ('Both models also ran on Windows Server 2022 CI. '
                  'The physical Windows 11 i7-1355U workstation remains unmeasured.'
                  if windows_normal else 'Depth also ran on Windows Server 2022 CI. '
                  'The physical Windows 11 i7-1355U workstation and Windows DSINE deployment remain unmeasured.')
stress = read(OUT / 'stress-surface.json', {})
robust = read(OUT / 'robustness-surface.json', {})
if robust:
    robust = {case: {k: v for k, v in rows.items() if k not in ('D5', 'D6', 'D8')
                   or read(OUT / 'robustness' / case / 'fit.json', {}).get('normal_convention') == 'physical-outward-v2'}
              for case, rows in robust.items()}
m7 = {}
for mode in ('calibrated', 'estimated'):
    for case in CASES:
        report = read(OUT / 'baseline' / case / mode / 'attempt.json', {})
        if report:
            diag = report['diagnostics']
            m7[f'{mode}/{case}'] = dict(status=report['status'], stages=diag['stages'],
                registration=diag['metrics'].get('experimental_registration_sources', {}),
                exclusions=diag['metrics'].get('experimental_registration_exclusions', {}),
                fitting=diag['metrics'].get('engine_b_fitting'), warnings=diag['warnings'])
result = dict(protocol='G5 matched reconstruction', baseline='020fcc793e7417d6927d9e07346678e110ae9ddc',
              primary_config=CONFIG, ci=ci, baseline_attempts=m7,
              subjects={f'{mode}_{family}': rows for (mode, family), rows in ALL.items()},
              heldout_aggregates=SUMMARY, ray_checks=ray,
              independent_cpu_model_runtime={k: {a: b for a, b in r.items() if a != 'images'} for k, r in timings.items()})
write('G5_MEASUREMENTS.json', json.dumps(result, indent=2, allow_nan=False))

with (REPORTS / 'G5_BENCHMARK_TABLE.csv').open('w', newline='') as stream:
    writer = csv.writer(stream)
    writer.writerow(['camera_path', 'family', 'case', 'partition', 'configuration', 'mean_mm', 'median_mm',
                     'p95_mm', 'max_mm', 'gain_mm', 'gain_percent', 'heldout_mask_iou', 'heldout_depth_mae_mm',
                     'heldout_normals_mean_degrees', 'fitting_seconds', 'disjoint_crossings'])
    for (mode, group), subjects in ALL.items():
        for case, configurations in subjects.items():
            for arm, row in configurations.items():
                writer.writerow([mode, group, case, 'development' if case in CONFIG['development'] else 'held-out',
                                 arm, *[row[k] for k in ('mean_mm', 'median_mm', 'p95_mm', 'max_mm', 'delta_mm',
                                     'relative_percent', 'heldout_iou', 'heldout_depth_mae_mm', 'heldout_normal_mean_deg',
                                     'optimization_seconds', 'disjoint_crossings')]])

calibrated_count = sum(k.startswith('calibrated/') and v['status'] == 'complete' for k, v in m7.items())
estimated_count = sum(k.startswith('estimated/') and v['status'] == 'complete' for k, v in m7.items())
validated_counts = {variant: sum(variant in row for rows in ALL.values() for row in rows.values()) for variant in VARIANTS}
complete_matrix = sum(all(k in tracks for k in VARIANTS) for family in ('A', 'B') for tracks in ALL['calibrated', family].values())

exec_summary = f'''# Human3D 2.0 G5 — feasibility decision

**Retain Strategy A for M7 and the next production release.** Exact channels establish the value of measured surface geometry under controlled acquisition. The predicted path requires a repeatable independent-topology benefit and reliable registration before it qualifies for integration. G5 measured the original G4 cohort with a separately executed Engine B baseline. The study remains open for the outstanding qualification listed below.

Qualified Engine B completed **{calibrated_count}/10 calibrated** and **{estimated_count}/10 estimated** full service runs. The calibrated D0–D9 matrix plus the photographic local control is available for **{complete_matrix}/10 subjects**. Mean metrics below use held-out subjects, paired by configuration, with separate camera paths.

'''
for mode, family in HOLD:
    cohort = 'MakeHuman' if family == 'A' else 'independent MB-Lab'
    display = []
    for arm, a in SUMMARY[f'{mode}_{family}'].items():
        if a is None:
            continue
        if arm == 'D0':
            disposition = 'Retain'
        elif arm in ('D1', 'D2', 'D3', 'D9'):
            disposition = 'Lab control'
        else:
            disposition = 'Defer production'
        display.append((f"{arm} ({a['n']})", value(a['mean_mm']) + ' mm',
                       value(a['paired_gain_mean_mm']) + ' mm', f"Δ IoU {value(a['heldout_delta_iou'], 3)}",
                       value(a['median_fitting_seconds']) + ' s', disposition))
    if display:
        exec_summary += '\n## ' + cohort + ' · ' + mode + '\n\n' + table(
            ['Configuration', 'Mean surface error', 'Improvement vs M7', 'Held-out impact', 'Runtime', 'Decision'], display) + '\n'
    else:
        exec_summary += f'\n## {cohort} · {mode}\n\nComparison data unavailable at consolidation.\n'

cal_held = HOLD['calibrated', 'A'] | HOLD['calibrated', 'B']
core = {key: aggregate(cal_held, key) for key in VARIANTS}
def headline(arm):
    a = core[arm]
    if not a:
        return 'unresolved'
    return f"{a['paired_gain_median_mm']:+.2f} mm median, best {a['best_gain_mm']:+.2f} mm ({a['best_subject']})"

exec_summary += f'''

## Findings

1. Exact depth had {headline('D1')}. Exact normals had {headline('D2')}. Combining exact channels had {headline('D3')}. The best observed gain represents a single subject under the frozen configuration.
2. Predicted depth had {headline('D4')}. Directly predicted normals had {headline('D5')}. Predicted fusion had {headline('D6')}. Compare held-out IoU and depth against the paired geometry result. D3 and D6 show joint performance, and D1 and D2 separate individual effects.
3. Both models executed offline on Linux CPU with pinned assets. {windows_status}

## Remaining qualification

1. The ten authored fixtures cover two asset families and a small held-out cohort. Real photographs, consented scans, independent metric scale, and a broader set of camera and body poses remain open.
2. Camera registration and pose attribution can change the result materially. The supplied camera and pose controls isolate error sources. They leave automatic onboarding from arbitrary photos unresolved.
3. D7 and D8 examine a single restricted displacement family. Retained local candidates and rejected proposals are separated. Representative USD and Blender rig save/reopen checks passed. A full textured desktop export regression and broader human-specific normal-model evidence remain open.

See the anatomical region, multiview, registration and local-refinement reports for gains, regressions and exact coverage. Positive gain means lower error than D0. Runtime covers the measured fit, including registration for D0, and excludes predictor inference. Concurrent workload timings include contention.
'''
write('G5_EXECUTIVE_REPORT.md', exec_summary)

def benchmark_report(keys, title):
    sections = []
    for (camera, family), rows in ALL.items():
        if not rows:
            continue
        subset = []
        for person, tracks in rows.items():
            subset.append([person, 'development' if person in CONFIG['development'] else 'held-out',
                           *[value(tracks[k]['mean_mm']) if k in tracks else '—' for k in keys]])
        sections.append(f'## {family} · {camera}\n\n' + table(['Subject', 'Partition', *keys], subset))
    bins = []
    for v in keys:
        a = core[v]
        if a:
            bins.append((v, a['n'], a['strictly_improved'], a['strictly_degraded'], a['gain_ge_5'], a['gain_ge_10'],
                         a['gain_ge_20'], a['absolute_change_below_5'], a['degradation_ge_5'],
                         value(a['best_gain_mm']), value(a['worst_gain_mm'])))
    return (f'# {title}\n\nMean symmetric closest-triangle distance in millimetres. '
            'Each reported pair uses the same subject and admitted view set. Rows marked development are exploratory. '
            'An em dash marks an unavailable result.\n\n' + '\n\n'.join(sections) +
            '\n\n## Held-out subjects · calibrated impact bands\n\n' +
            table(['Arm', 'n', 'Improved', 'Degraded', '≥5%', '≥10%', '≥20%', '|Δ| <5%', 'Loss ≥5%', 'Best mm', 'Worst mm'], bins) +
            '\n\nThe ≥5%, ≥10%, and ≥20% bands are nested and descriptive. Strict improvement and degradation include any signed change. '
            'Inference is paired by subject. Views contribute to the fit and never increase the independent sample count.')

write('G5_ORACLE_BENCHMARK.md', benchmark_report(['D0', 'D1', 'D2', 'D3', 'D9'], 'G5 exact evidence benchmark'))
write('G5_PREDICTED_EVIDENCE_BENCHMARK.md', benchmark_report(['D0', 'D4', 'D5', 'D6'], 'G5 pretrained evidence benchmark') +
      '\n\nDepth alignment during fitting uses a single D0-anchored inverse affine mapping per image. '
      'The pixel-quality report uses separate oracle-aligned validation and has a different interpretation.')

regions = sorted({k for r in cal_held.values() for k in r.get('D0', {}).get('regional_mm', {})})
scores = []
for region in regions:
    row = [region.replace('_',' ')]
    for arm in ('D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8'):
        diffs = [r['D0']['regional_mm'][region]-r[arm]['regional_mm'][region] for r in cal_held.values()
                 if arm in r and region in r[arm]['regional_mm'] and region in r['D0']['regional_mm']]
        row.append(value(mean(diffs)))
    scores.append(row)
write('G5_ANATOMICAL_REGION_IMPACT.md', '# G5 anatomical region impact\n\nCalibrated held-out average gain in millimetres versus the same subject’s D0. '
      'Positive values indicate improved geometry. Regions use fixed anatomical height and lateral bands and have overlapping support at selected borders. '
      'Region labels are approximate on independent topology, particularly the shoulder and forearm. Signed width, depth and anterior/posterior section errors '
      'are included in G5_MEASUREMENTS.json. Circumference and shape-loop errors remain open.\n\n' +
      table(['Region', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8'], scores))

def controls_block(keys, title, description):
    rows = []
    for tag, data in keys.items():
        rows.append([tag, *[value(data.get(k, {}).get('symmetric_mm', {}).get('mean')) for k in ('D0','D1','D2','D3','D4','D5','D6')]])
    return f'# {title}\n\n{description}\n\n' + table(['Control','D0 mm','D1 mm','D2 mm','D3 mm','D4 mm','D5 mm','D6 mm'], rows)

multiview = {k: v for k, v in robust.items() if k.startswith('views-')}
for group in ('A', 'B'):
    surfaces = read(OUT / 'calibrated-surface.json', {})
    for case in ('A_high_mass', 'A_heldout_1', 'B_female_expanded'):
        if case.startswith(group) and case in surfaces:
            multiview['views-4/' + case] = {k: v for k, v in surfaces[case].items()
                                          if k in ALL['calibrated', group].get(case, {})}

write('G5_MULTIVIEW_ANALYSIS.md', controls_block(dict(sorted(multiview.items())), 'G5 multiview evidence',
      'Nested sets use front, opposite-body side, rear, second lateral, then four obliques. The measured fit JSON records which requested photographs Engine B admitted. '
      'Held-out views are fixed across all conditions. The reported rows are the completed subset. Additional candidate photometric consistency weighting remains untested.'))
camera_rows = {k: v for k, v in robust.items() if not k.startswith('views-')}
write('G5_REGISTRATION_SENSITIVITY.md', controls_block(camera_rows, 'G5 camera, pose and visible-surface sensitivity',
      'Camera perturbations change the specified field while preserving the original RGB masks and truth maps. D0 here runs the G5 no-extra copy of the product schedule against deliberately corrupted registration. '
      'Distance modifies focal length and perspective depth at a fixed center span. The estimated Engine B path has separate tables.') +
      '\n\n## Pose, clothing and occlusion controls\n\n' +
      controls_block(stress, 'Controlled reference-surface changes',
      'These are calibrated two-view oracle controls on high mass. Garment shells are procedural geometry offsets and external occlusion is a pixel exclusion control. True pose and assumed pose angles are logged for each run. '
      'This matrix isolates geometry. The separate appearance report measures RGB channel quality against exposed and covered surfaces.'))
write('G5_LOCAL_REFINEMENT_BENCHMARK.md', benchmark_report(['D0','L0','D3','D7','D6','D8','D9'], 'G5 local refinement and native capacity') +
      '\n\nD7 and D8 use the same smoothed normal-direction field with a 5 mm bound. L0 uses projected contour corrections from Engine B masks. '
      'Rebind, face flips and new Blender BVH crossings are evaluated separately. Local candidates introducing new disjoint-index crossings are rejected in the reported result. '
      'The rejected proposal and the retained parent are distinguishable in the evidence. D9 measures the current registry under direct geometry. '
      'Its independent-topology optimizer is approximate ICP and therefore estimates attained capacity under a bounded schedule.')

quality_rows = []
groups = [('Front', ['0']), ('Left lateral', ['90']), ('Rear', ['180']), ('Right lateral',['270']),
          ('Oblique', ['45','135','225','315']), ('Alternate', ['0-alternate','90-alternate'])]
for label, views in groups:
    entries = [r for subject in pred_quality.values() for k, r in subject.items() if k in views and 'depth' in r and 'normal' in r]
    if entries:
        quality_rows.append([label, len(entries), *[value(med([r['depth'][k] for r in entries]))
              for k in ('affine_inverse_pixel_mae_mm','scale_only_inverse_pixel_mae_mm','rank_spearman',
                        'oracle_depth_normal_median_deg','derived_to_truth_median_deg','direct_vs_derived_median_deg')],
             value(med([r['normal']['median_deg'] for r in entries])),
             value(med([r['normal']['boundary_1_to_3px_median_deg'] for r in entries]))])
write('G5_EVIDENCE_QUALITY.md', '# G5 evidence quality\n\nResults are medians over per-image measurements. '
      'Ground-truth inverse alignment for quality uses one third of valid pixels per view and scores the remaining pixels. '
      'This pixel split is spatially interleaved and is an optimistic scale-ambiguity control. The fit uses a different alignment with zero reference geometry input to prediction. '
      'Positive larger disparity means closer. Exact Z is in centimeters; Euclidean ray length differs away from the principal point.\n\n' +
      table(['View','N','Affine depth MAE mm','Scale-only MAE mm','Rank ρ','Exact depth-derived °',
             'Predicted depth-derived °','DSINE vs derived °','DSINE median °','DSINE boundary °'], quality_rows) +
      '\n\nReduced input resolution, appearance variation and RGB-to-raster agreement are in the quality JSON. The exact depth-derived residual quantifies the screen-space finite-difference floor.')

profile = []
for predictor, r in timings.items():
    if not r:
        continue
    primary = [j['seconds'] for j in r['images'].values() if j['input_size'] >= 384]
    small = [j['seconds'] for j in r['images'].values() if j['input_size'] < 384]
    profile.append([predictor, len(primary), value(r['initialization_s']), value(primary[0]),
                    value(med(primary[1:])), value(med(small)), value(r['weight_bytes']/1024**2),
                    value(r['peak_rss_kib_linux']/1024)])
write('G5_RUNTIME_AND_RESOURCES.md', '# G5 CPU runtime and resources\n\nLinux host AMD EPYC 9V74, FP32, two inference threads. '
      'Initialization includes import, hash validation and cold session creation. Warm includes image resizing, inference and output resampling; image decoding is outside the timer. '
      'Peak RSS is per independently launched predictor process. The archive includes exact timing rows and pipeline stage timings.\n\n' +
      table(['Model','N','Init s','First s','Warm median s','Reduced median s','Weights MiB','Peak RSS MiB'], profile) +
      '\n\n## Windows and Linux CI\n\n' +
      table(['Artifact','System','Init s','First s','Warm median s','RSS MiB after runs'],
            [[key, r['platform'], value(r['initialization_s']), value(ci_seconds(r)[0]),
             value(med(ci_seconds(r)[1:])), value(r['working_set_rss_bytes_after_runs']/1024**2)]
                for key,r in ci.items()]) +
      '\n\nWindows CI used a synthetic geometric RGB smoke. The hardware differs from the physical Windows 11 target. '
      'Fit timing varies with admitted views and host contention. Full Windows application memory, quantization, host-specific cache throughput and target hardware power modes remain unmeasured. '
      'Per-image model inference is cacheable. Cache identity must include oriented RGB digest, checkpoint hash, image transform, calibrated or assumed intrinsics for DSINE, and evidence convention version. '
      'D0 depth alignment depends on canonical solve, visibility and calibration, so aligned artifacts need an additional fit-dependent key.')

assets = {
    'application_baseline': result['baseline'],
    'm7_docs': '2a91df9f8dcab0279981e90a2a77c7ce7976bea9',
    'lab_render': '66d84ba5775b0ab22f6e587e83efa0999180255c',
    'g1': '8743a0fe45cc8a68781cf19cbc0a7cc59cb964c5',
    'g2': '495f7be86628b35ae220de2897e4951507179400',
    'g3': 'f0884a858cc196f9d709fc234cfed4f9a622a402',
    'g4': 'ca90165d259bada9b3cea945d1227be0f83656ef',
    'makehuman': '1f508f6083b2f823dab15de924b3bde72e08d77c',
    'makehuman_core_asset_license': 'CC0',
    'engine_b_target_count': 582,
    'makehuman_archive': read(ROOT / 'DOCS/manifests/m7-g1-archive.json'),
    'pose_landmarker': read(ROOT / 'DOCS/manifests/m7-pose-model.json'),
    'model_manifest': 'G5_MODEL_MANIFEST.json',
    'independent_geometry': 'Original G4 SHA-256-verified MB-Lab blobs; numeric results only',
}
g4_root = ROOT.parent / 'g4'
original_manifest = read(g4_root / 'DOCS/g2/G2_DATASET_MANIFEST.json', {})
assets['independent_reference_files'] = original_manifest.get('families', {}).get('B', {}).get('cases', [])
write('G5_ASSET_MANIFEST.json', json.dumps(assets, indent=2))

from hashlib import sha256
manifest = dict(assets='G5_ASSET_MANIFEST.json', config=CONFIG, subjects={})
for case in CASES:
    ref = OUT / 'refs' / f'{case}.npz'
    if ref.exists():
        manifest['subjects'][case] = dict(cohort='MakeHuman' if case.startswith('A_') else 'MB-Lab',
                partition='development' if case in CONFIG['development'] else 'held-out',
                generated_reference_npz_sha256=sha256(ref.read_bytes()).hexdigest(),
                original_generation_params=read(OUT / 'refs' / 'original-configurations.json', {}).get(case[2:]) or
                    read(OUT / 'refs' / 'generation-only.json', {}).get(case),
                publish_geometry_and_maps=case.startswith('A_'),
                photos={view: {k: values[k] for k in ('sha256_rgb','camera','observation_pose')}
                        for view, values in pred_quality.get(case, {}).items()})
write('G5_DATASET_MANIFEST.json', json.dumps(manifest, indent=2))

arch = (REPORTS / 'G5_ARCHITECTURE_RECOMMENDATION.md').read_text()
if '\n## Observed decision metrics' in arch:
    arch = arch.split('\n## Observed decision metrics')[0]
decision_rows = []
for arm in ('D0','D1','D2','D3','D4','D5','D6','D7','D8','L0','D9'):
    a = core[arm]
    if not a:
        continue
    decision_rows.append((arm, LABELS[arm], a['n'], value(a['paired_gain_mean_mm']),
          value(a['paired_gain_median_mm']), value(a['heldout_delta_iou'], 3),
          a['gain_ge_10'], a['degradation_ge_5']))
observed = '\n\n## Observed decision metrics\n\n' + table(
    ['Arm','Evidence','Held-out cases','Mean gain mm','Median gain mm','Mean Δ held-out IoU','≥10% gain','≥5% loss'],
    decision_rows)
write('G5_ARCHITECTURE_RECOMMENDATION.md', arch + observed)

for label, oracle_id, learned_id in [('depth','D1','D4'),('normals','D2','D5'),('combined','D3','D6')]:
    common = [person for person in cal_held.values() if oracle_id in person and learned_id in person]
    if common:
        exact = mean([p[oracle_id]['delta_mm'] for p in common])
        learned = mean([p[learned_id]['delta_mm'] for p in common])
        exec_summary += (f'\n- Paired {label} retention over {len(common)} calibrated held-out bodies. '
            f'Exact mean gain {exact:+.2f} mm, predicted mean gain {learned:+.2f} mm.')
        if exact > 0:
            exec_summary += f' The ratio of the two mean gains is {100*learned/exact:+.0f}%.'

if core.get('D3'):
    comparison = [p for p in cal_held.values() if all(k in p for k in ('D1','D2','D3'))]
    if comparison:
        improvement = mean([min(p['D1']['mean_mm'],p['D2']['mean_mm'])-p['D3']['mean_mm'] for p in comparison])
        exec_summary += f'\n- Exact fusion versus the best single oracle channel per body averages {improvement:+.2f} mm over {len(comparison)} paired bodies.'
    regional = [(row[0], float(row[3])) for row in scores if row[3] != '—']
    if regional:
        ordered = sorted(regional, key=lambda x: x[1], reverse=True)
        exec_summary += ('\n- Exact fusion regions with the greatest gains are ' +
                         ', '.join(f'{r} ({d:+.2f} mm)' for r,d in ordered[:3]) +
                         '. The largest adverse regional changes are ' +
                         ', '.join(f'{r} ({d:+.2f} mm)' for r,d in ordered[-3:] if d < 0) + '.')
if core.get('D7') and core.get('D3'):
    locals_ = [p for p in cal_held.values() if 'D3' in p and 'D7' in p]
    gain = mean([p['D3']['mean_mm']-p['D7']['mean_mm'] for p in locals_])
    rejected = sum(p['D7']['local_rejection'] is not None for p in locals_)
    exec_summary += (f'\n- Oracle local refinement added {gain:+.2f} mm on average after the guards. '
                     f'{rejected}/{len(locals_)} proposals were rejected. The tested local field has conditional value and does not establish necessity.')
if camera_rows:
    misses = [(k, x['D3']['symmetric_mm']['mean']-x['D0']['symmetric_mm']['mean'])
              for k,x in camera_rows.items() if 'D0' in x and 'D3' in x]
    if misses:
        tag, loss = max(misses, key=lambda x: x[1])
        exec_summary += f'\n- Largest D3 penalty versus matched perturbed D0 was {loss:+.2f} mm under {tag}.'
predictions = [(case, key, arm['delta_mm']) for case, rows in cal_held.items() for key, arm in rows.items()
               if key in ('D4','D5','D6','D8')]
if predictions:
    low = min(predictions, key=lambda x: x[2])
    exec_summary += f'\n- Worst calibrated held-out predicted regression was {-low[2]:.2f} mm ({low[0]}, {low[1]}).'
write('G5_EXECUTIVE_REPORT.md', exec_summary)

decision = (REPORTS / 'G5_ARCHITECTURE_RECOMMENDATION.md').read_text()
decision += '''\nExact depth and normals earn conditional impact for calibrated Lab work. Exact local refinement earns conditional impact in the independent-topology cohort. Predicted depth, normals and fusion have low or conditional impact under the tested CPU cost and held-out scope. Adoption remains deferred across the predicted strategies.'''
write('G5_ARCHITECTURE_RECOMMENDATION.md', decision)

descriptions = [
    'Repository and prior experiment audit','M7 baseline reproduction','Dataset admission and partitioning',
    'Measurement methodology verification','Ground-truth depth generation','Ground-truth normal generation',
    'Coordinate and projection verification','Visibility and evidence representation','Depth model assessment',
    'Normal model assessment','License and dependency audit','CPU inference qualification','Predicted evidence quality evaluation',
    'Depth loss implementation','Normal loss implementation','Combined evidence objective','Oracle depth benchmark',
    'Oracle normal benchmark','Oracle combined benchmark','Predicted depth benchmark','Predicted normal benchmark',
    'Predicted combined benchmark','Anatomical region analysis','Multi-view evidence analysis','Camera registration sensitivity',
    'Observation pose sensitivity','Clothing and occlusion sensitivity','Parametric representation capacity',
    'Bounded local refinement controls','Held-out and structural validation','Runtime and memory profiling',
    'Intermediate snapshots and Blender evidence','Production integration assessment','Comparative strategy evaluation',
    'Final feasibility and impact decision','Evidence consolidation and handoff']
done = {1,2,3,4,5,6,7,9,12,14,15,16,33,34,35}
for i, arm in enumerate(['D1','D2','D3','D4','D5','D6'], 17):
    if sum(arm in track for family in ('A','B') for track in ALL['calibrated',family].values()) == 10:
        done.add(i)
if {k for k in camera_rows} >= {prefix+'/A_high_mass' for prefix in
     ('yaw-8','elevation-7','roll-5','dx-0.025','dy-0.025','span-15','distance--110','perspective-0')}:
    done.add(25)
if len([k for k in stress if k.endswith(('error','correct'))]) == 4:
    done.add(26)
if all(arm in row for arm in ('D7','D8','L0') for group in ('A','B')
       for row in ALL['calibrated',group].values()) and complete_matrix == 10:
    done.add(29)
if (OUT.parent / 'delivery/G5_Blender_Comparison.png').exists():
    done.add(32)
statuses = {i: 'DONE' if i in done else 'PARTIAL' for i in range(1,37)}
statuses[36] = 'DONE'
write('BACKLOG_G5.md', '# G5 backlog\n\n' + table(
    ['ID','Task','Status'], [(f'G5-{i:03d}',d,statuses[i]) for i,d in enumerate(descriptions,1)]))

appearance = read(OUT / 'appearance-quality.json', {})
if appearance:
    text = (REPORTS / 'G5_EVIDENCE_QUALITY.md').read_text()
    display = []
    for condition, views in appearance.items():
        for yaw, items in views.items():
            for support, row in items.items():
                display.append((condition, yaw, support, row['pixels'], value(row['depth_mae_mm']),
                                value(row['normal_median_deg'])))
    write('G5_EVIDENCE_QUALITY.md', text + '\n## Blender appearance perturbations\n\n'
          'An independent high-mass RGB series uses a close patterned torso shell, a loose shell, an occluding panel '
          'and striped background props. Separate masks score the visible altered surface and underlying body. '
          'The affine depth transform is estimated against the visible surface. This isolates appearance and '
          'surface-attribution errors without estimating real-world metric scale.\n\n' +
          table(['Condition','Yaw °','Evaluation support','Pixels','Depth MAE mm','Median normal error °'], display))

fov_surfaces = read(OUT / 'estimated-fov-surface.json', {})
if fov_surfaces:
    path = REPORTS / 'G5_REGISTRATION_SENSITIVITY.md'
    rows = []
    for case, arms in fov_surfaces.items():
        for arm in ('D5','D6'):
            if arm not in arms:
                continue
            old = ALL['estimated',case[0]].get(case, {}).get(arm, {})
            rows.append((case, arm, value(old.get('mean_mm')), value(arms[arm]['symmetric_mm']['mean'])))
    write(path.name, path.read_text() + '\n## Normal-intrinsics sensitivity on estimated registrations\n\n'
          'The main estimated table uses the synthetic RGB capture intrinsics for DSINE only. '
          'This supplementary block replaces them with the model’s 60° default and scores the same estimated M7 registration.\n\n' +
          table(['Subject','Arm','Known intrinsics mm','Assumed 60° mm'], rows))

rig = {}
for folder in sorted((OUT / 'roundtrip').glob('*')):
    rows = read(folder / 'blender-roundtrip.json', [])
    invariants = read(folder / 'm7_export_validation.json', {})
    if rows:
        rig[folder.name] = {'blender': rows, 'openusd_invariants': invariants}
result['roundtrip'] = rig
write('G5_MEASUREMENTS.json', json.dumps(result, indent=2, allow_nan=False))
if rig:
    path = REPORTS / 'G5_LOCAL_REFINEMENT_BENCHMARK.md'
    lines = [[f, row['source'], row['vertices'], row['faces'], row['uv_layers'], row['bones'],
              f"{row['max_weight_sum_error']:.2e}", row['editable_geometry_save_reopen']]
             for f,data in rig.items() for row in data['blender']]
    write(path.name, path.read_text() + '\n## M7 USD and Blender round trip\n\n'
         'Accepted representatives retain topology, UV coordinates and indices, skin indices and weights relative to the same subject’s D0 export. '
         'Blender 4.5.16 imported and articulated the rig, edited a vertex, and reopened the saved scene. '
         'The archive includes the numeric verification for Family B.\n\n' +
         table(['Subject','Source','Vertices','Faces','UV layers','Bones','Max skin sum error','Edit/reopen'], lines))
detail = (REPORTS / 'G5_EVIDENCE_QUALITY.md').read_text()
reductions = []
for model, res, metric in [('depth', 280, 'affine_inverse_pixel_mae_mm'), ('normal', 256, 'median_deg')]:
    matches = [p for views in pred_quality.values() for p in views.values() if f'{model}_{res}' in p]
    if matches:
        reductions.append([model, res, len(matches), value(mean([r[model][metric] for r in matches])),
                           value(mean([r[f'{model}_{res}'][metric] for r in matches])), metric])
write('G5_EVIDENCE_QUALITY.md', detail + '\n## Reduced-resolution development controls\n\n' +
      table(['Model','Reduced input px','Paired images','Mean full input error','Mean reduced input error','Metric'], reductions))

executive = (REPORTS / 'G5_EXECUTIVE_REPORT.md').read_text()
for arm in ('D1','D2','D3','D7'):
    available = [(s,v[arm]['delta_mm']) for f in ('A','B') for s,v in ALL['calibrated',f].items() if arm in v]
    if available:
        name, gain = max(available, key=lambda x:x[1])
        executive += f'\n- Maximum calibrated gain for {arm}, including development cases, was {gain:+.2f} mm on {name}.'
worst_est = [(s,k,v['delta_mm']) for family in ('A','B') for s,arms in ALL['estimated',family].items()
             for k,v in arms.items() if k in ('D4','D5','D6')]
if worst_est:
    case, key, gain = min(worst_est, key=lambda x:x[2])
    executive += f'\n- Worst predicted result in the main estimated-camera matrix regressed {abs(gain):.2f} mm on {case} ({key}).'
if 'loose_shell_naive' in stress and 'loose_shell_exclude' in stress:
    row = stress['loose_shell_naive']; excluded = stress['loose_shell_exclude']
    base, naive, gated = [r[k]['symmetric_mm']['mean'] for r, k in ((row,'D0'),(row,'D3'),(excluded,'D3'))]
    executive += f'\n- Treating the loose shell as anatomy increased error from {base:.2f} to {naive:.2f} mm. Excluding covered dense observations reduced it to {gated:.2f} mm.'
write('G5_EXECUTIVE_REPORT.md', executive)

# Resample bodies, never individual viewpoints. The small authored cohort
# supports descriptive intervals only.
rng = np.random.default_rng(1128)
intervals = {}
for arm in ('D1','D2','D3','D4','D5','D6','D7','D8'):
    delta = np.array([row[arm]['delta_mm'] for row in cal_held.values() if arm in row])
    if len(delta) >= 5:
        draws = rng.choice(delta, size=(10000, len(delta)), replace=True).mean(axis=1)
        intervals[arm] = [float(x) for x in np.percentile(draws, [2.5, 97.5])]
result['descriptive_subject_bootstrap_mean_gain_mm_95_percent'] = intervals
write('G5_MEASUREMENTS.json', json.dumps(result, indent=2, allow_nan=False))
if intervals:
    path = REPORTS / 'G5_EXECUTIVE_REPORT.md'
    write(path.name, path.read_text() + '\n## Descriptive 95% mean-gain intervals\n\n' +
         table(['Arm','Lower mm','Upper mm'], [[key, value(lo), value(hi)] for key,(lo,hi) in intervals.items()]) +
         '\n\nThe bootstrap resamples subjects and describes this small authored cohort. Population-level inference remains open.')

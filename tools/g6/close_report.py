"""Add final volume, posture and CI provenance to the G6 handover."""
import argparse
import json
from pathlib import Path
from statistics import mean
from zipfile import ZipFile

from report import tab


def main(root, docs, g5):
    def append(name, txt):
        p=docs/('G6_'+name+'.md')
        p.write_text(p.read_text()+txt.strip()+'\n')
    vol=json.loads((root/'volume-surface.json').read_text())
    held=('B_female_expanded','B_male','B_male_expanded')
    values=[]
    for case, d in vol.items():
        r=d['R2_volume_checked']
        fit=json.loads((root/'volume'/case/'fit.json').read_text())['study']['R2_volume_checked']
        minimum=fit['combined_determinant_min_by_surface_fraction'][str(r['fraction_vs_parent'])]
        assert minimum>.1
        values.append([case,f"{d['D0']['accepted']['mean']:.2f}",f"{r['accepted']['mean']:.2f}",
                       f"{fit['proposal_full_min_det']:.3f}",f"{minimum:.3f}",
                       f"{fit['pre_bvh_accepted_fraction']*r['fraction_vs_parent']:.4f}"])
    combined=mean(vol[c]['R2_volume_checked']['accepted']['mean'] for c in held)
    append('FFD_BENCHMARK','''
## Single-field determinant guard

The reported fine FFD uses displacement clipping and is screened against surface crossings and rig constraints. Its reembedded-field diagnostic showed nonpositive samples on some bodies, including B_female_expanded. The additional candidate fits one unclipped spline field from the M7 anchor to the retained fine-FFD result. A global displacement scale clears 3,375 sampled determinants above 0.10, then Blender performs its independent crossing screen. Samples cover the interior of the volume. They provide no continuous determinant proof.

'''+tab(['Subject','M7 mm','Retained guarded mm','Full-field min det','Retained min det','Combined scale'],values)+
    f'\n\nIndependent held-out mean after determinant and surface screens is **{combined:.2f} mm**.')
    append('EXECUTIVE_REPORT',f'''
## Determinant and CI disposition

The fine FFD surface benchmark remains **13.42 mm**. A separate single spline field with a sampled determinant guard and crossing check retains **{combined:.2f} mm** on the same three independent held-out subjects. This identifies a concrete stability cost to carry into M9. The selected architecture needs direct coefficient bounds and conservative determinant validation before enabling end-user volume deformation.

The qualified M7 revision is `020fcc793e7417d6927d9e07346678e110ae9ddc`. The CPU operator subset passed on Linux and Windows Server in CI on experimental revision `d18f15bb3a9208cb8c31030d09fd7c9b4e50eb84`. The local experiment artifacts carry full-matrix fit and validation logs.

[Representative CI run](https://github.com/egenovese-de/Human3D-2.0/actions/runs/46149317774) · [G6 branch](https://github.com/egenovese-de/Human3D-2.0/tree/lab/g6-geometry-capacity)
''')
    structure=json.loads((root/'structure.json').read_text())
    poses=[[k,v['all_crossings'],v['new_pairs_vs_native_D0']] for k,v in structure['poses'].items()
           if k in ('native','A','T','X')]
    append('CANONICAL_POSE_ANALYSIS','''
## Four-pose crossing control

'''+tab(['Pose','Disjoint-index crossing pairs','New relative to native'],poses)+
        '\n\nThe single control shares the same native pair set in all four poses. This does not establish a canonical advantage for A, T or X. There is no controlled multi-family result for axilla, groin separation, or conditioning.')
    append('STRUCTURAL_VALIDATION','''
## Sampled volumetric constraint

The new R2 volume-checked results evaluate the same global coefficient scale through the sampled determinant and surface screens. See G6_FFD_BENCHMARK.md. The refitted fine-FFD diagnostic and the single-field candidate are separate outputs. Regional and posed intersections are not inferred from determinant samples.
''')
    with ZipFile(g5) as z:
        historical=json.loads(z.read('measurements/calibrated-surface.json'))
    direct=0.
    product=0.
    local=[]
    for f in (root/'study').glob('*/surface.json'):
        rows=json.loads(f.read_text())
        ref=historical[f.parent.name]
        direct=max(direct,abs(rows['R0_D9']['accepted']['mean']-ref['D9']['symmetric_mm']['mean']))
        product=max(product,abs(rows['D0']['accepted']['mean']-ref['D0']['symmetric_mm']['mean']))
    for f in (root/'photo').glob('*/surface.json'):
        d=json.loads(f.read_text())
        if 'L0_replay' in d:
            local.append([f.parent.name,f"{historical[f.parent.name]['L0']['symmetric_mm']['mean']:.3f}",
                          f"{d['L0_replay']['accepted']['mean']:.3f}",
                          d['L0_replay']['new_crossings_proposal']])
    append('BASELINE_REPRODUCTION',f'''
## Numeric reconciliation

Maximum absolute G5-to-G6 differences are {product:.6f} mm for D0 and {direct:.6f} mm for D9. L0 replay below shows the numeric proposal and new crossings. G5 retained D0 when its L0 crossing rule rejected the proposal. Refer to the structural policy before comparing these columns.

'''+tab(['Subject','G5 retained L0 mm','G6 L0 replay proposal mm','New crossings'],local))
    raw=json.loads((docs/'G6_MEASUREMENTS.json').read_text())
    raw['volume_checked']=vol
    raw['representative_ci']=json.loads((root/'ci.json').read_text())
    (docs/'G6_MEASUREMENTS.json').write_text(json.dumps(raw,indent=2,allow_nan=False)+'\n')
    print('guarded independent held-out mean',combined)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('root','docs','g5'):
        p.add_argument(name,type=Path)
    main(**vars(p.parse_args()))

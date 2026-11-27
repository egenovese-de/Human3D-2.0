"""Calibrated silhouette-only controls, numerical observability and volume tests."""
import json
from dataclasses import replace
from pathlib import Path
import sys
import time
import cv2
import numpy as np
from scipy.ndimage import map_coordinates, distance_transform_edt
from g1_benchmark import Engine, dump, measurements
from evidence import edge_distance, mask_metrics, profile
from photographic import SIZE, compile_view, coordinate_fit, score
from projection import Camera, Raster

VIEW_COUNTS = [2,4,8,16,30]


def occupancy(camera, cloud, mask):
    xy = np.floor(camera.project(cloud,len(mask))[:,:2]).astype(int)
    valid = ((xy>=0)&(xy<len(mask))).all(axis=1)
    result = np.zeros(len(xy),np.bool_)
    result[valid] = mask[xy[valid,1],xy[valid,0]]
    return result


def volume_metrics(estimated, truth, step):
    both, union = int(np.count_nonzero(estimated & truth)),int(np.count_nonzero(estimated | truth))
    outside = estimated & ~truth
    missing = truth & ~estimated
    e = estimated & (distance_transform_edt(estimated) <= 1.)
    t = truth & (distance_transform_edt(truth) <= 1.)
    ds = np.r_[distance_transform_edt(~t)[e],distance_transform_edt(~e)[t]]*step*10
    return dict(iou=both/max(1,union),overestimate_l=float(outside.sum()*step**3/1000),
                underestimate_l=float(missing.sum()*step**3/1000),
                boundary_voxel_mean_mm=float(ds.mean()),memory_bytes=int(estimated.nbytes+truth.nbytes),
                overestimation_voxels_per_height_band=[int(x.sum()) for x in np.array_split(outside,5,axis=1)])


def hull_test(ref, ref_faces, raster, step, out):
    # The fixed grid uses camera coordinates in centimetres and a conservative box.
    lo,hi = ref[ref_faces].min(axis=(0,1))-4,ref[ref_faces].max(axis=(0,1))+4
    axes = [np.arange(x,y,step) for x,y in zip(lo,hi)]
    xyz = np.stack(np.meshgrid(*axes,indexing='ij'),axis=-1)
    cloud = xyz.reshape(-1,3)
    # Ray parity is computed against paired depth surfaces using robust line-triangle intersections.
    # Multiple disjoint intervals are kept. No front/back envelope fills cavities.
    hits = np.zeros((len(axes[0]),len(axes[1]),len(axes[2])),np.int32)
    xys = ref[ref_faces][:,:,:2]
    for k,tr in enumerate(xys):
        l = np.searchsorted(axes[0],tr[:,0].min())
        r = np.searchsorted(axes[0],tr[:,0].max(),side='right')
        b = np.searchsorted(axes[1],tr[:,1].min())
        t = np.searchsorted(axes[1],tr[:,1].max(),side='right')
        if l>=r or b>=t:
            continue
        first,second = tr[1]-tr[0],tr[2]-tr[0]
        det = first[0]*second[1]-first[1]*second[0]
        if abs(det)<1e-8:
            continue
        ox,oy = axes[0][l:r,None]-tr[0,0],axes[1][None,b:t]-tr[0,1]
        u,v = (ox*second[1]-oy*second[0])/det,(first[0]*oy-first[1]*ox)/det
        xi,yi = np.nonzero((u>=0)&(v>=0)&(u+v<1))
        z = ref[ref_faces[k],2]
        hit = z[0]+u[xi,yi]*(z[1]-z[0])+v[xi,yi]*(z[2]-z[0])
        layer = np.searchsorted(axes[2],hit)
        valid = layer<len(axes[2])
        np.add.at(hits,(xi[valid]+l,yi[valid]+b,layer[valid]),1)
    truth = np.cumsum(hits,axis=2)%2==1
    cases = {}
    for count in VIEW_COUNTS:
        start = time.perf_counter()
        angles = [0,90] if count==2 else np.arange(count)*180/count
        accepted = np.ones(len(cloud),bool)
        for angle in angles:
            cam = Camera(angle)
            mask = raster.draw(cam,ref,ref_faces,384)
            accepted &= occupancy(cam,cloud,mask)
        shape = truth.shape
        result = accepted.reshape(shape)
        cases[str(count)] = volume_metrics(result,truth,step)
        cases[str(count)].update(seconds=time.perf_counter()-start,angles=np.asarray(angles).tolist(),
                                 grid_points=len(cloud),cloud_bytes=cloud.nbytes)
        if count in (2,8,30):
            np.savez_compressed(out/(f'hull-{step}-{count}.npz'),hull=result,oracle_occupancy=truth,
                                axis_x=axes[0],axis_y=axes[1],axis_z=axes[2])
    # Points outside a calibrated 3D silhouette intersection provide an optional fit penalty.
    hull_distance = distance_transform_edt(~accepted.reshape(truth.shape))*step
    return cases, (axes,hull_distance)


def feature_vertices(e,x,names):
    return e.extended(dict(zip(names,x)))*10


def sensitivity(e, raster, faces, settings):
    names = settings['g1_fields']
    base = np.array(settings['g1_initial'])
    bounds = np.array(settings['g1_bounds'])
    cameras = [Camera(angle) for angle in (0,90,180,45)]
    points = feature_vertices(e,base,names)
    references = [raster.draw(c,points,faces,384,True) for c in cameras]
    basis = []
    for mask,depth,ids in references:
        boundary = np.flatnonzero(mask & (distance_transform_edt(mask)<2.2))[::4]
        interior = np.flatnonzero(distance_transform_edt(mask)>6)[::100]
        basis.append((boundary,interior))
    def collect(x):
        v = feature_vertices(e,x,names)
        result = []
        for camera,(boundary,interior) in zip(cameras,basis):
            mask,depth,_ = raster.draw(camera,v,faces,384,True)
            signed = distance_transform_edt(~mask)-distance_transform_edt(mask)
            filled = np.where(np.isfinite(depth),depth,650)
            sample = profile(mask,np.arange(65,325,4)).flatten()
            result.append(dict(contour=signed.flat[boundary],profiles=sample,depth=filled.flat[interior]))
        return result
    j = []
    columns = {}
    for i,name in enumerate(names):
        left,right = base.copy(),base.copy()
        left[i] = max(left[i]-.04,bounds[0,i])
        right[i] = min(right[i]+.04,bounds[1,i])
        denom = right[i]-left[i]
        lo,hi = collect(left),collect(right)
        pair = [{key:(b[key]-a[key])/denom for key in a} for a,b in zip(lo,hi)]
        j.append(pair)
        columns[name] = {str(camera.yaw):{key:float(np.sqrt(np.mean(value**2))) for key,value in block.items()}
                         for camera,block in zip(cameras,pair)}
    def matrix(view_indices,channels):
        return np.stack([np.concatenate([param[i][k] / (3 if k=='depth' else 1)
                                         for i in view_indices for k in channels]) for param in j],axis=1)
    ranks = {}
    for key,view_indices,channels in [
        ('front',[0],['contour']),('side',[1],['contour']),('oblique',[3],['contour']),
        ('front_side',[0,1],['contour']),('front_side_rear',[0,1,2],['contour']),
        ('four',[0,1,2,3],['contour']),('four_with_profiles',[0,1,2,3],['contour','profiles']),
        ('four_with_oracle_depth',[0,1,2,3],['contour','profiles','depth'])]:
        mat = matrix(view_indices,channels)
        values = np.linalg.svd(mat,compute_uv=False)
        corr = np.nan_to_num(np.corrcoef(mat,rowvar=False))
        pairs = sorted([(i,j,float(corr[i,j])) for i in range(len(names)) for j in range(i+1,len(names))],
                       key=lambda i:abs(i[2]),reverse=True)
        ranks[key] = dict(singular=values.tolist(),relative_rank_1pct=int((values>values[0]*.01).sum()),
                          strongest_aliases=[[names[i],names[j],v] for i,j,v in pairs[:8]])
    return columns,ranks


def camera_probe(ref,faces,raster):
    reference = Camera(35,distance=260,elevation=12,perspective=True)
    levels = np.arange(62,325,3)
    dims = {}
    true = raster.draw(reference,ref,faces,384)
    canon = profile(true,levels)
    actual_height = np.ptp(np.nonzero(true)[0])
    variants = {'weak_perspective':replace(reference,perspective=False),
                'focal_+8pct':replace(reference,span=reference.span/1.08),
                'roll_5deg':replace(reference,roll=5),
                'elevation_zero':replace(reference,elevation=0),
                'distance_450_same_angular_scale':replace(reference,distance=450),
                'yaw_+10deg':replace(reference,yaw=45),
                'crop_translation':replace(reference,dy=.12)}
    for name,camera in variants.items():
        mask = raster.draw(camera,ref,faces,384)
        visible_height = np.ptp(np.nonzero(mask)[0])
        pred = profile(mask,levels)
        # Match vertical fractions of the visible silhouette as an independent scale-free proxy.
        standard = np.linspace(.1,.9,40)
        t_rows = np.rint(np.min(np.nonzero(true)[0])+actual_height*standard).astype(int)
        p_rows = np.rint(np.min(np.nonzero(mask)[0])+visible_height*standard).astype(int)
        norm = abs(profile(true,t_rows)[:,2]/actual_height-profile(mask,p_rows)[:,2]/visible_height)
        dims[name] = dict(mask=mask_metrics(mask,true),profile_mae_px=float(abs(canon[:,2]-pred[:,2]).mean()),
                          normalized_foreground_width_mae=float(norm.mean()))
    return dims


def contour_probe(e, raster, ref, faces, settings):
    names = settings['g1_fields']
    base = np.array(settings['g1_initial'])
    camera = Camera(0)
    mask = raster.draw(camera,ref,faces,384)
    view = compile_view({'camera':camera,'mask':{'oracle':mask}},'oracle')
    rows = {}
    for mode in ('iou','signed','chamfer','sdf','gap','sparse','dense'):
        # Keep a known body/camera or shift only one nuisance. True reference geometry is a control.
        sweeps = {}
        variants = dict(shift=lambda x:replace(camera,dx=x*.04),
                        roll=lambda x: replace(camera,roll=x*8),
                        yaw=lambda x:replace(camera,yaw=x*18),
                        scale=lambda x:replace(camera,span=camera.span*(1+x*.08)))
        for metric,apply in variants.items():
            sweeps[metric]=[score(raster.draw(apply(x),ref,faces,SIZE),view,mode) for x in np.linspace(-1,1,25)]
        target_index = next(i for i,k in enumerate(names) if 'torso-scale-horiz' in k)
        sweeps['native_torso_width_neutral']=[]
        for offset in np.linspace(-.5,.5,25):
            values = base.copy()
            values[target_index] = offset
            sweeps['native_torso_width_neutral'].append(score(raster.draw(camera,feature_vertices(e,values,names),faces,SIZE),view,mode))
        rows[mode] = sweeps
    return rows


def main(refs,out,raster_path,config):
    out.mkdir(parents=True,exist_ok=True)
    e = Engine()
    raster = Raster(raster_path)
    settings = json.loads(config.read_text())
    names = settings['g1_fields']
    default = np.asarray(settings['g1_initial'])
    bounds = np.asarray(settings['g1_bounds'])
    for case in ('A_high_mass','A_heldout_1'):
        a = np.load(refs/(case+'.npz'))
        ref,faces,rt = a['reference'],a['faces'],a['reference_faces']
        sub = out/case
        sub.mkdir(exist_ok=True)
        row = {}
        row['hull_3cm'],_ = hull_test(ref,rt,raster,3.,sub)
        row['hull_2cm'], (axes,dist) = hull_test(ref,rt,raster,2.,sub)
        row['camera'] = camera_probe(ref,rt,raster)
        row['contour_landscape'] = contour_probe(e,raster,ref,faces,settings)
        verts = dict(reference=ref,faces=faces,reference_faces=rt)
        row['view_counts'] = {}
        native = lambda x:feature_vertices(e,x,names)
        for count in (2,4,8,16,30):
            angles = [0,90] if count==2 else np.arange(count)*180/count
            cameras = [Camera(angle) for angle in angles]
            observations = [compile_view({'camera':c,'mask':{'truth':raster.draw(c,ref,rt,384)}},'truth') for c in cameras]
            start_steps = (.23,.11,.05,.022)
            key = f'view_{count}'
            verts[key],row['view_counts'][key] = coordinate_fit(native,bounds,default,faces,observations,'dense',raster,steps=start_steps)
            if count==4:
                used = np.unique(faces)[::12]
                def volume_penalty(pred,depth,ids,obs,points):
                    target = ((points[used]-np.array([ax[0] for ax in axes]))/2).T
                    sampled = map_coordinates(dist,target,order=1,mode='constant',cval=10)
                    return .035*float(np.minimum(sampled,20).mean())/len(observations)
                verts['E8_oracle_hull'],row['view_counts']['E8_oracle_hull'] = coordinate_fit(native,bounds,default,faces,observations,
                        'dense',raster,steps=start_steps,extra=volume_penalty)
            print(case,key,round(row['view_counts'][key]['seconds'],2),flush=True)
        np.savez_compressed(sub/(case+'.npz'),**verts)
        dump(sub/'controls.json',row)
    columns,ranks = sensitivity(e,raster,faces,settings)
    dump(out/'sensitivity.json',dict(columns=columns,ranks=ranks))


if __name__ == '__main__':
    cv2.setNumThreads(1)
    main(*map(Path,sys.argv[1:]))

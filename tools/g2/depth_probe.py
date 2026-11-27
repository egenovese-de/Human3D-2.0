"""Depth Anything V2 Small CPU inference and isolated geometry probe."""
from hashlib import sha256
from pathlib import Path
import json
import resource
import sys
import time
import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image
from scipy.stats import spearmanr
from g1_benchmark import Engine, dump
from photographic import ANGLES, SIZE, compile_view, coordinate_fit, save_png
from projection import Camera, Raster

MODEL_SHA = 'afb6a5c28f3b6bf1618c6e43f02073ef9dfdc70e937502d51603e57b0a1df10c'


def fit_affine(x,y):
    x0,y0 = x-x.mean(),y-y.mean()
    slope = max(0.,float(np.dot(x0,y0)/max(1e-12,np.dot(x0,x0))))
    return slope,y.mean()-slope*x.mean()


def angular_error(depth, truth_normals, interior, span):
    dy,dx = np.gradient(np.where(np.isfinite(depth),depth,0.))
    unit = span/depth.shape[0]
    normals = np.stack([dx/unit,-dy/unit,np.ones_like(dx)],axis=-1)
    normals /= np.linalg.norm(normals,axis=-1,keepdims=True)
    return np.rad2deg(np.arccos(np.clip((normals[interior]*truth_normals[interior]).sum(axis=1),-1,1)))


def measure(pred,truth):
    visible = truth['visible']
    inner = cv2.erode(visible.astype(np.uint8),np.ones((9,9),np.uint8)).astype(bool)
    yy,xx = np.indices(visible.shape)
    train = inner & ((yy+xx)%3 == 0)
    val = inner & ~train
    inverse = np.zeros_like(pred)
    inverse[visible] = 1/truth['depth_cm'][visible]
    scale,shift = fit_affine(pred[train],inverse[train])
    mapped = 1/np.maximum(1e-5,pred*scale+shift)
    actual = truth['depth_cm'][val]
    normals = angular_error(mapped,truth['normals_camera'],val,215)
    oracle_normals = angular_error(truth['depth_cm'],truth['normals_camera'],val,215)
    regions = truth['region'][val]
    mae = abs(mapped[val]-actual)*10
    rho = spearmanr(pred[val],inverse[val]).statistic
    return dict(spearman=float(rho) if np.isfinite(rho) else None,scale_aligned_mae_mm=float(mae.mean()),
                plane_mae_mm=float(np.mean(abs(actual-np.mean(truth['depth_cm'][train])))*10),
                normal_median_deg=float(np.median(normals)), normal_mean_deg=float(normals.mean()),
                oracle_depth_gradient_normal_median_deg=float(np.median(oracle_normals)),
                regional_mae_mm={str(k):float(mae[regions==k].mean()) for k in np.unique(regions) if k>0},
                region_normal_median_deg={str(k):float(np.median(normals[regions==k])) for k in np.unique(regions) if k>0},
                pixels=int(val.sum()))


def objective(kind):
    def penalty(pred,depth,ids,obs,vertices):
        support = obs['depth_support'] & pred
        if support.sum()<20:
            return .5
        z = depth[support]
        observed = obs['relative'][support]
        if kind=='metric_oracle':
            return .12*np.mean(np.minimum(abs(z-observed)/14,3))
        candidate = 1/z
        scale,shift = fit_affine(observed,candidate)
        error = candidate-(scale*observed+shift)
        return .12 * float(np.minimum(abs(error)/max(candidate.std(),1e-7),3).mean())
    return penalty


def main(experiment, refs, model, raster_file, subjects=()):
    if sha256(model.read_bytes()).hexdigest()!=MODEL_SHA:
        raise ValueError('depth weight digest mismatch')
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    detector = ort.InferenceSession(str(model),options,providers=['CPUExecutionProvider'])
    e = Engine()
    config = json.loads((experiment/'measurements/config.json').read_text())
    names = config['g1_fields']
    bounds = np.asarray(config['g1_bounds'])
    default = np.asarray(config['g1_initial'])
    native = lambda values:e.extended(dict(zip(names,values)))*10
    raster = Raster(raster_file)
    out = experiment/'depth'
    out.mkdir(exist_ok=True)
    document = out/'depth.json'
    metrics = json.loads(document.read_text())['subjects'] if document.exists() else {}
    for subject in subjects or ('A_adult_asymmetric','A_high_mass','A_heldout_1','B_female'):
        sub = experiment/'maps'/subject
        if not all((sub/str(angle)/'oracle.npz').exists() for angle in ANGLES):
            continue
        row,observations = {},[]
        source = np.load(refs/(subject+'.npz'))
        for folder in sorted(sub.glob('*')):
            if not (folder/'oracle.npz').exists() or folder.name in ('perspective','cropped'):
                continue
            rgb = np.asarray(Image.open(folder/'rgb.png'))
            start = time.perf_counter()
            pixels = cv2.resize(rgb,(392,392),interpolation=cv2.INTER_CUBIC).astype(np.float32)/255
            pixels = (pixels-np.array([.485,.456,.406],np.float32))/np.array([.229,.224,.225],np.float32)
            raw = detector.run(None,{'pixel_values':pixels.transpose(2,0,1)[None]})[0][0]
            prediction = cv2.resize(raw,(384,384),interpolation=cv2.INTER_CUBIC)
            seconds = time.perf_counter()-start
            gt = dict(np.load(folder/'oracle.npz'))
            row[folder.name] = measure(prediction,gt) | {'extraction_seconds':seconds}
            encoded = ((prediction-prediction.min())*255/max(1e-5,np.ptp(prediction))).astype(np.uint8)
            save_png(folder/'predicted_depth.png',encoded)
            np.save(folder/'predicted_inverse_depth.npy', prediction)
            if folder.name in [str(angle) for angle in ANGLES]:
                keyed = np.asarray(Image.open(folder/'rgb_mask.png'))>0
                view = compile_view({'camera':Camera(float(folder.name)),'mask':{'rgb':keyed}},'rgb')
                view['relative'] = cv2.resize(prediction,(SIZE,SIZE))
                view['depth_support'] = cv2.erode(view['target'].astype(np.uint8),np.ones((5,5),np.uint8)).astype(bool)
                view['oracle_metric'] = gt['depth_cm'][np.floor((np.arange(SIZE)+.5)*384/SIZE).astype(int)[:,None],
                                                       np.floor((np.arange(SIZE)+.5)*384/SIZE).astype(int)[None,:]]
                observations.append(view)
        meshes = dict(reference=source['reference'],reference_faces=source['reference_faces'],faces=source['faces'])
        for key in ('same_budget_control','E6','oracle_depth'):
            extra = None if key=='same_budget_control' else objective('metric_oracle' if key=='oracle_depth' else 'relative')
            obs = observations if key!='oracle_depth' else [
                v|{'relative':v['oracle_metric'],'depth_support':v['depth_support'] & np.isfinite(v['oracle_metric'])}
                for v in observations]
            meshes[key],row[key] = coordinate_fit(native,bounds,default,source['faces'],obs,'dense',raster,extra=extra)
        np.savez_compressed(out/(subject+'.npz'),**meshes)
        metrics[subject] = row
        print(subject,{k:round(v['scale_aligned_mae_mm'],1) for k,v in row.items() if 'scale_aligned_mae_mm' in v},flush=True)
    dump(out/'depth.json',dict(model_bytes=model.stat().st_size,sha256=MODEL_SHA,
         peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,subjects=metrics))


if __name__ == '__main__':
    cv2.setNumThreads(1)
    main(*map(Path,sys.argv[1:5]), subjects=sys.argv[5:])

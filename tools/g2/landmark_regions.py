"""Measured landmark-derived region baselines and detector confidence calibration."""
from hashlib import sha256
from pathlib import Path
import sys
import time
import cv2
import numpy as np
from PIL import Image
from g1_benchmark import dump
from evidence import mask_metrics
from photographic import REGIONS
from human3d.vision import _NativePoseLandmarker

# MediaPipe landmarks define coarse pixel partitions, independent of model rig joints.
PAIRS = [(0,0),(0,-1),(-1,-2),(-2,-2),(11,13),(12,14),(13,15),(14,16),
         (15,19),(16,20),(23,25),(24,26),(25,27),(26,28),(27,31),(28,32)]


class SoftMaskDetector(_NativePoseLandmarker):
    def _mask_png(self, raw, image_size, content_size=None, original_size=None):
        width,height = content_size
        self.maps.append(np.reshape(raw,image_size[::-1])[:height,:width].copy())
        return super()._mask_png(raw,image_size,content_size,original_size)

    def predict(self,path):
        self.maps = []
        return self.detect(path,sha256(path.read_bytes()).hexdigest())


def segmentation(landmarks, mask):
    points = {i:p[:2] for i,p in enumerate(landmarks)}
    points[-1] = (points[11]+points[12])/2
    points[-2] = (points[23]+points[24])/2
    yy,xx = np.indices(mask.shape)
    grid = np.stack([xx+.5,yy+.5],axis=-1)
    distance = []
    for a,b in PAIRS:
        start,end = points[a],points[b]
        off,delta = grid-start,end-start
        t = np.clip((off@delta)/max(1e-6,np.dot(delta,delta)),0,1)
        distance.append(np.sum((off-t[...,None]*delta)**2,axis=-1))
    return (1+np.argmin(distance,axis=0))*mask


def binned(probability, outcome):
    results = []
    for low in np.arange(0,1,.1):
        selected = (probability>=low)&(probability<low+.1+1e-9)
        if selected.any():
            results.append(dict(n=int(selected.sum()),predicted=float(probability[selected].mean()),
                                observed=float(outcome[selected].mean())))
    return results


def main(experiment,model,out):
    det = SoftMaskDetector(model,segmentation=True)
    rows = {}
    for case in ('A_adult_asymmetric','A_high_mass','A_heldout_1'):
        folder = experiment/'maps'/case
        for key in ('0','90','180','45','occluded','background','low_resolution'):
            view = folder/key
            if not (view/'estimated.npz').exists():
                continue
            gt = dict(np.load(view/'oracle.npz'))
            raw = dict(np.load(view/'estimated.npz'))
            if len(raw['landmarks_px'])!=33:
                continue
            truth = gt['visible']
            regional = segmentation(raw['landmarks_px'],raw['mask_m6'])
            labels = gt['region']
            rgb = Image.open(view/'rgb.png')
            det.predict(view/'rgb.png')
            probabilities = det.maps[0] if len(det.maps)==1 else None
            valid = ~gt['occluded']
            row = {'region_coverage':{name:int(np.count_nonzero((labels==i)&valid)) for i,name in enumerate(REGIONS,1)},
                   'region_iou':{name:mask_metrics((regional==i)&valid,(labels==i)&truth)['iou']
                                 for i,name in enumerate(REGIONS,1) if ((labels==i)&truth).any()}}
            if probabilities is not None:
                row['mask_calibration'] = binned(probabilities[valid],truth[valid])
                row['mask_brier'] = float(np.mean((probabilities[valid]-truth[valid])**2))
                row['threshold_sweep'] = {str(i):mask_metrics((probabilities>=i)&valid,truth)['iou'] for i in (.3,.4,.5,.6,.7)}
            if key in ('0','90'):
                scaled = rgb.resize((768,768),Image.Resampling.LANCZOS)
                tmp = out.parent/'upscaled.png'
                scaled.save(tmp)
                start = time.perf_counter()
                result = det.predict(tmp)
                row['upscaled_seconds'] = time.perf_counter()-start
                if len(result.candidates)==1 and len(det.maps)==1:
                    sample = cv2.resize(det.maps[0],(384,384),interpolation=cv2.INTER_LINEAR)
                    row['upscaled_iou'] = mask_metrics(sample>=.5,truth)['iou']
                tmp.unlink()
            colors = np.r_[np.zeros((1,3),np.uint8),np.random.default_rng(782).integers(35,245,(len(REGIONS),3),dtype=np.uint8)]
            Image.fromarray(colors[regional]).save(view/'landmark_regions.png')
            for label,r in [('head',1),('left_hand',9),('right_hand',10),('left_foot',15),('right_foot',16)]:
                y,x = np.nonzero((labels==r)&truth)
                row.setdefault('body_detail_bbox_px',{})[label] = [int(np.ptp(x)+1),int(np.ptp(y)+1)] if len(x) else None
            rows[f'{case}/{key}'] = row
    det.close()
    dump(out,rows)


if __name__=='__main__':
    cv2.setNumThreads(1)
    main(*map(Path,sys.argv[1:]))

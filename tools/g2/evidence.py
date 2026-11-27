"""Evidence representation and extraction. Oracle channels never enter RGB methods."""
from dataclasses import dataclass
from enum import IntEnum
import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt


class State(IntEnum):
    FOREGROUND = 1
    BACKGROUND = 2
    UNOBSERVED = 3
    UNCERTAIN = 4


@dataclass
class MaskEvidence:
    state: np.ndarray
    silhouette: np.ndarray
    source: str
    image_id: str
    confidence: np.ndarray
    sigma_px: float
    coordinates: str = 'pixel centers in oriented RGB'
    units: str = 'px'
    observation_class: str = 'direct estimated visible occupancy'


def sdf(mask):
    return (distance_transform_edt(~mask)-distance_transform_edt(mask)).astype(np.float32)


def uncertainty(mask, image_id, source, band=1., hidden=None):
    distance = sdf(mask)
    state = np.where(mask, State.FOREGROUND, State.BACKGROUND).astype(np.uint8)
    state[abs(distance) <= band] = State.UNCERTAIN
    confidence = np.clip(abs(distance)/(2*max(1.,band)),0,1).astype(np.float32)
    if hidden is not None:
        state[hidden] = State.UNOBSERVED
        confidence[hidden] = 0
    return MaskEvidence(state, mask, source, image_id, confidence, band)


def rgb_uniform(rgb):
    """Background key using sampled image borders, for controlled studio captures."""
    edge = np.concatenate([rgb[0],rgb[-1],rgb[:,0],rgb[:,-1]])
    color = np.median(edge,axis=0)
    distance = np.linalg.norm(rgb.astype(np.float32)-color,axis=-1)
    mask = distance > 21
    _, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype('uint8'), 8)
    if len(stats) > 1:
        mask = labels == 1+np.argmax(stats[1:,cv2.CC_STAT_AREA])
    return mask


def rgb_grabcut(rgb, seed):
    if not seed.any() or seed.all():
        return seed
    distance = sdf(seed)
    labels = np.where(distance < -3, cv2.GC_FGD, np.where(distance > 5, cv2.GC_BGD,
                       np.where(seed, cv2.GC_PR_FGD, cv2.GC_PR_BGD))).astype(np.uint8)
    if not (labels == cv2.GC_FGD).any() or not (labels == cv2.GC_BGD).any():
        return seed
    cv2.grabCut(rgb, labels, None, np.zeros((1,65)), np.zeros((1,65)), 2, cv2.GC_INIT_WITH_MASK)
    return labels%2 == 1


def edge(mask):
    return mask & ~cv2.erode(mask.astype('uint8'),np.ones((3,3),np.uint8),borderValue=0).astype(bool)


def edge_distance(mask):
    return cv2.distanceTransform((~edge(mask)).astype('uint8'),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)


def profile(mask, rows, column_mask=None):
    """Cross-image envelopes and internal gaps. Rows remain in registered image coordinates."""
    data = mask if column_mask is None else mask & column_mask
    profiles = np.zeros((len(rows),4),float)
    for i,y in enumerate(rows):
        xs = np.flatnonzero(data[y])
        if xs.size:
            profiles[i] = [xs[0], xs[-1]+1, len(xs), xs[-1]+1-xs[0]-len(xs)]
    return profiles


def gaps(mask):
    return (np.maximum.accumulate(mask,axis=1) &
            np.maximum.accumulate(mask[:,::-1],axis=1)[:,::-1] & ~mask)


def mask_metrics(prediction, truth):
    intersection = (prediction & truth).sum()
    union = (prediction | truth).sum()
    ep, et = edge(prediction), edge(truth)
    forward = edge_distance(truth)[ep] if et.any() else np.array([])
    reverse = edge_distance(prediction)[et] if ep.any() else np.array([])
    gt_gap = gaps(truth)
    thin = truth & (distance_transform_edt(truth) <= 2)
    pixels = max(1,int(truth.sum()))
    return dict(iou=float(intersection/max(1,union)),
                dice=float(2*intersection/max(1,prediction.sum()+truth.sum())),
                false_positive_per_truth=float((prediction & ~truth).sum()/pixels),
                false_negative_per_truth=float((~prediction & truth).sum()/pixels),
                boundary_precision_2px=float(np.mean(forward<=2)) if forward.size else 0.,
                boundary_recall_2px=float(np.mean(reverse<=2)) if reverse.size else 0.,
                boundary_symmetric_px=float(np.r_[forward,reverse].mean()) if forward.size and reverse.size else None,
                thin_recall=float(prediction[thin].mean()) if thin.any() else None,
                gap_preserved=float((~prediction[gt_gap]).mean()) if gt_gap.any() else None)

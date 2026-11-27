"""Static calibrated stereo and close-view correspondence control."""
from dataclasses import replace
from pathlib import Path
import sys
import time
import cv2
import numpy as np
from PIL import Image
from g1_benchmark import dump
from projection import Camera, Raster


class StereoCamera(Camera):
    def __init__(self, center_x):
        super().__init__(0,distance=265,perspective=True)
        object.__setattr__(self,'center_x',center_x)

    def project(self, vertices,size):
        return super().project(vertices-[self.center_x,0,0],size)


def make_observation(camera,vertices,faces,raster,texture):
    size = 512
    fg,depth,ids = raster.draw(camera,vertices,faces,size,True)
    iy,ix = np.indices(fg.shape)
    z = depth[fg]
    f = size*camera.distance/camera.span
    x = (ix[fg]+.5-size/2)*z/f+camera.center_x
    y = -(iy[fg]+.5-size/2)*z/f
    world_z = camera.distance-z
    # A fixed three-dimensional albedo field gives coaligned texture at corresponding points.
    gray = np.full(fg.shape,214,np.uint8)
    a,b,c = vertices[faces[ids[fg]]].transpose(1,0,2)
    n = np.cross(b-a,c-a)
    n /= np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-8)
    shade = 110+35*(n@np.array([.2,.6,.6]))
    if texture:
        shade += 25*(np.sin(2.4*x+2*y)+np.sin(.97*y+2.2*world_z)+np.cos(1.63*x-1.4*world_z))
    gray[fg] = np.clip(shade,0,255)
    return gray,fg,depth


def main(ref_path,out,raster_path):
    out.mkdir(parents=True,exist_ok=True)
    a = np.load(ref_path)
    ref,faces = a['reference'],a['reference_faces']
    raster = Raster(raster_path)
    x_base = 8
    cameras = [StereoCamera(0),StereoCamera(x_base)]
    rows = {}
    for texture in (False,True):
        label = 'analytic_texture' if texture else 'smooth_facet_shading'
        stereo = [make_observation(c,ref,faces,raster,texture) for c in cameras]
        (left,fg,z),(right,_,right_depth) = stereo
        t = time.perf_counter()
        stereo_matcher = cv2.StereoSGBM_create(minDisparity=0,numDisparities=32,blockSize=5,
            P1=8*25,P2=32*25,disp12MaxDiff=1,uniquenessRatio=12,speckleWindowSize=30,speckleRange=2)
        disparity = stereo_matcher.compute(left,right).astype(float)/16
        pixel_y,pixel_x = np.indices(z.shape)
        f = len(z)*cameras[0].distance/cameras[0].span
        valid = fg & (disparity>0)
        z_pred = np.zeros(z.shape)
        z_pred[valid] = f*x_base/disparity[valid]
        gt_disparity = np.zeros_like(z)
        gt_disparity[fg] = f*x_base/z[fg]
        right_x = np.clip(np.rint(pixel_x-gt_disparity).astype(int),0,len(z)-1)
        # The reference depth test marks points hidden in the right observation.
        jointly_visible = fg & (abs(np.where(fg,z,0)-right_depth[pixel_y,right_x])<1.4)
        selected = jointly_visible & valid
        error = abs(disparity[selected]-gt_disparity[selected])
        depth_error = abs(z_pred[selected]-z[selected])*10
        rows[label] = dict(seconds=time.perf_counter()-t,coverage=float(selected.sum()/jointly_visible.sum()),
                           rejected_occluded_share=float((~valid & fg & ~jointly_visible).sum()/max(1,(fg&~jointly_visible).sum())),
                           median_correspondence_error_px=float(np.median(error)),median_depth_error_mm=float(np.median(depth_error)),
                           p95_correspondence_px=float(np.percentile(error,95)),p95_depth_error_mm=float(np.percentile(depth_error,95)),
                           flat_plane_median_error_mm=float(np.median(abs(z[selected]-np.median(z[selected])))*10))
        Image.fromarray(left).save(out/(label+'-left.png'))
        Image.fromarray(right).save(out/(label+'-right.png'))
        image = np.zeros((*z.shape,3),np.uint8)
        image[jointly_visible] = [75,73,90]
        image[selected] = np.stack([np.clip(error*90,0,255),np.clip(255-error*100,0,255),np.full(len(error),135)],axis=1)
        Image.fromarray(image).save(out/(label+'-match-error.png'))
        np.savez_compressed(out/(label+'.npz'),predicted_disparity_px=disparity,
                            reference_disparity_px=gt_disparity,jointly_visible=jointly_visible)
    dump(out/'stereo.json',rows)


if __name__=='__main__':
    cv2.setNumThreads(1)
    main(*map(Path,sys.argv[1:]))

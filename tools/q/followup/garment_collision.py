"""Cross-check production signed samples with independent triangle intersections."""
import argparse
from collections import Counter
import json
from pathlib import Path

import bpy  # Initializes Blender mathutils in the module distribution.
from mathutils.bvhtree import BVHTree
import numpy as np
from scipy.spatial import cKDTree

from clothing_fixtures import triangulate
from evaluate import sample_surface
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.garments import CATEGORIES, measure_clearance, prototype
from human3d.session import Session


def boundary(vertices, faces):
    edges = Counter(tuple(sorted((a,b))) for f in faces for a,b in zip(f, f[1:]+f[:1]))
    border = sorted({p for edge, degree in edges.items() if degree == 1 for p in edge})
    return vertices[border], len(border)


def volume_proxy(points, polygons):
    counts = Counter(tuple(sorted((a,b))) for face in polygons for a,b in zip(face,face[1:]+face[:1]))
    directed = [(a,b) for face in polygons for a,b in zip(face,face[1:]+face[:1])
                if counts[tuple(sorted((a,b)))] == 1]
    head = dict(directed)
    if (len(head)!=len(directed) or set(head)!=set(head.values())
            or any(n>2 for n in counts.values())):
        return {"closed_cap_volume_l":None,"volume_exclusion":"nonmanifold boundary"}
    loops=[]
    while head:
        origin=next(iter(head))
        loop=[origin]
        while head[loop[-1]]!=origin:
            loop.append(head.pop(loop[-1]))
        head.pop(loop[-1])
        loops.append(loop)
    original=list(map(tuple,points))
    extended=list(original)
    faces=triangulate(polygons)
    caps=[]
    for loop in loops:
        center=len(extended)
        extended.append(tuple(points[loop].mean(axis=0)))
        caps.extend((b,a,center) for a,b in zip(loop,loop[1:]+loop[:1]))
    closed=faces+caps
    counts=Counter(tuple(sorted((a,b))) for face in closed for a,b in zip(face,face[1:]+face[:1]))
    if any(n!=2 for n in counts.values()):
        return {"closed_cap_volume_l":None,"volume_exclusion":"edge multiplicity after closure"}
    tree=BVHTree.FromPolygons(extended,closed,all_triangles=True)
    sets=[set(t) for t in closed]
    overlaps=sum(a<b and not sets[a]&sets[b] for a,b in tree.overlap(tree))
    if overlaps:
        return {"closed_cap_volume_l":None,"volume_exclusion":"closed proxy self-intersections",
                "self_intersection_pairs":overlaps,"capped_boundary_loops":len(loops)}
    xyz=np.asarray(extended)[np.asarray(closed)]
    signed=np.einsum("ij,ij->i",xyz[:,0],np.cross(xyz[:,1],xyz[:,2])).sum()/6
    return {"closed_cap_volume_l":float(abs(signed)*1000), "capped_boundary_loops":len(loops),
            "volume_definition":"virtual triangle fan closure; liters of enclosed envelope"}

def measure(a, b):
    return float(500*(cKDTree(a).query(b)[0].mean()+cKDTree(b).query(a)[0].mean()))


def run(dataset, clothes, previous, output):
    rows = []
    for identity in ("f_af01","m_la01"):
        truth = json.loads((dataset/f"{identity}_neutral"/"manifest.json").read_text())
        path = next((previous/"holdout-native").glob(f"*_{identity}_bend0-1"))/"project"
        body = load_project_body(Session(path).store)
        points = np.asarray(deform_vertices(body, {}))
        faces = [tuple(i for i,_ in f["corners"]) for f in body["mesh"]["faces"] if f["group"]=="body"]
        elevations = points[np.unique(np.concatenate(faces)),1]
        factor = truth["height_m"]/np.ptp(elevations)
        floor = elevations.min()
        body_tree = BVHTree.FromPolygons(points.tolist(),triangulate(faces),all_triangles=True)
        for category in CATEGORIES:
            oracle = json.loads((clothes/identity/category/"layer_0.json").read_text())
            oracle_points = np.asarray(oracle["vertices"])
            oracle_sample = sample_surface(oracle_points,oracle["faces"],7000,2473)
            oracle_edge, _ = boundary(oracle_points,oracle["faces"])
            for ease, hem in ((0,0),(5,.25),(10,-.25)):
                shell = prototype(body,points,category,ease_mm=ease,hem=hem)
                sampled = measure_clearance(shell,body,points,shell.points)
                shell_faces = [tuple(i for i,_ in f) for f in shell.faces]
                garment_tree = BVHTree.FromPolygons(shell.points.tolist(),triangulate(shell_faces),all_triangles=True)
                intersect = body_tree.overlap(garment_tree)
                x,y,z = shell.points.T
                world = np.column_stack((x,-z,y-floor))*factor
                surface = sample_surface(world,shell_faces,7000,2474)
                edge, n = boundary(world,shell_faces)
                rows.append(dict(identity=identity,category=category,ease_mm=ease,hem_dm=hem,
                  release_sampled_violations=sampled.violations,release_sampled_minimum_mm=100*sampled.minimum,
                  triangle_intersection_pairs=len(intersect),garment_triangles_intersecting=len({b for _,b in intersect}),
                  independent_pattern_surface_mm=measure(oracle_sample,surface),
                  independent_boundary_mm=measure(oracle_edge,edge),boundary_vertices=n,
                  native_volume=volume_proxy(world,shell_faces),
                  independent_volume=volume_proxy(oracle_points,oracle["faces"])))
                output.write_text(json.dumps(rows,indent=2,allow_nan=False)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    for name in ("dataset","clothes","previous","output"):
        parser.add_argument(name,type=Path)
    run(**vars(parser.parse_args()))

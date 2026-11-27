"""Fixed direction oracle and semantic joint endpoints on independent reference bodies."""
from pathlib import Path
import hashlib, json, sys
import numpy as np
from g1_exact_surface import tree, distance
from g1_benchmark import Engine,dump,summary,sample
from human3d.alignment import Alignment,Camera
from human3d.native_rig import pose_transforms,rebind_joints,skin_vertices

NAMES={"upperarm":"upperarm01","lowerarm":"lowerarm01","thigh":"upperleg01","calf":"lowerleg01"}

def main(root,raw):
    e=Engine(); out=[]
    rig=e.body["rig"]
    for sex,identifier in (("female","f_ca01"),("male","m_la01")):
        location=raw/f"MBLab_human_{sex}_{identifier}_bend0"
        data=(location/"mesh.json").read_bytes()
        source=json.loads((location/"manifest.json").read_text())
        assert hashlib.sha256(data).hexdigest()==source["mesh_sha256"]
        original=np.asarray(json.loads(data)["vertices"])
        p=json.loads((root/f"B_{sex}_manifest.json").read_text())
        target={};angles={};depths={}
        for part,native in NAMES.items():
            for side in "LR":
                points=np.asarray(source["joint_anchors"][f"{part}_{side}"])
                bone=f"{native}.{side}"
                target[bone]=np.c_[points[:,0],points[:,2]-original[:,2].min(),-points[:,1]]*p["scale_cm_per_m"]
                target[bone][:,1]+=p["vertical_origin_cm"]
                x,y,z=target[bone][1]-target[bone][0]
                angles[bone]=float(np.arctan2(-y,x))
                depths[bone]=float(z/max(np.hypot(x,y),1e-8))
        alignment=Alignment(Camera(0,100,0j,1),0,angles,depths)
        baseline_joints=rebind_joints(rig,e.base)
        fixed=pose_transforms(rig,baseline_joints,alignment)
        with np.load(root/f"B_{sex}.npz") as a:
            ref=a["reference"];rt=a["reference_faces"];faces=a["faces"]
            rt_tree=tree(ref,rt); rpoints=sample(ref,rt,12000,819)
            rows={}
            for mode in ("M0","M1","M2","M3","M4","M5"):
                rest=a[mode]/10
                joints=rebind_joints(rig,rest)
                rows[mode]={}
                for label,t in (("native_rest",None),("frozen_direction_oracle",fixed),
                                ("shape_rebound_direction_oracle",pose_transforms(rig,joints,alignment))):
                    v=rest if t is None else np.asarray(skin_vertices(rest,rig["skin"],t))
                    d=np.r_[distance(sample(v*10,faces,12000,818),rt_tree),distance(rpoints,tree(v*10,faces))]
                    joint_errors={}
                    # Compare segment-chain head landmarks. Native helper-bone tails
                    # can be shorter than complete independent anatomical segments.
                    for k,q in target.items():
                        head=joints[rig["bones"][k]["head"]]
                        if t is not None: head=t[k][0]@head+t[k][1]
                        joint_errors[k]=float(np.linalg.norm(head*10-q[0])*10)
                    rows[mode][label]={"surface_mm":summary(d),"semantic_joint_head_mm":joint_errors,
                                       "joint_head_mean_mm":float(np.mean(list(joint_errors.values())))}
        out.append({"case":"B_"+sex,"geometry_sha256":source["mesh_sha256"],"oracle_bones":list(target),"rows":rows})
        print(sex,[(k,round(r["surface_mm"]["mean"],3),round(r["joint_head_mean_mm"],3)) for k,r in rows["M4"].items()],flush=True)
    dump(root/"independent_stance.json",out)
if __name__=="__main__":main(Path(sys.argv[1]),Path(sys.argv[2]))

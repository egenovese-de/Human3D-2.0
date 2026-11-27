"""Export two validated MakeHuman-generated fits through the existing USD bridge."""
from pathlib import Path
import sys
import numpy as np
import hashlib
from g1_benchmark import Engine, dump
from human3d.alignment import Alignment, Camera
from human3d.fitting import Fit
from human3d.native_rig import validate_rebind
from human3d.usd_export import export_body

def main(root):
    out=root/"export"
    out.mkdir(exist_ok=True)
    e=Engine()
    results={}
    for stem in ("A_muscular","A_high_mass"):
        with np.load(root/(stem+".npz")) as a:
            vertices=a["M4"]/10
        validate_rebind(e.body,vertices)
        body=e.body|{"mesh":e.body["mesh"]|{"vertices":vertices.tolist()}}
        path=out/(stem+"_M4.usdc")
        export_body(path,body,Fit({},1.,1.),Alignment(Camera(0,1,0j,1),0,{}))
        results[stem]={"file":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
    dump(out/"exports.json",results)
if __name__=="__main__": main(Path(sys.argv[1]))

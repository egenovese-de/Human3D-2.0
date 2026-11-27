import argparse
import json
from pathlib import Path
import numpy as np
from scipy.linalg import solve
p=argparse.ArgumentParser()
p.add_argument("--seed",type=int,required=True)
p.add_argument("--output",type=Path,required=True)
a=p.parse_args()
rng=np.random.default_rng(a.seed)
m=rng.integers(-5,6,size=(8,8)).astype(float)
m=m.T@m+np.eye(8)
b=rng.integers(-10,11,size=8).astype(float)
x=solve(m,b)
assert np.linalg.norm(m@x-b)<1e-10
a.output.write_bytes((json.dumps({"seed":a.seed,"solution":np.round(x,12).tolist(),"residual_pass":True},sort_keys=True)+"\n").encode("utf-8"))

"""Attained direct-geometry comparator on the two new MakeHuman references."""
from pathlib import Path
import json
import sys
import time
import numpy as np
from scipy.optimize import least_squares
from g1_benchmark import Engine, dump


def main(refs,config,out):
    out.mkdir(parents=True,exist_ok=True)
    e=Engine()
    setup=json.loads(config.read_text())
    names=setup['g1_fields']
    default=np.asarray(setup['g1_initial'])
    bounds=np.asarray(setup['g1_bounds'])
    ids=np.sort(np.random.default_rng(626).choice(e.skin,1400,replace=False))
    flat=(ids[:,None]*3+np.arange(3)).ravel()
    e.train_matrix=e.matrix[flat].tocsc()
    for path in sorted(refs.glob('A_heldout_*.npz')):
        a=np.load(path)
        ref=a['reference']
        def residual(x):
            v=e.extended(dict(zip(names,x)),vertices=flat)*10
            return np.r_[(v-ref[ids]).ravel(),.12*(x-default)]
        rows=[]
        best=None
        for seed in (None,.15,.85):
            start=time.perf_counter()
            initial=default.copy()
            if seed is not None:
                initial[0],initial[1]=seed,.60
            trial=least_squares(residual,initial,bounds=(bounds[0],bounds[1]),max_nfev=30,
                                ftol=7e-5,gtol=2e-4,xtol=5e-5)
            rows.append(dict(seed=seed,cost=float(trial.cost),evaluations=trial.nfev,seconds=time.perf_counter()-start))
            if best is None or trial.cost<best.cost:
                best=trial
        v=e.extended(dict(zip(names,best.x)))*10
        np.savez_compressed(out/path.name,reference=ref,reference_faces=a['reference_faces'],faces=a['faces'],E10=v)
        dump(out/(path.stem+'.json'),rows)
        print(path.stem,best.cost,flush=True)


if __name__=='__main__':
    main(*map(Path,sys.argv[1:]))

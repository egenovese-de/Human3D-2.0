import json
import numpy as np
unique = np.unique
from g1_engine import Engine, MACROS
np.unique = unique
engine = Engine()
selected = {name: engine.mac[name] for name in MACROS}
stems = ("torso/torso-scale-depth", "torso/torso-scale-horiz", "buttocks/buttocks-volume",
         "pelvis/pelvis-scale-depth", "hip/hip-scale-horiz", "measure/measure-bust-circ",
         "measure/measure-waist-circ", "measure/measure-hips-circ", "measure/measure-thigh-circ",
         "measure/measure-upperarm-circ")
local = {}
for stem in stems:
    keys = [key for key in engine.mods if key.startswith(stem+"-") and engine.defs[key]]
    if len(keys) != 1:
        print("Omitted unavailable or ambiguous field:",stem,keys)
        continue
    k = keys[0]
    local[k] = engine.defs[k]
for k, (m, _) in engine.mods.items():
    if not m.isMacro() and engine.default[k] and engine.defs[k]:
        local.setdefault(k, engine.defs[k])
indices = sorted({idx for rows in [*engine.group_rows.values(), *local.values()] for idx, _ in rows})
index_map = {idx:i for i,idx in enumerate(indices)}
def entries(rows):
    return [[index_map[i], *f] for i, f in rows]
doc = dict(schema_version=1, upstream="1f508f6083b2f823dab15de924b3bde72e08d77c",
    globals=list(selected), groups=[entries(rows) for rows in engine.group_rows.values()],
    local=[dict(name=k, targets=entries(rows), left=engine.mods[k][0].left,
                right=engine.mods[k][0].right,center=engine.mods[k][0].center,
                default=engine.default[k], fitted=k.startswith(stems)) for k,rows in local.items()],
    files=[[engine.rows[i]["path"],engine.rows[i]["sha256"],engine.paths[i].stat().st_size] for i in indices])
rng=np.random.default_rng(37379)
native=[]
for overrides in ({}, {engine.mac["Weight"]:.82,engine.mac["Muscle"]:.65}, {engine.mac["Gender"]:.18,engine.mac["Age"]:.70, next(iter(local)):.52}):
    vertices, _ = engine.native(overrides)
    controls={next((name for name,key in selected.items() if key==k),k):v for k,v in overrides.items()}
    ii=np.sort(rng.choice(len(vertices),100,replace=False))
    native.append(dict(controls=controls,indices=ii.tolist(),vertices=vertices[ii].tolist()))
doc["parity_controls"]=native
with open("DOCS/manifests/m7-g1-native.json","w") as f:
    json.dump(doc,f,separators=(",",":"))
    f.write("\n")
print(len(indices),sum(x[2] for x in doc["files"]))

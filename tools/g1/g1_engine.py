"""Headless upstream oracle and independent sparse evaluator for G1."""
from pathlib import Path
from math import prod
import hashlib
import json
import os
import numpy as np
from scipy.sparse import csc_matrix
import algos3d
import files3d
import human
import humanmodifier as hm
import targets
from human3d import bootstrap
from human3d.frozen_body import deform_vertices, morph_controls
from human3d.native_rig import rebind_joints

U = Path(os.environ["U"]).resolve()
DATA = U / "data"
MACROS = {"Gender":"gender", "Age":"age", "Weight":"weight", "Muscle":"muscle",
          "Height":"height", "BodyProportions":"proportions",
          "BreastSize":"cup", "BreastFirmness":"firmness"}
DEFAULT_FILES = ("modeling", "measurement", "bodyshapes")

class Headless(human.Human):
    def __init__(self):
        self.setDefaultValues()
        self.targetsDetailStack = {}
        self.blockEthnicUpdates = False

    def callEvent(self, *args):
        pass

def metadata(path):
    raw = path.read_bytes()
    rows = []
    for line in raw.splitlines():
        values = line.split()
        if len(values) == 4 and not values[0].startswith(b"#"):
            rows.append((int(values[0]), *map(float, values[1:])))
    a = np.asarray(rows, dtype=float).reshape(-1,4)
    idx = a[:,0].astype(int)
    d = a[:,1:]
    return raw, idx, d

class Engine:
    def __init__(self):
        targets._targets = targets.Targets(str(DATA))
        self.mesh = files3d.loadMesh(str(DATA / "3dobjs/base.obj"), maxFaces=8)
        assert self.mesh is not False
        self.paths = sorted((DATA / "targets").rglob("*.target"))
        raw_specs = {p.name:p for p in (DATA/"3dobjs/base.obj", DATA/"rigs/default.mhskel",
                     DATA/"rigs/default_weights.mhw", *self.paths)}
        expected = bootstrap.ASSETS | bootstrap.MORPH_ASSETS | bootstrap.TORSO_ASSETS
        assert all(hashlib.sha256(raw_specs[n].read_bytes()).hexdigest()==h for n,h in expected.items())
        self.asset_hashes = expected
        self.body = {
            "mesh":bootstrap._mesh(raw_specs["base.obj"].read_text()),
            "morph_targets":bootstrap._morph_targets(
                {n:raw_specs[n].read_bytes() for n in expected.keys()-bootstrap.ASSETS.keys()},
                len(self.mesh.coord))}
        self.body["rig"] = bootstrap._rig(json.loads(raw_specs["default.mhskel"].read_text()),
                                       json.loads(raw_specs["default_weights.mhw"].read_text()),
                                       self.body["mesh"]["vertices"])
        self.base = np.asarray(self.body["mesh"]["vertices"])
        self.faces = np.asarray([[x[0] for x in f["corners"]] for f in self.body["mesh"]["faces"] if f["group"]=="body"])
        self.skin = np.unique(self.faces)
        self.mods = {}
        for name in DEFAULT_FILES:
            source = DATA/"modifiers"/f"{name}_modifiers.json"
            for mod in hm.loadModifiers(str(source), None):
                self.mods[mod.fullName]=(mod,source)
        self.by_path = {str(p):i for i,p in enumerate(self.paths)}
        self.rows = []
        indices, indptr, vals = [], [0], []
        product_names = bootstrap.MORPH_ASSETS.keys() | bootstrap.TORSO_ASSETS.keys()
        for p in self.paths:
            raw,idx,delta = metadata(p)
            assert np.isfinite(delta).all() and np.all((0<=idx)&(idx<len(self.base))), p
            order = idx.argsort()
            idx,delta = idx[order],delta[order]
            assert len(np.unique(idx))==len(idx), p
            indices.append((idx[:,None]*3+np.arange(3)).ravel().astype(np.int32))
            vals.append(delta.ravel())
            indptr.append(indptr[-1]+delta.size)
            directions = np.sign(delta)
            starts=np.flatnonzero(np.r_[True,np.diff(idx)!=1]) if len(idx) else np.array([],dtype=int)
            ends=np.r_[starts[1:]-1,len(idx)-1] if len(idx) else starts
            self.rows.append(dict(path=str(p.relative_to(U)),sha256=hashlib.sha256(raw).hexdigest(),
                 region=p.relative_to(DATA/"targets").parts[0],
                 affected_vertices=len(idx), affected_vertex_runs=np.c_[idx[starts],idx[ends]].tolist(), vertex_index_sha256=hashlib.sha256(idx.astype("<u4").tobytes()).hexdigest(),
                 index_range=[int(idx.min()),int(idx.max())] if len(idx) else None,
                 axis_negative=(directions<0).sum(0).tolist(),axis_positive=(directions>0).sum(0).tolist(),
                 delta_min=delta.min(0).tolist() if len(delta) else None,delta_max=delta.max(0).tolist() if len(delta) else None,
                 product_admitted=p.name in product_names))
        self.matrix = csc_matrix((np.concatenate(vals),np.concatenate(indices),indptr),shape=(self.base.size,len(self.paths)))
        self.mac = {m.name:key for key,(m,_) in self.mods.items() if m.isMacro()}
        self.default = {key:mod.getDefaultValue() for key,(mod,_) in self.mods.items()}
        self.defs = {}
        for key,(mod,_) in self.mods.items():
            self.defs[key] = [(self.by_path[str(Path(p).resolve())], tuple(f)) for p,f in mod.targets]
        self.macro_keys = list(dict.fromkeys(m.groupName for m,_ in self.mods.values() if m.isMacro()))
        self.group_mod = {m.groupName:key for key,(m,_) in self.mods.items() if m.isMacro()}
        self.default_factors = self.factors({})
        self.group_rows = {g:self.defs[self.group_mod[g]] for g in self.macro_keys}

    def native(self, overrides, reverse=False):
        h = Headless()
        for key,(mod,_) in self.mods.items():
            mod.human = h
            if mod.isMacro() and mod.name not in ("African","Asian","Caucasian"):
                getattr(h,mod.setter)(overrides.get(key,self.default[key]),updateModifier=False)
        for n in ("African","Asian","Caucasian"):
            setattr(h,n.lower()+"Val",overrides.get(self.mac[n],h.__dict__[n.lower()+"Val"]))
        selected = [(self.mods[key][0], overrides.get(key,self.default[key]))
                    for key in dict.fromkeys([*self.group_mod.values(),*overrides,
                        *(k for k,v in self.default.items() if v and not self.mods[k][0].isMacro())])
                    if not self.mods[key][0].isMacro() or key in self.group_mod.values()]
        if reverse:
            selected.reverse()
        for mod,value in selected:
            hm.ManagedTargetModifier.setValue(mod,value,skipDependencies=True)
        algos3d.resetObj(self.mesh,update=False,calcNorm=False)
        for path, weight in h.targetsDetailStack.items():
            algos3d.loadTranslationTarget(self.mesh,path,weight,None,0,0)
        return np.array(self.mesh.coord,dtype=float), dict(h.targetsDetailStack)

    def factors(self, overrides):
        v = {n:overrides.get(self.mac[n],0.5) for n in MACROS}
        age=v["Age"]
        f = {"female":1-v["Gender"],"male":v["Gender"],
             "baby":max(0,1-age*5.333) if age<.5 else 0,
             "child":max(0,min(1,age*5.333)-max(0,(age-.1875)*3.2)) if age<.5 else 0,
             "young":max(0,(age-.1875)*3.2) if age<.5 else 2-2*age,"old":max(0,2*age-1)}
        for n,lo,mid,hi in (
            ("Weight","minweight","averageweight","maxweight"),
            ("Muscle","minmuscle","averagemuscle","maxmuscle"),
            ("Height","minheight","averageheight","maxheight"),
            ("BodyProportions","uncommonproportions","regularproportions","idealproportions"),
            ("BreastSize","mincup","averagecup","maxcup"),
            ("BreastFirmness","minfirmness","averagefirmness","maxfirmness")):
            left=max(0,1-2*v[n]); right=max(0,2*v[n]-1)
            f.update({lo:left,hi:right})
            if mid:
                f[mid]=1-left-right
        for n in ("African","Asian","Caucasian"):
            f[n.lower()]=overrides.get(self.mac[n],1/3)
        return f

    def extended(self, overrides, frozen_regional=False, vertices=None):
        f=self.factors(overrides)
        result={}
        for group, rows in self.group_rows.items():
            for idx, tokens in rows:
                w=prod(f[t] for t in tokens[:-1]) if len(tokens)>1 else 1
                if w: result[idx]=w
        changes={k:v for k,v in overrides.items() if not self.mods[k][0].isMacro()}
        for key,value in self.default.items():
            if value and not self.mods[key][0].isMacro():
                changes.setdefault(key,value)
        for key,value in changes.items():
            m=self.mods[key][0]
            groups={m.right:max(0,value),m.left:max(0,-value)}
            if m.center:
                groups[m.center]=1-abs(value)
            factors=self.default_factors if frozen_regional else f
            for idx,tokens in self.defs[key]:
                w=groups[tokens[-1]]
                for t in tokens[:-1]:
                    w*=factors[t]
                if w: result[idx]=w
                else: result.pop(idx,None)
        i=np.fromiter(result,int)
        matrix=self.matrix if vertices is None else self.train_matrix
        base=self.base.ravel() if vertices is None else self.base.ravel()[vertices]
        return (base+matrix[:,i]@np.fromiter(result.values(),float)).reshape(-1,3)

    def current(self, controls):
        return np.asarray(deform_vertices(self.body,controls))

    def inventory(self):
        modifiers=[]
        regions={"macrodetails":"global","armslegs":"limbs and skeletal proportions","measure":"measurement and skeletal proportions",
                 "torso":"torso","breast":"torso","buttocks":"torso","stomach":"torso","hip":"torso","pelvis":"torso","asym":"asymmetry"}
        for key,(m,source) in sorted(self.mods.items()):
            group=m.groupName
            rows=[dict(target=self.rows[i]["path"], factors=list(f)) for i,f in self.defs[key]]
            modifiers.append(dict(identifier=key,source=str(source.relative_to(U)),group=group,
                region=regions.get(group,"global" if group.startswith("macrodetails") else "head, face or local"),
                modifier_type=type(m).__name__,range=[m.getMin(),m.getMax()],default=m.getDefaultValue(),
                interpolation="product of dependency factors; shared macro group" if m.isMacro() else
                "signed piecewise linear endpoints, center 1-|v| when defined, times native factors",
                depends_on=sorted(m.macroDependencies), symmetry_side=m.getSymmetrySide(),
                symmetric_opposite=m.getSymmetricOpposite(),targets=rows,
                verified_available=bool(rows),product_support="admitted target subset" if any(
                self.rows[i]["product_admitted"] for i,_ in self.defs[key]) else "not wired",
                reconstruction_value="candidate prior" if m.isMacro() else "local field subject to observability and validation"))
        return dict(upstream="1f508f6083b2f823dab15de924b3bde72e08d77c",
            compatibility="MakeHuman pinned hm08 seed OBJ and zero-based source indices; ordered x,y,z in decimetres",
            assets=self.asset_hashes, product_controls=morph_controls(self.body),modifiers=modifiers, target_files=self.rows)

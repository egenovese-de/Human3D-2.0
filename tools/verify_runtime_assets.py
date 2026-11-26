"""Explicit CI-only provisioning followed by offline verification; no asset publication."""
import json
import tempfile
from pathlib import Path
from urllib.request import urlopen
from unittest.mock import patch
from human3d.bootstrap import ASSETS, MORPH_ASSETS, TORSO_ASSETS, freeze_neutral
from human3d.asset_preflight import verify_assets
from human3d.vision import PoseLandmarker

ROOT = Path(__file__).resolve().parents[1]
REV = "1f508f6083b2f823dab15de924b3bde72e08d77c"
BASE = "https://raw.githubusercontent.com/makehumancommunity/makehuman/" + REV + "/"
MODEL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"

def main():
    expected = ASSETS | MORPH_ASSETS | TORSO_ASSETS
    sources = {}
    for manifest in (ROOT/"DOCS"/"manifests").glob("makehuman*.json"):
        m = json.loads(manifest.read_text(encoding="utf-8"))
        assert m["revision"] == REV
        for item in m["files"]:
            name = Path(item["path"]).name
            if expected.get(name) == item["sha256"]:
                sources[name] = (BASE + m.get("source_prefix","") + item["path"], item["bytes"])
    assert sources.keys() == expected.keys()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        assets = root/"assets"
        assets.mkdir()
        for name,(url,size) in sources.items():
            with urlopen(url,timeout=60) as response:
                data = response.read(size+1)
            assert len(data) == size, name
            (assets/name).write_bytes(data)
        model = root/"model.task"
        with urlopen(MODEL,timeout=60) as response:
            model.write_bytes(response.read(32*1024*1024))
        with patch("socket.socket",side_effect=AssertionError("network forbidden")):
            report = verify_assets(model,assets)
            print(json.dumps(report),flush=True)
            assert report["status"] == "PASS"
            PoseLandmarker(model).close()
            digest = freeze_neutral(assets,root/"frozen",with_morphs=True)
            from human3d.frozen_body import load_frozen_body
            body = load_frozen_body(root/"frozen"/(digest+".json"))
            print("Canonical frozen structure: PASS",flush=True)
            from human3d.frozen_body import deform_vertices, morph_controls
            from human3d.native_rig import validate_rebind
            from copy import deepcopy
            original = deepcopy(body)
            frozen_path = root/"frozen"/(digest+".json")
            original_bytes = frozen_path.read_bytes()
            controls = {name: .125 for name in morph_controls(body)}
            vertices = deform_vertices(body, controls)
            assert len(vertices) == len(body["mesh"]["vertices"])
            assert vertices != tuple(map(tuple, body["mesh"]["vertices"]))
            validate_rebind(body, vertices)
            assert body == original
            assert freeze_neutral(assets,root/"frozen",with_morphs=True) == digest
            assert frozen_path.read_bytes() == original_bytes
            assert load_frozen_body(frozen_path) == original
            print("Canonical post-freeze deformation/rebind and repeat freeze immutability: PASS",flush=True)
            import numpy as np
            uv = np.asarray(body["mesh"]["texcoords"])
            assert np.isfinite(uv).all() and np.all((uv >= 0) & (uv <= 1)), (uv.min(), uv.max())
            print("Canonical UV domain: PASS", float(uv.min()), float(uv.max()), flush=True)
            assert len(body["morph_targets"]) == 14
            assert body["source_asset_digests"] == expected
            from human3d.texture_bake import _hidden_vertices
            from human3d.anatomical_evidence import REGION_LANDMARKS
            rig = body["rig"]
            assert not _hidden_vertices(rig, ())
            regions = {name: _hidden_vertices(rig, (name,)) for name in REGION_LANDMARKS}
            for name, vertices in regions.items():
                assert vertices, ("empty canonical region", name)
                assert all(0 <= i < len(rig["skin"]) for i in vertices)
            for left, right in (("left_arm","right_arm"),("left_leg","right_leg")):
                assert not regions[left] & regions[right]
            print("Canonical hidden region mapping: PASS", json.dumps({name:len(vertices) for name,vertices in regions.items()},sort_keys=True),flush=True)
            profile_pipeline(body, root, assets)
            print("Actual pinned assets: PASS; frozen digest:",digest,flush=True)

def profile_pipeline(body, root, assets):
    """Canonical mesh, synthetic raster, no real photographs or inference."""
    import time
    import numpy as np
    from io import BytesIO
    from PIL import Image, ImageDraw
    from human3d.alignment import Alignment, Camera
    from human3d.fitting import fit_body
    from human3d.mask_review import SubjectMask
    from human3d.appearance import AppearanceView
    from human3d.texture_bake import bake_atlas
    from human3d.garment_fit import fit_garment
    from human3d.garments import GarmentAsset
    from human3d.usd_export import export_body
    from human3d.frozen_body import deform_vertices
    from human3d.native_rig import validate_rebind, pose_transforms, skin_vertices
    def measure(name, operation):
        start = time.perf_counter()
        result = operation()
        print("AUD-06 stage " + json.dumps({"stage": name, "seconds": time.perf_counter()-start,
              "disk_bytes": sum(p.stat().st_size for p in root.rglob("*") if p.is_file())}), flush=True)
        return result
    measure("freeze", lambda: freeze_neutral(assets, root/"profile-frozen", with_morphs=True))
    points = np.asarray(body["mesh"]["vertices"])
    lo, hi = points.min(axis=0), points.max(axis=0)
    scale = 200 / (hi[1]-lo[1])
    camera = Camera(0, scale, complex(128-scale*(hi[0]+lo[0])/2,128+scale*(hi[1]+lo[1])/2),1)
    alignment = Alignment(camera,0,{})
    size = (256,256)
    raster = Image.new("L",size)
    draw = ImageDraw.Draw(raster)
    projected = [camera.project(p) for p in points]
    for face in body["mesh"]["faces"]:
        if face["group"] == "body":
            draw.polygon([(projected[i].real,projected[i].imag) for i,_ in face["corners"]],fill=255)
    buffer = BytesIO()
    raster.save(buffer,format="PNG")
    mask = SubjectMask("a"*64,0,buffer.getvalue())
    fit = measure("fit_body",lambda: fit_body(body,mask,alignment))
    def pose():
        neutral = deform_vertices(body,fit.controls)
        joints = validate_rebind(body,neutral)
        return skin_vertices(neutral,body["rig"]["skin"],pose_transforms(body["rig"],joints,alignment))
    measure("deform_rebind_pose",pose)
    foreground = np.asarray(raster)>0
    rgb = np.full((256,256,3),120,dtype=np.uint8)
    view = AppearanceView(rgb,foreground,np.zeros_like(foreground),alignment)
    views = {"target":(view,size)}
    atlas = measure("body_atlas_256",lambda: bake_atlas(body,fit.controls,views,"target",size=256))
    garment = measure("garment_top",lambda: fit_garment(body,fit,view,size,"top",optimize=False))
    garment_atlas = measure("garment_atlas_256",lambda: bake_atlas(body,fit.controls,views,"target",size=256,garment=garment.garment))
    destination = root/"profile.usdz"
    measure("usdz",lambda: export_body(destination,body,fit,alignment,texture=atlas.color,
        garments=[GarmentAsset(garment.garment,garment_atlas.color,garment_atlas.observed_fraction)]))
    assert destination.stat().st_size > 0
    print("AUD-06 package_bytes",destination.stat().st_size,flush=True)

if __name__ == "__main__":
    main()

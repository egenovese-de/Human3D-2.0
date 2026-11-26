"""Audit native body and garment USDZ parts using the pinned OpenUSD wheel."""
import json
from pathlib import Path
import sys
from zipfile import ZipFile

from pxr import Usd, UsdGeom, UsdSkel


def audit(path):
    with ZipFile(path) as package:
        assert package.testzip() is None
        members = package.namelist()
    stage = Usd.Stage.Open(str(path))
    mesh_prims = [prim for prim in stage.Traverse() if prim.IsA(UsdGeom.Mesh)]
    topology = {}
    for prim in mesh_prims:
        mesh = UsdGeom.Mesh(prim)
        points = mesh.GetPointsAttr().Get()
        binding = UsdSkel.BindingAPI(prim)
        skeleton = binding.GetInheritedSkeleton()
        topology[str(prim.GetPath())] = {
            "vertices": len(points),
            "faces": len(mesh.GetFaceVertexCountsAttr().Get()),
            "skeleton": str(skeleton.GetPath()) if skeleton else None,
            "has_joint_indices": bool(binding.GetJointIndicesPrimvar()),
            "has_uv": bool(UsdGeom.PrimvarsAPI(prim).GetPrimvar("st")),
        }
    return {"mesh_topology": topology, "archive_members": members,
            "skeleton_count": sum(prim.IsA(UsdSkel.Skeleton) for prim in stage.Traverse())}


if __name__ == "__main__":
    scratch, output = map(Path, sys.argv[1:])
    cases = sorted(scratch.glob("ai-native-*/garment.usdz"))
    output.write_text(json.dumps({p.parent.name: audit(p) for p in cases}, indent=2) + "\n")

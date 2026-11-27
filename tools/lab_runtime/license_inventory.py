import ast
import json
from pathlib import Path
import subprocess

paths=subprocess.check_output(["git","ls-files","*.py"],text=True).splitlines()
rows=[]
for name in paths:
    source=Path(name).read_text(encoding="utf-8-sig")
    tree=ast.parse(source,filename=name)
    imports=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            imports.extend(a.name for a in node.names if a.name.split(".")[0] in {"bpy","mathutils","bmesh"})
        elif isinstance(node,ast.ImportFrom) and node.module and node.module.split(".")[0] in {"bpy","mathutils","bmesh"}:
            imports.append(node.module)
    if imports:
        rows.append({"path":name,"imports":sorted(set(imports)),"header":source.splitlines()[:3]})
print("BLENDER_SOURCE_INVENTORY="+json.dumps({"scanned":len(paths),"files":rows}))

assert len(rows)==22, "Blender inventory changed; review required"
assert all("# SPDX-License-Identifier: GPL-3.0-or-later" in row["header"] for row in rows)
assert Path("LICENSES/GPL-3.0-or-later.txt").stat().st_size > 30000
print("BLENDER_LICENSE_GATE_PASS",len(rows))

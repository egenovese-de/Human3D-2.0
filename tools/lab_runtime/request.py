import json
import os
import re
from bootstrap import ROOT, LOCK, digest

def main():
    request=json.loads((ROOT/"lab/experiments/request.json").read_text())
    if set(request)!={"schema_version","experiment","source_revision","groups","request_id"} or request["schema_version"]!=1:
        raise ValueError("invalid request")
    if request["experiment"] not in ("lr-004-smoke","lr-005-q-boundaries","lr-005-m6-bind"):
        raise ValueError("experiment not admitted")
    if not re.fullmatch(r"[a-zA-Z0-9_-]+",request["request_id"]):
        raise ValueError("invalid request id")
    if not re.fullmatch(r"[0-9a-f]{40}",request["source_revision"]):
        raise ValueError("invalid source revision")
    config="lab/experiments/"+request["experiment"]+".json"
    if json.loads((ROOT/config).read_text())["source_revision"]!=request["source_revision"]:
        raise ValueError("source mismatch")
    groups=request["groups"]
    if not isinstance(groups,list) or any(g not in ("morph02","anatomical_torso") for g in groups) or len(set(groups))!=len(groups):
        raise ValueError("invalid groups")
    lock=json.loads(LOCK.read_text())
    import hashlib
    inputs=[LOCK,ROOT/lock["platforms"]["windows"]["dependency_lock"],ROOT/"tools/lab_runtime/bootstrap.py"]
    inputs += [ROOT/lock["asset_groups"][g]["manifest"] for g in sorted(set(groups)|{"foundation","pose_lite"})]
    key="lab-windows-2022-x64-"+hashlib.sha256("".join(digest(p) for p in inputs).encode()).hexdigest()
    with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf-8") as out:
        for k,v in {"source":request["source_revision"],"config":config,"groups":" ".join(groups),"cache_key":key}.items():
            print(f"{k}={v}",file=out)
if __name__=="__main__":
    main()

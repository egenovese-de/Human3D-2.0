"""Default-deny artifact staging and offline verification."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from bootstrap import ROOT, safe, digest

def verify(root):
    manifest=json.loads((root/"artifact_manifest.json").read_text())
    actual={p.relative_to(root).as_posix():{"sha256":digest(p),"bytes":p.stat().st_size}
            for p in root.rglob("*") if p.is_file() and p!=root/"artifact_manifest.json"}
    if actual!=manifest["files"] or not actual:
        raise ValueError("artifact inventory mismatch")
    print("ARTIFACT_VERIFY_PASS",len(actual))
    return manifest

def stage(config,run,runtime,out):
    config=config.resolve()
    admitted=ROOT/"lab/experiments/lr-004-smoke.json"
    if config!=admitted.resolve():
        raise ValueError("experiment not admitted for publication")
    c=json.loads(config.read_text())
    report=json.loads((run/"run_manifest.json").read_text())
    if report["status"]!="PASS" or report["source_revision"]!=c["source_revision"]:
        raise ValueError("run not qualified")
    policy=json.loads((ROOT/"lab/manifests/artifact-admission.json").read_text())
    fixture=ROOT/"lab/fixtures/smoke.usda"
    def blob(p):
        return subprocess.check_output(["git","-C",str(ROOT),"hash-object","--",str(p)],text=True).strip()
    if blob(fixture)!=policy["fixture_blob"] or blob(config)!=policy["config_blob"]:
        raise ValueError("unapproved fixture or configuration")
    if len(report["stages"])!=len(c["stages"]):
        raise ValueError("stage count mismatch")
    out.mkdir(parents=True,exist_ok=False)
    def copy(src,rel):
        if src.is_symlink() or not src.is_file():
            raise ValueError("invalid artifact input")
        dest=safe(out,rel)
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(src,dest)
    for i,(s,result) in enumerate(zip(c["stages"],report["stages"])):
        if result["status"]!="PASS" or set(result["outputs"])!=set(s["expected"]):
            raise ValueError("stage outputs mismatch")
        for name,sha in result["outputs"].items():
            src=safe(run,f"{i}/{name}")
            if digest(src)!=sha:
                raise ValueError("stage output changed")
            copy(src,f"{i}/{name}")
        copy(run/str(i)/"execution.log",f"{i}/execution.log")
    for name in ("runtime_report.json","bootstrap_report.json"):
        copy(runtime/name,name)
    copy(run/"run_manifest.json","run_manifest.json")
    copy(config,"experiment.json")
    copy(fixture,"inputs/smoke.usda")
    copy(ROOT/"lab/manifests/artifact-admission.json","admission.json")
    files={p.relative_to(out).as_posix():{"sha256":digest(p),"bytes":p.stat().st_size} for p in out.rglob("*") if p.is_file()}
    manifest={"schema_version":1,"scope":"original procedural fixture only","retention_days":7,
              "source_revision":c["source_revision"],"lab_revision":subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip(),
              "run_id":os.environ.get("GITHUB_RUN_ID"),"run_attempt":os.environ.get("GITHUB_RUN_ATTEMPT"),
              "config_sha256":digest(config),"files":files}
    (out/"artifact_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    verify(out)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--verify",type=Path)
    p.add_argument("--config",type=Path)
    p.add_argument("--run",type=Path)
    p.add_argument("--runtime",type=Path)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    if a.verify: verify(a.verify.resolve())
    else: stage(a.config,a.run,a.runtime,a.output.resolve())

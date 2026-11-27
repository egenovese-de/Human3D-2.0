"""Execute admitted operations sequentially using the isolated runtime."""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from bootstrap import ROOT, LOCK, safe, digest
from historical_inputs import verify_holdout, verify_rig

HISTORICAL={"q_evidence_boundaries":"tools/q/finalization/evidence_boundaries.py","m6_bind_control":"tools/lab_runtime/m6_bind_control.py"}
OPERATIONS={"numerical": {"seed","expected"}, "blender_roundtrip":{"input","expected"}, **{op:{"expected"} for op in HISTORICAL}, "q_validate_holdout":{"expected"}, "m6_audit_source_rig":{"expected"}, "m6_audit_native":{"expected"}}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True,type=Path)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--runtime",type=Path,default=ROOT/".lab-runtime")
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--historical-workspace",type=Path)
    a=p.parse_args()
    c=json.loads(a.config.read_text())
    if set(c)!={"schema_version","id","source_revision","stages"} or c["schema_version"]!=1 or not re.fullmatch(r"[a-zA-Z0-9_-]+",c["id"]) or not re.fullmatch(r"[0-9a-f]{40}",c["source_revision"]):
        raise ValueError("invalid experiment configuration")
    if not isinstance(c["stages"],list) or not c["stages"]:
        raise ValueError("stages required")
    for s in c["stages"]:
        op=s.get("operation")
        if op not in OPERATIONS or set(s)-({"framing"} if op=="blender_roundtrip" else set())!=(OPERATIONS[op]|{"operation","timeout"}):
            raise ValueError("invalid operation or arguments")
        if type(s["timeout"]) is not int or not 1<=s["timeout"]<=1800:
            raise ValueError("invalid timeout")
        if op=="numerical" and (type(s["seed"]) is not int or not 0<=s["seed"]<2**32):
            raise ValueError("invalid seed")
        if not isinstance(s["expected"],list) or not s["expected"]:
            raise ValueError("expected outputs required")
        for name in s["expected"]:
            safe(a.output,name)
        if op=="blender_roundtrip":
            if not safe(ROOT,s["input"]).is_file():
                raise ValueError("missing input")
    source=subprocess.check_output(["git","-C",str(a.source),"rev-parse","HEAD"],text=True).strip()
    if source!=c["source_revision"]:
        raise ValueError("source revision mismatch")
    out=a.output.resolve()
    out.mkdir(parents=True,exist_ok=False)
    root=a.runtime.resolve()
    windows=platform.system()=="Windows"
    py=root/"venv"/("Scripts/python.exe" if windows else "bin/python")
    blender=root/"blender"/("blender.exe" if windows else "blender")
    env=dict(os.environ,**json.loads(LOCK.read_text())["environment"])
    env.update(PYTHONPATH=str(a.source.resolve()/"src"),OPENBLAS_NUM_THREADS="1",OMP_NUM_THREADS="1",MKL_NUM_THREADS="1",PYTHONHASHSEED="0")
    report={"schema_version":1,"id":c["id"],"source_revision":source,"config_sha256":__import__("hashlib").sha256(json.dumps(c,sort_keys=True,separators=(",",":")).encode()).hexdigest(),"status":"FAIL","stages":[]}
    try:
        for i,s in enumerate(c["stages"]):
            stage=out/str(i)
            stage.mkdir()
            if s["operation"]=="numerical":
                cmd=[py,ROOT/"tools/lab_runtime/numerical_probe.py","--seed",s["seed"],"--output",stage/"numerical.json"]
            elif s["operation"]=="q_validate_holdout":
                if a.historical_workspace is None:
                    raise ValueError("historical workspace required")
                provenance=verify_holdout(a.historical_workspace.resolve())
                (stage/"input_manifest.json").write_text(json.dumps(provenance,indent=2))
                cmd=[py,ROOT/"tools/q/validate.py",a.historical_workspace.resolve()/"holdout",stage/"metrics.json"]
            elif s["operation"]=="m6_audit_source_rig":
                if a.historical_workspace is None:
                    raise ValueError("historical workspace required")
                workspace=a.historical_workspace.resolve()
                provenance=verify_rig(workspace)
                (stage/"input_manifest.json").write_text(json.dumps(provenance,indent=2))
                cmd=[py,ROOT/"tools/lab_runtime/m6_source_replay.py",workspace/"rig-fixtures",stage/"metrics.json"]
            elif s["operation"]=="m6_audit_native":
                if a.historical_workspace is None:
                    raise ValueError("historical workspace required")
                cmd=[py,ROOT/"tools/lab_runtime/m6_native_replay.py",a.historical_workspace.resolve(),stage/"metrics.json"]
            elif s["operation"] in HISTORICAL:
                cmd=[py,ROOT/HISTORICAL[s["operation"]],stage/"metrics.json"]
            else:
                cmd=[blender,"--background","--factory-startup","--python-exit-code","1","--python",ROOT/"tools/lab_runtime/blender_runner.py","--","--input",safe(ROOT,s["input"]),"--output",stage]
            if s["operation"]=="blender_roundtrip" and "framing" in s:
                cmd.extend(["--framing",safe(out,s["framing"])])
            entry={"operation":s["operation"],"status":"FAIL"}
            report["stages"].append(entry)
            if s["operation"] in HISTORICAL:
                entry["script_sha256"]=digest(ROOT/HISTORICAL[s["operation"]])
                if s["operation"]=="m6_bind_control":
                    entry["original_script_sha256"]=digest(ROOT/"tools/m6/audit_bind_frames.py")
            start=time.monotonic()
            try:
                with (stage/"execution.log").open("wb") as log:
                    proc=subprocess.run([str(x) for x in cmd],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=s["timeout"])
                entry["exit_code"]=proc.returncode
                if proc.returncode:
                    raise RuntimeError("operation failed")
                entry["outputs"]={name:digest(safe(stage,name)) for name in s["expected"]}
                entry["status"]="PASS"
            except subprocess.TimeoutExpired:
                entry["error"]="timeout"
                raise
            finally:
                entry["seconds"]=time.monotonic()-start
        report["status"]="PASS"
    finally:
        (out/"run_manifest.json").write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps(report))
if __name__=="__main__":
    main()

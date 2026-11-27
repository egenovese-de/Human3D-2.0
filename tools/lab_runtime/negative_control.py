"""Exercise actual runtime failures without modifying the shared cache."""
import json, os, subprocess, sys, tempfile
from pathlib import Path
from bootstrap import ROOT, acquire
from urllib.error import URLError

def main():
    runtime=ROOT/".lab-runtime"
    source=ROOT/".lab-source"
    py=runtime/"venv/Scripts/python.exe"
    blender=runtime/"blender/blender.exe"
    env=dict(os.environ,PYTHONPATH=str(source/"src"))
    results={}
    with tempfile.TemporaryDirectory() as tmp:
        t=Path(tmp)
        f=t/"input"; f.write_bytes(b"bad")
        for name,url,kind in (("checksum",f.as_uri(),ValueError),("missing_asset",(t/"absent").as_uri(),URLError)):
            try: acquire(url,t/"download","0"*64)
            except kind: results[name]="PASS"
            else: raise AssertionError(name)
        assert not (t/"download").exists()
        def reject(name,cmd,marker):
            p=subprocess.run([str(x) for x in cmd],env=env,capture_output=True,text=True,timeout=120)
            assert p.returncode!=0 and marker in p.stdout+p.stderr,(name,p.stdout,p.stderr)
            results[name]={"status":"PASS","exit_code":p.returncode}
        c=t/"invalid.json"; c.write_text("{}")
        reject("invalid_config",[sys.executable,ROOT/"tools/lab_runtime/runner.py","--config",c,"--source",source,"--output",t/"invalid"],"invalid experiment configuration")
        reject("python_failure",[py,ROOT/"tools/lab_runtime/native_control.py","--runtime",t,"--output",t],"missing or corrupt asset")
        bad=t/"bad.usda"; bad.write_text("invalid USD")
        reject("blender_failure",[blender,"--background","--factory-startup","--python-exit-code","1","--python",ROOT/"tools/lab_runtime/blender_runner.py","--","--input",bad,"--output",t],"Error")
        try: subprocess.run([str(py),"-c","import time; time.sleep(10)"],timeout=1,check=True)
        except subprocess.TimeoutExpired: results["timeout"]="PASS"
        else: raise AssertionError("timeout")
    report={"status":"PASS","checks":results,"scope":"actual isolated child failures and acquisition errors; timeout subprocess primitive"}
    (ROOT/"lab-output/experiment/negative_runtime.json").write_text(json.dumps(report,indent=2))
    print("NEGATIVE_RUNTIME="+json.dumps(report))
if __name__=="__main__": main()

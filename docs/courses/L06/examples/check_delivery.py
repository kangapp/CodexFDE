"""Reuse L05 execution-evidence verification with the L06 frozen file set."""
import importlib.util
from pathlib import Path
from prepare_checks import FROZEN
path=Path(__file__).resolve().parents[2]/'L05/examples/check_delivery.py'
spec=importlib.util.spec_from_file_location('l06_delivery_verifier',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.CHECKS=FROZEN
original_verify=module.verify
def verify(*args,**kwargs):
    result=original_verify(*args,**kwargs)
    result['boundary']='仅核对执行器采集区间、记录文件现状及六份冻结检查；人工接受仍独立进行'
    return result
module.verify=verify
if __name__=='__main__':raise SystemExit(module.main())

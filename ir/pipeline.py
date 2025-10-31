from ir.ir_types import Function
from ir.const_fold import const_fold_function
from ir.dce import drop_unreachable, dead_store_elim

def optimize_function(fn: Function) -> None:
    changed=True
    while changed:
        changed=False
        if const_fold_function(fn):   changed=True
        if drop_unreachable(fn):      changed=True
        if dead_store_elim(fn):       changed=True

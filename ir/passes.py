# ir/passes.py
from typing import Callable, Dict, List
from ir.ir_types import Function
from ir.const_prop import const_propagate_function
from ir.const_fold import const_fold_function
from ir.dce import drop_unreachable, dead_store_elim

# Only import these if these are working now
try:
    from ir.copy_prop import copy_propagate_function
except ImportError:
    def copy_propagate_function(fn: Function) -> bool: return False
try:
    from ir.algebra import algebra_simplify_function
except ImportError:
    def algebra_simplify_function(fn: Function) -> bool: return False

# Map canonical pass names to callables
PASS_FNS: Dict[str, Callable[[Function], bool]] = {
    "constprop":        const_propagate_function,
    "constfold":        const_fold_function,
    "drop_unreachable": drop_unreachable,
    "dse":              dead_store_elim,          # dead store elimination
    "copyprop":         copy_propagate_function,
    "algebra":          algebra_simplify_function,
}

def run_passes(fn: Function, names: List[str], trace: bool=False, dumper=None):
    """Run passes by name, in order. If trace=True and dumper provided, print after each."""
    for name in names:
        fn_changed = PASS_FNS[name](fn)
        if trace and dumper is not None:
            print(f"\n;; after {name} (changed={fn_changed})")
            print(dumper(fn))

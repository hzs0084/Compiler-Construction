from ir.ir_types import Function
from ir.const_prop import const_propagate_function
from ir.const_fold import const_fold_function
from ir.dce import drop_unreachable, dead_store_elim
from typing import Optional

def optimize_function(fn: Function, opt_level: int = 0) -> None:
    if opt_level <= 0:
        return

    changed = True
    while changed:
        changed = False

        # O1 base
        if const_propagate_function(fn): changed = True
        if const_fold_function(fn):      changed = True
        if drop_unreachable(fn):         changed = True
        if dead_store_elim(fn):          changed = True

        # O2: copy propagation + cleanup
        if opt_level >= 2:
            from ir.copy_prop import copy_propagate_function
            if copy_propagate_function(fn): changed = True
            if const_fold_function(fn):      changed = True
            if dead_store_elim(fn):          changed = True

        # # O3: algebraic simplification + cleanup
        # if opt_level >= 3:
        #     from ir.algebra import algebra_simplify_function
        #     if algebra_simplify_function(fn): changed = True
        #     if const_fold_function(fn):        changed = True
        #     if dead_store_elim(fn):            changed = True

# ir/pipeline.py (excerpt)
from ir.const_prop import const_propagate_function
from ir.const_fold import const_fold_function
from ir.dce import drop_unreachable, dead_store_elim
from ir.fuse import fuse_straightline
from ir.copy_prop import copy_propagate_function
from ir.algebra import algebra_simplify_function


def optimize_function(fn, opt_level: int = 0):
    MAX_OUTER = 8
    for _ in range(MAX_OUTER):
        changed = False

        # O1 core
        if const_propagate_function(fn): changed = True
        if const_fold_function(fn):      changed = True
        if drop_unreachable(fn):         changed = True
        if fuse_straightline(fn):        changed = True   # <--- add here
        if dead_store_elim(fn):          changed = True

        # O2 extras
        if opt_level >= 2:

            if copy_propagate_function(fn): changed = True
            if const_fold_function(fn):      changed = True
            if dead_store_elim(fn):          changed = True
            if fuse_straightline(fn):        changed = True  # cleanup

        # O3 extras
        if opt_level >= 3:
                
            if algebra_simplify_function(fn): changed = True
            if const_fold_function(fn):      changed = True
            if dead_store_elim(fn):          changed = True
            if fuse_straightline(fn):        changed = True  # cleanup

        if not changed:
            break

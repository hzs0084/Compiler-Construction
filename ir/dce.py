from collections import deque
from typing import Set, Dict
from ir.ir_types import *

def drop_unreachable(fn: Function) -> bool:
    if not fn.blocks: return False
    start = fn.blocks[0].label
    seen:set[str]=set()
    q=deque([start])
    while q:
        u=q.popleft()
        if u in seen: continue
        seen.add(u)
        for v in fn.succ.get(u,[]): 
            if v: q.append(v)
    before=len(fn.blocks)
    fn.blocks=[b for b in fn.blocks if b.label in seen]
    from ir.builder import build_cfg
    build_cfg(fn)
    return len(fn.blocks)!=before

# Returns the set of variable names read by this instruction (no Consts, no dst).

def _uses(ins: Instr) -> Set[str]:
    s:set[str]=set()
    def add(v):
        if isinstance(v,Var): s.add(v.name)
    if ins.kind in {"mov","unop","ret"}: add(ins.a)
    elif ins.kind=="binop": add(ins.a); add(ins.b)
    elif ins.kind=="br": add(ins.a)
    return s

# Returns the destination variable name defined by this instruction, or None.

def _def(ins: Instr) -> str|None:
    return ins.dst.name if ins.dst else None


"""
PRE:  fn has a valid CFG. Instructions may define dst or be pure uses for example - (mov/binop/unop/br/ret).
POST: Backward liveness per block (with successor live-outs) and removes pure instructions
       whose destination is not live-out. Returns True iff any instruction was deleted.
NOTE: Relies on Instr.has_side_effect() to keep it accurate when adding calls/stores.
"""

def dead_store_elim(fn: Function) -> bool:
    changed=False
    # simple per-block backward sweep using succ live-out (one pass is fine for now)
    live_out:Dict[str,set[str]]={b.label:set() for b in fn.blocks}
    # a couple of iterations is enough here to keep it simple
    for _ in range(3):
        for b in reversed(fn.blocks):
            out=set()
            for s in fn.succ.get(b.label,[]): out|=live_out.get(s,set())
            live=set(out)
            for ins in reversed(b.instrs):
                d=_def(ins)
                if d and d in live: live.remove(d)
                for u in _uses(ins): live.add(u)
            live_out[b.label]=live

    for b in fn.blocks:
        out=set()
        for s in fn.succ.get(b.label,[]): out|=live_out.get(s,set())
        live=set(out)
        new=[]
        for ins in reversed(b.instrs):
            if ins.kind in {"mov","binop","unop"} and not ins.has_side_effect():
                d=_def(ins)
                if d and (d not in live):
                    changed=True
                    continue
            d=_def(ins)
            if d and d in live: live.remove(d)
            for u in _uses(ins): live.add(u)
            new.append(ins)
        new.reverse()
        b.instrs=new
    return changed

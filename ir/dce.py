from collections import deque
from typing import Set, Dict
from ir.ir_types import *
from ir.builder import build_cfg


def drop_unreachable(fn: Function) -> bool:

    """
    PRE:  fn has blocks and a valid CFG with a single entry block (with the label '_entry').
    POST: Removes blocks not reachable from entry via succ edges and rebuilds CFG.
        Returns True if any block was deleted.
    NOTE: Run after const-fold so `br Const` -> `jmp` exposes unreachable arms.
    """

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

    build_cfg(fn)
    return len(fn.blocks)!=before

# Returns the set of variable names read by this instruction (no Consts, no dst).

def _uses(ins) -> set[str]:
    s = set()
    if ins.kind == "mov":
        if isinstance(ins.a, Var): s.add(ins.a.name)
    elif ins.kind == "binop":
        if isinstance(ins.a, Var): s.add(ins.a.name)
        if isinstance(ins.b, Var): s.add(ins.b.name)
    elif ins.kind == "unop":
        if isinstance(ins.a, Var): s.add(ins.a.name)
    elif ins.kind == "br":
        if isinstance(ins.a, Var): s.add(ins.a.name)
    elif ins.kind == "ret":
        if ins.a is not None and isinstance(ins.a, Var): s.add(ins.a.name)
    return s

# Returns the destination variable name defined by this instruction, or None.

def _def(ins) -> str | None:
    if ins.kind in ("mov", "binop", "unop") and ins.dst is not None:
        return ins.dst.name
    return None

def dead_store_elim(fn) -> bool:
    # ---- Phase A: dataflow to compute live_in/live_out ----
    blocks = fn.blocks
    succ = fn.succ  # dict: label -> [succ labels]
    live_in: dict[str, set[str]]  = {b.label: set() for b in blocks}
    live_out: dict[str, set[str]] = {b.label: set() for b in blocks}

    # Precompute per-block USE and DEF sets (classic formulation)
    USE: dict[str, set[str]] = {}
    DEF: dict[str, set[str]] = {}
    for b in blocks:
        u, d = set(), set()
        for ins in b.instrs:
            # any use of a var not yet defined in this block contributes to USE
            for v in _uses(ins):
                if v not in d:
                    u.add(v)
            # defs go to DEF
            dv = _def(ins)
            if dv is not None:
                d.add(dv)
        USE[b.label] = u
        DEF[b.label] = d

    changed = True
    iters = 0
    MAX_ITERS = 16
    while changed and iters < MAX_ITERS:
        changed = False
        iters += 1
        for b in blocks:
            old_in  = live_in[b.label]
            old_out = live_out[b.label]

            # out[b] = ⋃ in[s] for all successors s
            new_out = set()
            for s in succ.get(b.label, []):
                new_out |= live_in.get(s, set())

            # in[b] = USE[b] ∪ (out[b] - DEF[b])
            new_in = USE[b.label] | (new_out - DEF[b.label])

            if new_out != old_out:
                live_out[b.label] = new_out
                changed = True
            if new_in != old_in:
                live_in[b.label] = new_in
                changed = True

    # ---- Phase B: per-block backward sweep using live_out as seed ----
    any_removed = False
    for b in blocks:
        live = set(live_out[b.label])   # seed from successors
        new_instrs: list[Instr] = []
        for ins in reversed(b.instrs):
            # add uses first
            live |= _uses(ins)
            dv = _def(ins)
            # drop pure defs that are dead at this point
            if dv is not None and (not ins.has_side_effect()) and (dv not in live):
                any_removed = True
                # do not append (i.e., delete)
            else:
                new_instrs.append(ins)
                # def kills the name (it becomes newly defined)
                if dv is not None and dv in live:
                    live.remove(dv)
        new_instrs.reverse()
        b.instrs = new_instrs

    return any_removed
# ir/fuse.py
from typing import Dict, Set
from ir.ir_types import Function, Instr
from ir.builder import build_cfg

def _recompute_preds(fn: Function) -> Dict[str, Set[str]]:
    preds: Dict[str, Set[str]] = {b.label: set() for b in fn.blocks}
    for b in fn.blocks:
        for s in fn.succ.get(b.label, []):
            preds.setdefault(s, set()).add(b.label)
    return preds

def fuse_straightline(fn: Function) -> bool:
    """
    PRE:  fn has valid blocks/CFG (one terminator per block).
    POST: Repeatedly fuse B -> S when B ends with `jmp S` and S has exactly one
          predecessor (B). Returns True iff any fusion happened.
    NOTE: Rebuilds CFG after structural changes.
    """
    changed = False
    # Make sure succ/pred are up-to-date
    build_cfg(fn)
    preds = _recompute_preds(fn)

    while True:
        fused_any = False
        label_to_block = {b.label: b for b in fn.blocks}
        i = 0
        while i < len(fn.blocks):
            b = fn.blocks[i]
            if not b.instrs:
                i += 1
                continue

            term = b.instrs[-1]
            if term.kind == "jmp":
                target = term.tlabel
                sblk = label_to_block.get(target)
                # only fuse if the successor exists and has a single predecessor (B)
                if sblk is not None and preds.get(target, set()) == {b.label}:
                    # 1) remove the jmp in B
                    b.instrs.pop()
                    # 2) splice S's body into B (skip S's leading "label" if present)
                    for ins in sblk.instrs:
                        if ins.kind == "label":
                            continue
                        b.instrs.append(ins)
                    # 3) delete S from function
                    fn.blocks.remove(sblk)
                    # 4) rebuild CFG and preds after topology change
                    build_cfg(fn)
                    preds = _recompute_preds(fn)
                    # 5) refresh maps and keep scanning from same index
                    label_to_block = {blk.label: blk for blk in fn.blocks}
                    fused_any = True
                    changed = True
                    continue  # re-check current i (block B grew)
            i += 1

        if not fused_any:
            break

    if changed:
        build_cfg(fn)
    return changed

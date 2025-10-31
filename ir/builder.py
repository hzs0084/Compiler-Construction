from typing import List, Dict
from ir.ir_types import *
from ir.tac_adapter import FALLTHRU

def linear_to_blocks(func_name: str, linear: List[Instr]) -> Function:
    blocks: List[Block] = []
    label_to_block: Dict[str, Block] = {}

    # Start with a synthetic entry if first isn’t a label
    cur = None
    def start_block(lbl: str):
        nonlocal cur
        cur = Block(label=lbl)
        blocks.append(cur)
        label_to_block[lbl] = cur

    if not linear or linear[0].kind != "label":
        start_block("_entry")

    for ins in linear:
        if ins.kind == "label":
            # close previous block with fallthrough jmp if needed
            if cur and cur.instrs and cur.instrs[-1].kind not in {"br","jmp","ret"}:
                # fallthrough to this label
                cur.instrs.append(Instr(kind="jmp", tlabel=ins.label))
            start_block(ins.label)
            continue
        if cur is None:
            start_block("_entry")
        cur.instrs.append(ins)
        if ins.kind in {"br","jmp","ret"}:
            cur = None  # next instruction starts a new block unless it's a label

    fn = Function(name=func_name, blocks=blocks)
    # resolve FALLTHRU in br to the next block label in order
    for i, b in enumerate(fn.blocks):
        if not b.instrs: continue
        term = b.instrs[-1]
        if term.kind == "br" and term.tlabel == FALLTHRU:
            # next block if exists else no fallthrough
            nxt = fn.blocks[i+1].label if i+1 < len(fn.blocks) else None
            term.tlabel = nxt

    build_cfg(fn)
    return fn

def build_cfg(fn: Function) -> None:
    succ: Dict[str, List[str]] = {}
    pred: Dict[str, List[str]] = {}
    for b in fn.blocks:
        outs: List[str] = []
        if b.instrs:
            term = b.instrs[-1]
            if term.kind == "br":
                if term.tlabel: outs.append(term.tlabel)
                if term.flabel: outs.append(term.flabel)
            elif term.kind == "jmp":
                if term.tlabel: outs.append(term.tlabel)
            elif term.kind == "ret":
                pass
        succ[b.label] = outs
    for u, outs in succ.items():
        for v in outs:
            pred.setdefault(v, []).append(u)
    fn.succ, fn.pred = succ, pred

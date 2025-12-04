from typing import List, Dict
from ir.ir_types import Block, Instr, Function
from ir.tac_adapter import FALLTHRU


def linear_to_blocks(func_name: str, linear: List[Instr]) -> Function:

    """
    PRE:  linear is a list of IR Instr (may include 'label'). No block structure yet.
    POST: Returns a Function with basic blocks built and terminators enforced:
          - Every block ends in br/jmp/ret
          - Implicit fallthroughs are replaced with explicit jmp
          - FALLTHRU in br is resolved to the next block label
          - CFG (succ/pred) is computed; succ is successor and pred is predecessor
    NOTE: A synthetic '_entry' block is created if the first item is not a label.

    """

    blocks: List[Block] = []
    label_to_block: Dict[str, Block] = {}
    bb_idx = 0

    def new_anon_label():
        nonlocal bb_idx
        lab = f"_Basic-Block{bb_idx}"
        bb_idx += 1
        return lab

    # Start with a synthetic entry if first isn’t a label
    cur: Block | None = None

    
    # Entry Block

    cur = Block(label="_entry")
    blocks.append(cur)
    label_to_block[cur.label] = cur

    for ins in linear:
        if ins.kind == "label":
            # close previous block with fallthrough jmp if unterminated
            if cur and cur.instrs and cur.instrs[-1].kind not in {"br","jmp","ret"}:
                # fallthrough to this label
                cur.instrs.append(Instr(kind="jmp", tlabel=ins.label))
            cur = Block(label=ins.label)
            blocks.append(cur)
            label_to_block[cur.label] = cur
            continue

        # start a fresh anon block if needed
        if cur is None:
            cur = Block(label=new_anon_label())
            blocks.append(cur)
            label_to_block[cur.label] = cur

        cur.instrs.append(ins)

        if ins.kind in {"br","jmp","ret"}:
            cur = None  # next instruction starts a new block unless it's a label

    # Resolve FALLTHRU to the physical next block label to remove implicit fallthrough.

    for i, b in enumerate(blocks):
        if not b.instrs: 
            continue
        term = b.instrs[-1]
        if term.kind == "br" and term.tlabel == FALLTHRU:
            # next block if exists else no fallthrough
            nxt = blocks[i+1].label if i+1 < len(blocks) else None
            b.instrs[-1] = Instr(kind="br", a = term.a, tlabel = nxt, flabel = term.flabel)

    fn = Function(name=func_name, blocks=blocks)

    build_cfg(fn)
    return fn



def build_cfg(fn: Function) -> None:

    """
    PRE:  fn.blocks is a list of blocks where the last instruction of each block is a terminator (br/jmp/ret).
    POST: Populates fn.succ and fn.pred maps from terminators.
    NOTE: Keep block terminator invariant intact or CFG becomes incorrect.
    """
    
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

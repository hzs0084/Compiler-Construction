# codegen/ra.py
from collections import defaultdict
from typing import Dict, List, Set, Tuple
from .x86ir import *

CALLER_SAVED = ["rax","rcx","rdx","rsi","rdi","r8","r9","r10","r11"]
SPILL_SCRATCH = "r10"   # keep one scratch for spill reload/store
# NOTE: we’ll avoid using rax/rdx unless needed (helps idiv freedom)

def is_vreg(r: Reg) -> bool:
    return r.name.startswith("R")  # includes R1.. and RAX/RDX as virtuals

def reads_writes(ins: Instr) -> Tuple[Set[str], Set[str]]:
    R: Set[str] = set()
    W: Set[str] = set()
    def add_read(o: Operand):
        if isinstance(o, Reg) and is_vreg(o): R.add(o.name)
    def add_write(o: Operand):
        if isinstance(o, Reg) and is_vreg(o): W.add(o.name)

    if isinstance(ins, Mov):
        add_read(ins.src); add_write(ins.dst)
    elif isinstance(ins, Add) or isinstance(ins, Sub) or isinstance(ins, IMul):
        add_read(ins.dst); add_read(ins.src); add_write(ins.dst)
    elif isinstance(ins, Cmp):
        add_read(ins.a); add_read(ins.b)
    elif isinstance(ins, Idiv):
        # idiv reads RAX,RDX,src ; writes RAX,RDX
        R.update({"RAX","RDX"}); add_read(ins.src)
        W.update({"RAX","RDX"})
    elif isinstance(ins, Jcc) or isinstance(ins, Jmp) or isinstance(ins, LabelDef):
        pass
    elif isinstance(ins, Ret):
        if ins.val: add_read(ins.val)
    else:
        pass
    return (R, W)

def successors(p: Program) -> Dict[int, List[int]]:
    # map label -> index
    labels: Dict[str,int] = {}
    for i, ins in enumerate(p):
        if isinstance(ins, LabelDef):
            labels[ins.label.name] = i

    succ = defaultdict(list)
    for i, ins in enumerate(p):
        nxt = i+1 if i+1 < len(p) else None
        if isinstance(ins, (Mov,Add,Sub,IMul,Cmp,Idiv,LabelDef, Push, Pop)):
            if nxt is not None: succ[i].append(nxt)
        elif isinstance(ins, Ret):
            pass
        elif isinstance(ins, Jmp):
            succ[i].append(labels[ins.target.name])
        elif isinstance(ins, Jcc):
            if nxt is not None: succ[i].append(nxt)  # fall-through
            succ[i].append(labels[ins.target.name])
    return succ

def liveness(p: Program):
    succ = successors(p)
    R = []; W = []
    for ins in p:
        r,w = reads_writes(ins)
        R.append(r); W.append(w)
    IN = [set() for _ in p]; OUT = [set() for _ in p]
    changed = True
    while changed:
        changed = False
        for i in reversed(range(len(p))):
            in_old, out_old = IN[i].copy(), OUT[i].copy()
            OUT[i].clear()
            for j in succ[i]:
                OUT[i] |= IN[j]
            IN[i] = R[i] | (OUT[i] - W[i])
            changed |= (IN[i] != in_old) or (OUT[i] != out_old)
    return IN, OUT, R, W

def build_igraph(p: Program, IN, OUT, R, W):
    G = defaultdict(set)

    def edge(a: str, b: str):
        if a == b: return
        G[a].add(b); G[b].add(a)

    def touch(v: str):
        # make sure isolated nodes exist
        _ = G[v]

    # helper to record any vreg name appearing in operands
    def collect_vregs(op) -> list[str]:
        from .x86ir import Reg
        out = []
        if isinstance(op, Reg) and is_vreg(op):
            out.append(op.name)
        return out

    for i, ins in enumerate(p):
        # Touch anything read or written so isolated nodes exist
        for v in R[i] | W[i]:
            touch(v)

        # writes vs live-out = classic interference
        for x in W[i]:
            for y in OUT[i]:
                if y != x:
                    edge(x, y)

        # idiv constraints: RAX/RDX must be exclusive when idiv occurs
        if isinstance(ins, Idiv):
            # Dividend in RAX / remainder in RDX interfere with all live at that point
            live = IN[i] | OUT[i]
            for fx in ("RAX", "RDX"):
                touch(fx)
                for y in live:
                    if y != fx:
                        edge(fx, y)
            edge("RAX", "RDX")
    return G

def greedy_color(G, precolored: Dict[str,str] | None = None, k_regs: List[str] | None = None):
    if precolored is None: precolored = {}
    # reserve a scratch
    pool = [r for r in (k_regs or CALLER_SAVED) if r != SPILL_SCRATCH]
    nodes = set(G.keys()) | set(precolored.keys())

    def degree(v): return len(G[v])

    stack: List[str] = []
    spills: Set[str] = set()
    work = set(nodes)
    while work:
        pick = None
        for v in work:
            if v in precolored: continue
            if degree(v) < len(pool):
                pick = v; break
        if pick is None:
            # spill: highest degree non-precolored
            cand = [v for v in work if v not in precolored]
            pick = max(cand, key=degree) if cand else None
            if pick: spills.add(pick)
        if pick is None: break
        stack.append(pick); work.remove(pick)

    colors = dict(precolored)
    while stack:
        v = stack.pop()
        used = {colors[n] for n in G[v] if n in colors}
        # try to avoid rax/rdx unless needed
        try_first = [r for r in pool if r not in ("rax","rdx")]
        try_then  = [r for r in pool if r in ("rax","rdx")]
        color = next((r for r in try_first + try_then if r not in used), None)
        if color is None:
            spills.add(v)
        else:
            colors[v] = color
    return colors, spills

def rewrite_with_spills(p: Program, colors: Dict[str,str], spills: Set[str]) -> Program:
    out: Program = []

    def phys(o: Operand) -> Operand:
        if isinstance(o, Reg) and is_vreg(o) and o.name in colors:
            return Reg(colors[o.name])
        return o

    def spill_mem(vname: str) -> Mem:
        return Mem(f"spill_{vname}")

    for ins in p:
        if isinstance(ins, LabelDef):
            out.append(ins); continue

        if isinstance(ins, Ret):
            if isinstance(ins.val, Reg) and is_vreg(ins.val) and ins.val.name in spills:
                out.append(Mov(Reg(SPILL_SCRATCH), spill_mem(ins.val.name)))
                out.append(Ret(Reg(SPILL_SCRATCH)))
            else:
                out.append(Ret(phys(ins.val) if ins.val else None))
            continue

        if isinstance(ins, Idiv):
            src = ins.src
            if is_vreg(src) and src.name in spills:
                out.append(Mov(Reg(SPILL_SCRATCH), spill_mem(src.name)))
                out.append(Idiv(Reg(SPILL_SCRATCH)))
            else:
                out.append(Idiv(phys(src)))
            continue

        if isinstance(ins, Cmp):
            a, b = ins.a, ins.b
            ap = a; bp = b
            if isinstance(a, Reg) and is_vreg(a) and a.name in spills:
                out.append(Mov(Reg(SPILL_SCRATCH), spill_mem(a.name)))
                ap = Reg(SPILL_SCRATCH)
            else:
                ap = phys(a)
            if isinstance(b, Reg) and is_vreg(b) and b.name in spills:
                bp = spill_mem(b.name)
            else:
                bp = phys(b)
            out.append(Cmp(ap, bp))
            continue

        if isinstance(ins, Mov):
            dst, src = ins.dst, ins.src
            if isinstance(dst, Reg) and is_vreg(dst) and dst.name in spills:
                # mov [spill_dst], src'
                if isinstance(src, Reg) and is_vreg(src) and src.name in spills:
                    out.append(Mov(Reg(SPILL_SCRATCH), spill_mem(src.name)))
                    out.append(Mov(spill_mem(dst.name), Reg(SPILL_SCRATCH)))
                else:
                    out.append(Mov(spill_mem(dst.name), phys(src)))
            else:
                pdst = phys(dst)
                if isinstance(src, Reg) and is_vreg(src) and src.name in spills:
                    out.append(Mov(Reg(SPILL_SCRATCH), spill_mem(src.name)))
                    out.append(Mov(pdst, Reg(SPILL_SCRATCH)))
                else:
                    out.append(Mov(pdst, phys(src)))
            continue

        if isinstance(ins, (Add,Sub,IMul)):
            dst, src = ins.dst, ins.src
            if isinstance(dst, Reg) and is_vreg(dst) and dst.name in spills:
                # load, op, store back
                out.append(Mov(Reg(SPILL_SCRATCH), spill_mem(dst.name)))
                s_op: Operand
                if isinstance(src, Reg) and is_vreg(src) and src.name in spills:
                    s_op = spill_mem(src.name)
                else:
                    s_op = phys(src)
                if isinstance(ins, Add):
                    out.append(Add(Reg(SPILL_SCRATCH), s_op))
                elif isinstance(ins, Sub):
                    out.append(Sub(Reg(SPILL_SCRATCH), s_op))
                else:
                    out.append(IMul(Reg(SPILL_SCRATCH), s_op))
                out.append(Mov(spill_mem(dst.name), Reg(SPILL_SCRATCH)))
            else:
                pdst = phys(dst)
                s_op = phys(src) if not (isinstance(src, Reg) and is_vreg(src) and src.name in spills) else spill_mem(src.name)
                if isinstance(ins, Add):
                    out.append(Add(pdst, s_op))
                elif isinstance(ins, Sub):
                    out.append(Sub(pdst, s_op))
                else:
                    out.append(IMul(pdst, s_op))
            continue

        if isinstance(ins, (Jcc, Jmp, Push, Pop)):
            out.append(ins); continue

        raise NotImplementedError(type(ins))

    return out

def allocate_registers_on_program(p: Program) -> Program:
    # 1) liveness
    IN, OUT, R, W = liveness(p)
    # 2) IG
    G = build_igraph(p, IN, OUT, R, W)

    pre = {"RAX": "rax", "RDX": "rdx"}

    # 3) precoloring: none by default (we constrained idiv via edges)
    colors, spills = greedy_color(G, precolored=pre)
    # 4) rewrite
    p2 = rewrite_with_spills(p, colors, spills)
    return p2

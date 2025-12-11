# codegen/ra.py
"""
Refs: 
https://github.com/johnflanigan/graph-coloring-via-register-allocation
https://www.reddit.com/r/Compilers/comments/1hhsaw5/how_to_calculate_live_ranges_and_interference/
https://en.wikipedia.org/wiki/Register_allocation
https://stackoverflow.com/questions/1960888/register-allocation-and-spilling-the-easy-way

"""

from collections import defaultdict
from typing import Dict, List, Set, Tuple

from .x86ir import (
    Reg,
    Instr,
    Operand,
    Mov,
    Sub,
    Cmp,
    Add,
    Idiv,
    Mem,
    IMul,
    Jcc,
    Jmp,
    Program,
    LabelDef,
    Ret,
    Push,
    Pop,
)

CALLER_SAVED = ["rax", "rcx", "rdx", "rsi", "rdi", "r8", "r9", "r10", "r11"]
SPILL_SCRATCH = "r10"   # keep one scratch for spill reload/store


def is_vreg(r: Reg) -> bool:
    """Return True if this register is a virtual register (read*, RAX, RDX)."""
    return r.name.startswith("read")


# small top-level helpers

def _add_vreg_read(op: Operand, reads: Set[str]) -> None:
    """If operand is a virtual register, add its name to reads."""
    if isinstance(op, Reg) and is_vreg(op):
        reads.add(op.name)


def _add_vreg_write(op: Operand, writes: Set[str]) -> None:
    """If operand is a virtual register, add its name to writes."""
    if isinstance(op, Reg) and is_vreg(op):
        writes.add(op.name)


def _igraph_edge(G: Dict[str, Set[str]], a: str, b: str) -> None:
    """Add an undirected edge between a and b in the interference graph."""
    if a == b:
        return
    G[a].add(b)
    G[b].add(a)


def _igraph_touch(G: Dict[str, Set[str]], v: str) -> None:
    """Ensure node v exists in the interference graph."""
    _ = G[v]


def _phys(op: Operand, colors: Dict[str, str]) -> Operand:
    """
    Map virtual Reg operands to their physical registers according to colors.
    Non-virtual or uncolored operands are returned unchanged.
    """
    if isinstance(op, Reg) and is_vreg(op) and op.name in colors:
        return Reg(colors[op.name])
    return op


def _spill_mem(vname: str) -> Mem:
    """Return the synthetic memory location for a spilled virtual register."""
    return Mem(f"spill_{vname}")


def _degree(G: Dict[str, Set[str]], v: str) -> int:
    """Degree of node v in the interference graph."""
    return len(G[v])


# main analysis passes

def reads_writes(ins: Instr) -> Tuple[Set[str], Set[str]]:
    """
    Compute (reads, writes) sets of virtual register names for an instruction.
    """
    read: Set[str] = set()
    write: Set[str] = set()

    if isinstance(ins, Mov):
        _add_vreg_read(ins.src, read)
        _add_vreg_write(ins.dst, write)
    elif isinstance(ins, (Add, Sub, IMul)):
        # two-operand form: dst := dst op src
        _add_vreg_read(ins.dst, read)
        _add_vreg_read(ins.src, read)
        _add_vreg_write(ins.dst, write)
    elif isinstance(ins, Cmp):
        _add_vreg_read(ins.a, read)
        _add_vreg_read(ins.b, read)
    elif isinstance(ins, Idiv):
        # idiv reads RAX,RDX,src ; writes RAX,RDX
        read.update({"RAX", "RDX"})
        _add_vreg_read(ins.src, read)
        write.update({"RAX", "RDX"})
    elif isinstance(ins, (Jcc, Jmp, LabelDef)):
        pass
    elif isinstance(ins, Ret):
        if ins.val is not None:
            _add_vreg_read(ins.val, read)
    else:
        # Push/Pop are assumed to use only physical registers in this setup
        pass

    return read, write


def successors(p: Program) -> Dict[int, List[int]]:
    """
    Build control-flow successors over instruction indices.
    """
    labels: Dict[str, int] = {}
    for i, ins in enumerate(p):
        if isinstance(ins, LabelDef):
            labels[ins.label.name] = i

    succ: Dict[int, List[int]] = defaultdict(list)
    for i, ins in enumerate(p):
        nxt = i + 1 if i + 1 < len(p) else None
        if isinstance(ins, (Mov, Add, Sub, IMul, Cmp, Idiv, LabelDef, Push, Pop)):
            if nxt is not None:
                succ[i].append(nxt)
        elif isinstance(ins, Ret):
            # return has no successors
            pass
        elif isinstance(ins, Jmp):
            succ[i].append(labels[ins.target.name])
        elif isinstance(ins, Jcc):
            if nxt is not None:
                succ[i].append(nxt)                     # fall-through
            succ[i].append(labels[ins.target.name])     # branch
    return succ


def liveness(p: Program):
    """
    Standard backward liveness analysis.
    Returns IN, OUT, read, write lists indexed by instruction.
    """
    succ = successors(p)
    read_list: List[Set[str]] = []
    write_list: List[Set[str]] = []
    for ins in p:
        r, w = reads_writes(ins)
        read_list.append(r)
        write_list.append(w)

    IN: List[Set[str]] = [set() for _ in p]
    OUT: List[Set[str]] = [set() for _ in p]

    changed = True
    while changed:
        changed = False
        for i in reversed(range(len(p))):
            in_old, out_old = IN[i].copy(), OUT[i].copy()

            # OUT[i] = union of IN[s] for successors s
            OUT[i].clear()
            for j in succ[i]:
                OUT[i] |= IN[j]

            # IN[i] = read[i] ∪ (OUT[i] − write[i])
            IN[i] = read_list[i] | (OUT[i] - write_list[i])

            if IN[i] != in_old or OUT[i] != out_old:
                changed = True

    return IN, OUT, read_list, write_list


def build_igraph(p: Program, IN, OUT, read_list, write_list):
    """
    Construct the interference graph from liveness and reads/writes.
    Nodes are virtual register names and edges mean "these cannot share a color, so can't share register".
    """
    G: Dict[str, Set[str]] = defaultdict(set)

    for i, ins in enumerate(p):
        # Ensure nodes exist for anything read or written
        for v in read_list[i] | write_list[i]:
            _igraph_touch(G, v)

        # Classic: any register written at i interferes with everything live out of i
        for x in write_list[i]:
            for y in OUT[i]:
                if y != x:
                    _igraph_edge(G, x, y)

        # idiv needs RAX/RDX exclusively
        if isinstance(ins, Idiv):
            live = IN[i] | OUT[i]
            for fx in ("RAX", "RDX"):
                _igraph_touch(G, fx)
                for y in live:
                    if y != fx:
                        _igraph_edge(G, fx, y)
            _igraph_edge(G, "RAX", "RDX")

    return G


# coloring & spilling

def greedy_color(
    G: Dict[str, Set[str]],
    precolored: Dict[str, str] | None = None,
    k_regs: List[str] | None = None,
):
    """
    Simplified graph-coloring allocator.
    Returns (colors, spills):
      colors: vreg_name -> physical reg name
      spills: set of vreg_names that must be spilled
    """
    if precolored is None:
        precolored = {}

    pool = [r for r in (k_regs or CALLER_SAVED) if r != SPILL_SCRATCH]
    nodes = set(G.keys()) | set(precolored.keys())

    stack: List[str] = []
    spills: Set[str] = set()
    work: Set[str] = set(nodes)

    # Simplify phase
    while work:
        pick = None

        # Prefer removing low-degree nodes
        for v in work:
            if v in precolored:
                continue
            if _degree(G, v) < len(pool):
                pick = v
                break

        if pick is None:
            # Spill candidate: highest-degree non-precolored
            cand = [v for v in work if v not in precolored]
            pick = max(cand, key=lambda x: _degree(G, x)) if cand else None
            if pick:
                spills.add(pick)

        if pick is None:
            break

        stack.append(pick)
        work.remove(pick)

    # Select phase
    colors = dict(precolored)
    while stack:
        v = stack.pop()
        used = {colors[n] for n in G[v] if n in colors}

        # Avoid rax/rdx if possible (leave flexibility for idiv)
        try_first = [r for r in pool if r not in ("rax", "rdx")]
        try_then = [r for r in pool if r in ("rax", "rdx")]
        color = next((r for r in try_first + try_then if r not in used), None)

        if color is None:
            spills.add(v)
        else:
            colors[v] = color

    return colors, spills


# program rewrite with spills

def rewrite_with_spills(
    p: Program,
    colors: Dict[str, str],
    spills: Set[str],
) -> Program:
    """
    Rewrite program p so that:
      - Colored virtual regs are replaced with their physical registers.
      - Spilled virtual regs are accessed via Mem("spill_<name>") using SPILL_SCRATCH.
    """
    out: Program = []

    for ins in p:
        # Labels pass through unchanged
        if isinstance(ins, LabelDef):
            out.append(ins)
            continue

        # Return
        if isinstance(ins, Ret):
            if isinstance(ins.val, Reg) and is_vreg(ins.val) and ins.val.name in spills:
                out.append(Mov(Reg(SPILL_SCRATCH), _spill_mem(ins.val.name)))
                out.append(Ret(Reg(SPILL_SCRATCH)))
            else:
                out.append(Ret(_phys(ins.val, colors) if ins.val else None))
            continue

        # Idiv: special x86 calling convention
        if isinstance(ins, Idiv):
            src = ins.src
            if isinstance(src, Reg) and is_vreg(src) and src.name in spills:
                out.append(Mov(Reg(SPILL_SCRATCH), _spill_mem(src.name)))
                out.append(Idiv(Reg(SPILL_SCRATCH)))
            else:
                out.append(Idiv(_phys(src, colors)))
            continue

        # Cmp: support spills on a/b
        if isinstance(ins, Cmp):
            a, b = ins.a, ins.b

            # Left operand
            if isinstance(a, Reg) and is_vreg(a) and a.name in spills:
                out.append(Mov(Reg(SPILL_SCRATCH), _spill_mem(a.name)))
                ap = Reg(SPILL_SCRATCH)
            else:
                ap = _phys(a, colors)

            # Right operand
            if isinstance(b, Reg) and is_vreg(b) and b.name in spills:
                bp = _spill_mem(b.name)
            else:
                bp = _phys(b, colors)

            out.append(Cmp(ap, bp))
            continue

        # Mov
        if isinstance(ins, Mov):
            dst, src = ins.dst, ins.src

            # Destination spilled
            if isinstance(dst, Reg) and is_vreg(dst) and dst.name in spills:
                if isinstance(src, Reg) and is_vreg(src) and src.name in spills:
                    # both spilled: load src, store to dst
                    out.append(Mov(Reg(SPILL_SCRATCH), _spill_mem(src.name)))
                    out.append(Mov(_spill_mem(dst.name), Reg(SPILL_SCRATCH)))
                else:
                    out.append(Mov(_spill_mem(dst.name), _phys(src, colors)))
            else:
                pdst = _phys(dst, colors)
                if isinstance(src, Reg) and is_vreg(src) and src.name in spills:
                    out.append(Mov(Reg(SPILL_SCRATCH), _spill_mem(src.name)))
                    out.append(Mov(pdst, Reg(SPILL_SCRATCH)))
                else:
                    out.append(Mov(pdst, _phys(src, colors)))
            continue

        # Add/Sub/IMul
        if isinstance(ins, (Add, Sub, IMul)):
            dst, src = ins.dst, ins.src

            # Spilled destination: load, op, store back
            if isinstance(dst, Reg) and is_vreg(dst) and dst.name in spills:
                out.append(Mov(Reg(SPILL_SCRATCH), _spill_mem(dst.name)))

                if isinstance(src, Reg) and is_vreg(src) and src.name in spills:
                    s_op: Operand = _spill_mem(src.name)
                else:
                    s_op = _phys(src, colors)

                if isinstance(ins, Add):
                    out.append(Add(Reg(SPILL_SCRATCH), s_op))
                elif isinstance(ins, Sub):
                    out.append(Sub(Reg(SPILL_SCRATCH), s_op))
                else:  # IMul
                    out.append(IMul(Reg(SPILL_SCRATCH), s_op))

                out.append(Mov(_spill_mem(dst.name), Reg(SPILL_SCRATCH)))
            else:
                pdst = _phys(dst, colors)
                if isinstance(src, Reg) and is_vreg(src) and src.name in spills:
                    s_op = _spill_mem(src.name)
                else:
                    s_op = _phys(src, colors)

                if isinstance(ins, Add):
                    out.append(Add(pdst, s_op))
                elif isinstance(ins, Sub):
                    out.append(Sub(pdst, s_op))
                else:  # IMul
                    out.append(IMul(pdst, s_op))
            continue

        # Control-flow and stack ops pass through unchanged (no vregs expected)
        if isinstance(ins, (Jcc, Jmp, Push, Pop)):
            out.append(ins)
            continue

        raise NotImplementedError(f"rewrite_with_spills missing case for {type(ins)}")

    return out


# top-level entry

def allocate_registers_on_program(p: Program) -> Program:
    """
    Run liveness, build an interference graph, color it, and rewrite p so that
    all virtual registers are either mapped to physical registers or spilled.
    """
    # 1) liveness
    IN, OUT, read_list, write_list = liveness(p)

    # 2) interference graph
    G = build_igraph(p, IN, OUT, read_list, write_list)

    # 3) precoloring for idiv-related regs
    pre = {"RAX": "rax", "RDX": "rdx"}

    # 4) color graph and decide spills
    colors, spills = greedy_color(G, precolored=pre)

    # 5) rewrite with physical regs + spill slots
    return rewrite_with_spills(p, colors, spills)


"""
I am going a bit crazy here to make sure i can verbalize the thought process as to what happens here
"""

"""
High-level pipeline (tiny example)
  Pseudo-x86 input:
      L0:
        mov R1, [rbp-8]     ; a
        mov R2, [rbp-16]    ; b
        add R1, R2          ; R1 = a + b
        mov RAX, R1         ; return in RAX
        ret
  1) reads_writes  -> for each instruction i, compute:
        R[i] = set of vregs read (used)
        W[i] = set of vregs written (defined)
  2) successors    -> for each instruction i, list of successor indices (CFG).
  3) liveness      -> compute IN[i], OUT[i] for each i:
        OUT[i] = union of IN[s] for successors s
        IN[i]  = R[i] ∪ (OUT[i] − W[i])
  4) build_igraph  -> interference graph:
        node per virtual reg (e.g., "R1","R2","RAX")
        edge between x and y if they are live at the same time.
  5) greedy_color  -> assign each vreg a physical register (color),
                       or mark it as spilled if we run out of colors.
  6) rewrite_with_spills -> rewrite program so that:
        - vregs use their assigned physical registers
        - spilled vregs are loaded/stored from Mem("spill_<name>")
  7) pseudo_x86.remap_spills_to_frame -> later maps spill slots to real [rbp-offset] stack slots.
"""

"""
In v_reg

Return True if this register is a virtual register.
In my pipeline, virtual registers are named R1, R2, ..., RAX, RDX (start with "R").

Example:
    Reg("R1")  -> True
    Reg("rax") -> False
"""

"""
For a single instruction, compute which virtual registers it READS and WRITES.

Input:
    ins: one pseudo-x86 instruction (Mov/Add/Sub/IMul/Cmp/Idiv/Ret/etc)

Output:
    (R, W) where:
        R = set of vreg names read by this instruction
        W = set of vreg names written by this instruction

Tiny example (no control flow, just instruction-by-instruction):

    1: mov R1, [rbp-8]
        - reads: [rbp-8] (memory, NOT a vreg)
        - writes: R1
        => R[1] = {}, W[1] = {"R1"}

    2: add R1, R2
        - two-operand form: R1 := R1 + R2
        - reads: R1, R2
        - writes: R1
        => R[2] = {"R1","R2"}, W[2] = {"R1"}

    3: mov RAX, R1
        - reads: R1
        - writes: RAX
        => R[3] = {"R1"}, W[3] = {"RAX"}

Note:
    Memory operands like [rbp-8] are NOT vregs, so they never appear in R/W.
"""

"""
in liveness function do
Backward liveness analysis

Uses:
    - successors(p) to know CFG structure
    - reads_writes(ins) to know which vregs each instruction uses/defines

Computes:
    IN[i]  = set of vregs live *before* instruction i
    OUT[i] = set of vregs live *after* instruction i
    (plus R[i], W[i] copies from reads_writes)

Equations:
    OUT[i] = union(IN[s] for s in succ[i])
    IN[i]  = R[i] ∪ (OUT[i] − W[i])

Tiny example (straight-line, no branches):

    0: L0:
    1: mov R1, [rbp-8]
    2: mov R2, [rbp-16]
    3: add R1, R2
    4: mov RAX, R1
    5: ret

From reads_writes:
    R[1] = {},           W[1] = {"R1"}
    R[2] = {},           W[2] = {"R2"}
    R[3] = {"R1","R2"},  W[3] = {"R1"}
    R[4] = {"R1"},       W[4] = {"RAX"}
    R[5] = {},           W[5] = {}

After liveness converges (final IN/OUT):

    IN[1] = {}
    OUT[1] = {"R1"}          ; after mov R1, ... we will need R1 later

    IN[2] = {"R1"}
    OUT[2] = {"R1","R2"}     ; at point after mov R2, both R1 and R2 are live

    IN[3] = {"R1","R2"}
    OUT[3] = {"R1"}          ; after add, R2 is dead, R1 holds the sum

    IN[4] = {"R1"}
    OUT[4] = {}

    IN[5] = {}
    OUT[5] = {}

build_igraph() will use OUT[i] together with W[i] to add interference edges.
"""

"""
in build_igraph
Build the interference graph from liveness information.

Nodes:
    All virtual register names (e.g., "R1","R2","RAX","RDX").

Edges:
    An edge between x and y means: x and y are live at the same time
    at some program point, so they must not share the same physical register.

Classic rule used here:
    For each instruction i, for each vreg x in W[i],
    we add edges from x to every y in OUT[i] (except x itself).

Tiny example continuing the liveness example:

    Instruction 2:  mov R2, [rbp-16]
        W[2]   = {"R2"}
        OUT[2] = {"R1","R2"}

    For x = "R2":
        y = "R1"  -> edge("R2","R1")
        y = "R2"  -> skip (same as x)

    That means: at the program point *after* instruction 2,
    R1 and R2 are both live, so they interfere:

        R1 ---- R2

    RAX gets its own node, and will also interfere with any vregs that are
    live at the same time if we had such a case.

idiv special case:
    x86 idiv uses RAX/RDX, so when we see an Idiv, we add extra edges
    from RAX/RDX to everything live at that point, and between RAX and RDX.
"""

"""
in greedy_color
Simplified graph-coloring register allocator.

Input:
    G          : interference graph (vreg -> set[vreg])
    precolored : mapping of some vregs to fixed physical regs
                    (e.g., {"RAX": "rax", "RDX": "rdx"})
    k_regs     : list of allowed physical registers to use as colors
                    (defaults to CALLER_SAVED without SPILL_SCRATCH)

Output:
    (colors, spills) where:
        colors[vreg] = physical register name (e.g., "R1" -> "rsi")
        spills       = set of vregs that could not be assigned a register

Algorithm (Chaitin/Briggs-style, very simplified):

    1) Simplify phase:
        - Repeatedly pick a non-precolored node v with degree(v) < #colors,
            push it on a stack, and remove it from the graph.
        - If no such node exists, pick a high-degree node as a spill candidate,
            mark it in 'spills', push it on the stack, and remove it.
        - Precolored nodes are never removed.

    2) Select phase:
        - Pop nodes off the stack (reverse of removal order).
        - For each node v:
            look at the colors already used by its neighbors
            pick any available physical register not in that set
            if none is available, v remains in 'spills'.

Tiny example:

    Nodes: R1, R2, RAX
    Edges: R1 <-> R2, RAX isolated
    Precolored: {"RAX": "rax"}
    Colors available (pool): ["rax","rcx","rdx",...,"r11"] minus "r10"

    Simplify:
        - R1 and R2 each have degree 1, pool size is 8 -> both "easy".
        - Push R1, then R2.
    Select:
        - R2: neighbors = {R1}, but R1 isn't colored yet => used = {}
            -> pick "rcx"
        - R1: neighbors = {R2}, and R2 is "rcx" => used = {"rcx"}
            -> pick next free, e.g., "rsi"

    Result:
        colors = {"RAX":"rax", "R2":"rcx", "R1":"rsi"}, spills = {}
"""

"""
in rewrite_with_spills

Rewrite the program using the coloring and spill decisions.

For each vreg:
    - If vreg in colors: use Reg(colors[vreg]) instead.
    - If vreg in spills: keep its value in Mem("spill_<vregname>") and
        use SPILL_SCRATCH (= r10) to load/store as needed.

This step removes virtual registers from the code. Later, pseudo_x86
will map spill_* memory slots to real [rbp-offset] stack slots.

Tiny example (with a spill):

    Suppose we had:
        mov R3, R1
        add R3, R2

    And RA decided:
        colors = {"R1":"rsi","R2":"rcx"}, spills = {"R3"}

    rewrite_with_spills turns this into:

        ; mov R3, R1
        mov r10, rsi                   ; load R1 into scratch
        mov [spill_R3], r10            ; store into spill slot

        ; add R3, R2
        mov r10, [spill_R3]            ; load spilled R3
        add r10, rcx                   ; do the arithmetic
        mov [spill_R3], r10            ; store back

    Later, remap_spills_to_frame might convert [spill_R3] into [rbp-24].
"""

"""
in allocate_registers_on_program

Top-level entry point for RA.

Pipeline:
    1) liveness: compute IN/OUT, plus R/W for each instruction.
    2) build_igraph: construct interference graph from liveness.
    3) greedy_color: assign physical registers + decide spills.
    4) rewrite_with_spills: rewrite program to use only physical regs
                            and Mem("spill_*") for spilled vregs.

After this:
    - There are no bare virtual regs left (only physical regs + spills).
    - pseudo_x86.remap_spills_to_frame() can then map spill_* to [rbp-offset].
"""
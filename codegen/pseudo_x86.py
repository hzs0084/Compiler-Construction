# Signed-only and minimal instruction set with virtual registers for temps.
from dataclasses import dataclass, replace
from typing import Dict, List
from ir.ir_types import Function, Instr, Var, Const
from codegen.x86ir import (
    Program, Imm, Reg, Mem, Label, LabelDef,
    Mov, Add, Sub, IMul, Cmp, Idiv, Jcc, Jmp, Ret, FrameRef, Push, Pop,
    print_program,
)
from codegen.ra import allocate_registers_on_program

# Virtual register naming

@dataclass
class FrameLayout:
    off_by_name: Dict[str, int]   # e.g., {"a": -8, "b": -16}
    size: int                     # positive, rounded for alignment

def build_frame_layout(fn: Function) -> FrameLayout:
    # collect locals (named Vars that TAC declared/used)
    names: list[str] = []
    seen = set()
    for blk in fn.blocks:
        for ins in blk.instrs:
            for v in (getattr(ins, "dst", None), getattr(ins, "a", None), getattr(ins, "b", None)):
                if isinstance(v, Var) and not v.name.startswith("t"):
                    if v.name not in seen:
                        seen.add(v.name); names.append(v.name)

    # assign 8-byte slots: a -> -8, b -> -16, z -> -24, ...
    off_by_name = {}
    off = 0
    for nm in names:
        off -= 8
        off_by_name[nm] = off

    # frame size is positive
    frame_size = -off

    # Optional: 16-byte align (nice for future calls)
    aligned = (frame_size + 15) & ~15
    return FrameLayout(off_by_name, aligned or 0)


@dataclass
class VRegs:
    """
    next_id is the next virtual register index to assign (R1, R2, …)
    by_temp is map from temp name (e.g., "t3") to its virtual register (e.g., "R2")
    cmp_seq is a counter to make fresh label names for tiny true/false
    """
    next_id: int = 1
    by_temp: Dict[str, str] = None
    cmp_seq: int = 0  

    def __post_init__(self):
        if self.by_temp is None:
            self.by_temp = {}

    def reg_of(self, temp_name: str) -> str:
        
        """
        does this temp already have a register and if not then give it the next one
        """
        r = self.by_temp.get(temp_name)
        if r is None:
            r = f"R{self.next_id}"
            self.by_temp[temp_name] = r
            self.next_id += 1
        return r
    
    def fresh_cmp_labels(self):
        """Return (true_label, end_label)."""
        self.cmp_seq += 1
        i = self.cmp_seq
        return (f"Lcmp{i}_true", f"Lcmp{i}_end")

def is_temp(v: Var) -> bool:
    return isinstance(v, Var) and v.name.startswith("t")

def opnd(v, vregs: VRegs, frame: FrameLayout | None = None):
    """
    Map IR values to x86-IR operands:
      Const -> Imm(42)
      temp Var (tN) -> Reg("Rk")
      named Var (x) -> Mem("x")
    """
    if isinstance(v, Const):
        return Imm(v.value)
    if isinstance(v, Var):
        if v.name.startswith("t"):               # temp -> virtual reg
            return Reg(vregs.reg_of(v.name))
        else:
            if frame is not None:                # STACK mode
                return FrameRef(frame.off_by_name[v.name])
            else:                                # SYMBOLIC mode
                return Mem(v.name)
    raise TypeError(f"Unknown value type: {type(v)}")


# Emit helpers

def ensure_in(acc_name: str, src, vregs: VRegs, out: Program, frame: FrameLayout | None) -> Reg:
    s = opnd(src, vregs, frame)

    
    """
    Ensure 'src' is available in a register; if not, move it into acc_name.
    Returns a Reg operand.
    """
    if isinstance(s, Reg):
        return s
    acc = Reg(acc_name)       # virtual register like "R3"
    out.append(Mov(acc, s))   # mov  acc, s
    return acc


def emit_mov(dst, a, vregs: VRegs, out: Program, frame: FrameLayout | None):
    """
    dst = a
    - If dst is temp like t0, emit_mov uses VRegs to map it to a virtual register name like R1 and emits mov R1, <a-opnd>
    - If dst is named variable like a, it uses opnd plus the FrameLayout to choose either a stack slot [rbp-8] in stack mode or a symbolic memory location [a] in non-stack mode, and emits mov [rbp-8], <a-opnd>
    """
    if isinstance(dst, Var) and is_temp(dst):
        # temp: put a into the temp's virtual register
        out.append(Mov(Reg(vregs.reg_of(dst.name)), opnd(a, vregs, frame)))
    elif isinstance(dst, Var):
        # named variable: put 'a' into it's own memory location
        out.append(Mov(opnd(dst, vregs, frame), opnd(a, vregs, frame)))
    else:
        raise TypeError("mov dst must be a Var")


def emit_binop(dst, a, op, b, vregs: VRegs, out: Program,frame: FrameLayout | None):
    # comparisons -> booleanize (0/1)
    comp_jcc = {"==":"je","!=":"jne","<":"jl","<=":"jle",">":"jg",">=":"jge"}
    if op in comp_jcc:
        
        if isinstance(dst, Var) and is_temp(dst):
            dst_where = Reg(vregs.reg_of(dst.name))
        elif isinstance(dst, Var):
            dst_where = Mem(dst.name)
        else:
            raise TypeError("binop dst must be Var")

        tlabel, endlabel = vregs.fresh_cmp_labels()
        # dst = 0
        out.append(Mov(dst_where, Imm(0)))
        # cmp a, b
        left = ensure_in("R3", a, vregs, out, frame)
        out.append(Cmp(left, opnd(b, vregs, frame)))
        # jcc true; jmp end; true: dst=1; end:
        out.append(Jcc(comp_jcc[op], Label(tlabel)))
        out.append(Jmp(Label(endlabel)))
        out.append(LabelDef(Label(tlabel)))
        out.append(Mov(dst_where, Imm(1)))
        out.append(LabelDef(Label(endlabel)))
        return

    # division (signed: idiv). Result lives in RAX, so move a -> RAX, divisor in a reg, idiv
    if op == "/":
        if isinstance(dst, Var) and is_temp(dst):
            dst_where = Reg(vregs.reg_of(dst.name))
        elif isinstance(dst, Var):
            dst_where = Mem(dst.name)
        else:
            raise TypeError("binop dst must be Var")
        # mov RAX, a
        a_src = opnd(a, vregs, frame)
        out.append(Mov(Reg("RAX"), a_src))
        # divisor must be a reg
        divreg = ensure_in("R2", b, vregs, out, frame)
        out.append(Idiv(divreg))
        # move result if needed
        if not (isinstance(dst_where, Reg) and dst_where.name == "RAX"):
            out.append(Mov(dst_where, Reg("RAX")))
        return

    if op == "%":
        raise NotImplementedError("Modulo (%) is not supported yet (by design).")

    # arithmetic +, -, * (two-operand: dst := dst op src)
    # Choose accumulator 
    if isinstance(dst, Var) and is_temp(dst):
        dst_where = Reg(vregs.reg_of(dst.name))
        acc = dst_where
        a_src = opnd(a, vregs, frame)
        if not (isinstance(a_src, Reg) and a_src.name == acc.name):
            out.append(Mov(acc, a_src))
    elif isinstance(dst, Var):
        dst_where = Mem(dst.name)
        acc = Reg("R1")
        out.append(Mov(acc, opnd(a, vregs, frame)))
    else:
        raise TypeError("binop dst must be Var")

    # do the op
    src_op = opnd(b, vregs, frame)
    if op == "+":
        out.append(Add(acc, src_op))
    elif op == "-":
        out.append(Sub(acc, src_op))
    elif op == "*":
        out.append(IMul(acc, src_op))
    else:
        raise NotImplementedError(f"Unsupported binop: {op}")

    # if destination is memory, store back
    if isinstance(dst_where, Mem):
        out.append(Mov(dst_where, acc))


def emit_unop(dst, op, a, vregs: VRegs, out: Program, frame: FrameLayout | None):
    if not isinstance(dst, Var):
        raise TypeError("unop dst must be Var")

    if op == "+":
        emit_mov(dst, a, vregs, out, frame)
        return

    if op == "-":
        if is_temp(dst):
            acc = Reg(vregs.reg_of(dst.name))
            out.append(Mov(acc, Imm(0)))
            out.append(Sub(acc, opnd(a, vregs, frame)))
        else:
            acc = Reg("R1")
            out.append(Mov(acc, Imm(0)))
            out.append(Sub(acc, opnd(a, vregs, frame)))
            out.append(Mov(Mem(dst.name), acc))
        return

    if op == "!":
        where = Reg(vregs.reg_of(dst.name)) if is_temp(dst) else Mem(dst.name)
        tlabel, endlabel = vregs.fresh_cmp_labels()
        out.append(Mov(where, Imm(0)))
        left = ensure_in("R4", a, vregs, out, frame)
        out.append(Cmp(left, Imm(0)))
        out.append(Jcc("je", Label(tlabel)))  # true when a==0
        out.append(Jmp(Label(endlabel)))
        out.append(LabelDef(Label(tlabel)))
        out.append(Mov(where, Imm(1)))
        out.append(LabelDef(Label(endlabel)))
        return

    raise NotImplementedError(f"Unsupported unop: {op}")


def emit_br(cond, tlabel: str, flabel: str, next_label: str, vregs: VRegs, out: Program, frame: FrameLayout | None):
    """
    Compare cond with 0 and branch. If the next block is the false path,
    fall through without an extra jump (cosmetic).
    """
    left = ensure_in("R5", cond, vregs, out, frame)
    out.append(Cmp(left, Imm(0)))
    if next_label == flabel:
        out.append(Jcc("jne", Label(tlabel)))  # fall-through to false
    elif next_label == tlabel:
        out.append(Jcc("je", Label(flabel)))   # invert, fall-through to true
    else:
        out.append(Jcc("jne", Label(tlabel)))
        out.append(Jmp(Label(flabel)))

def emit_instr(ins: Instr, next_blk_label: str, vregs: VRegs, out: Program, frame: FrameLayout | None):
    k = ins.kind
    if k == "label":
        out.append(LabelDef(Label(ins.label)))
    elif k == "mov":
        emit_mov(ins.dst, ins.a, vregs, out, frame)
    elif k == "binop":
        emit_binop(ins.dst, ins.a, ins.op, ins.b, vregs, out, frame)
    elif k == "unop":
        emit_unop(ins.dst, ins.op, ins.a, vregs, out, frame)
    elif k == "br":
        emit_br(ins.a, ins.tlabel, ins.flabel, next_blk_label, vregs, out, frame)
    elif k == "jmp":
        out.append(Jmp(Label(ins.tlabel)))
    elif k == "ret":
        if ins.a is None:
            # real x86 returns don’t carry an operand
            out.append(Ret())
        else:
            # move return value into RAX, then ret
            out.append(Mov(Reg("RAX"), opnd(ins.a, vregs, frame)))
            out.append(Ret())

    else:
        raise NotImplementedError(k)

    
def _dedupe_adjacent(lines):
    
    """if two identical mov lines are right next to each other, erase the extra one."""

    out = []
    last = None
    for ln in lines:
        if ln == last and ln.startswith("mov"):
            # only delete duplicate movs and keep labels/branches etc.
            continue
        out.append(ln)
        last = ln
    return out


def _name(o):
    return getattr(o, "name", "").lower()

def _is_epilogue_ins(ins):
    # Treat stack epilogue as "transparent" between tail shuffles and ret
    return (isinstance(ins, Add) and isinstance(ins.dst, Reg) and _name(ins.dst) == "rsp") \
           or isinstance(ins, Pop)

def peephole_ret_rax_program(prog: Program) -> Program:
    """
    Clean up redundant RAX shuffles at function tail.
    Handles both:
      - mov Rt, rax ; mov rax, Rt ; ret
      - mov Rt, rax ; mov rax, Rt ; (add rsp, K)? ; (pop rbp)? ; ret
    Also drops 'mov rax, rax'.
    """
    out: Program = []
    i = 0
    n = len(prog)

    while i < n:
        ins = prog[i]

        # Drop trivial 'mov rax, rax'
        if isinstance(ins, Mov) and isinstance(ins.dst, Reg) and isinstance(ins.src, Reg):
            if _name(ins.dst) == "rax" and _name(ins.src) == "rax":
                i += 1
                continue

        # Try to match: mov Rt, rax ; mov rax, Rt ; (epilogue...)? ; ret
        if i + 1 < n and isinstance(prog[i], Mov) and isinstance(prog[i+1], Mov):
            m1: Mov = prog[i]
            m2: Mov = prog[i+1]
            if (isinstance(m1.dst, Reg) and isinstance(m1.src, Reg) and _name(m1.src) == "rax" and
                isinstance(m2.dst, Reg) and _name(m2.dst) == "rax" and
                isinstance(m2.src, Reg) and _name(m2.src) == _name(m1.dst)):
                # Scan forward over optional epilogue to see if a Ret follows
                j = i + 2
                while j < n and _is_epilogue_ins(prog[j]):
                    j += 1
                if j < n and isinstance(prog[j], Ret):
                    # Keep the epilogue (if any), drop the two movs
                    # Emit any epilogue between them and the ret, then the ret
                    # First, copy through everything from i+2 up to and including j
                    for k in range(i + 2, j + 1):
                        out.append(prog[k])
                    i = j + 1
                    continue
                # If no ret after, fall through (don't risk changing semantics).

        # Default: pass-through
        out.append(ins)
        i += 1

    return out


def replace_operands(ins, map_op):
    if isinstance(ins, Mov):
        return Mov(map_op(ins.dst), map_op(ins.src))
    if isinstance(ins, Add):
        return Add(map_op(ins.dst), map_op(ins.src))
    if isinstance(ins, Sub):
        return Sub(map_op(ins.dst), map_op(ins.src))
    if isinstance(ins, IMul):
        return IMul(map_op(ins.dst), map_op(ins.src))
    if isinstance(ins, Cmp):
        return Cmp(map_op(ins.a), map_op(ins.b))
    if isinstance(ins, Idiv):
        return Idiv(map_op(ins.src))  # src is a Reg (map_op will pass it through)
    if isinstance(ins, Jcc):
        return ins
    if isinstance(ins, Jmp):
        return ins
    if isinstance(ins, Ret):
        return ins
    if isinstance(ins, LabelDef):
        return ins
    if isinstance(ins, Push):
        return Push(map_op(ins.reg))
    if isinstance(ins, Pop):
        return Pop(map_op(ins.reg))
    return ins


def remap_spills_to_frame(prog: Program, frame: FrameLayout) -> Program:
    next_off = -(frame.size + 8)  # grow below locals
    spill_map: Dict[str, int] = {}
    patched = []
    for ins in prog:
        def map_op(op):
            if isinstance(op, Mem) and op.name.startswith("spill"):
                if op.name not in spill_map:
                    spill_map[op.name] = next_off
                    next_off -= 8
                return FrameRef(spill_map[op.name])
            return op

        ins = replace_operands(ins, map_op)  # tiny helper to rebuild ins with mapped operands
        patched.append(ins)
    # also bump frame.size by the spill area (abs(next_off) - original size), then re-emit epilogue sizes
    return patched



# entrypoint

def emit_function(fn: Function, enable_ra: bool = False, frame_mode: str = "off") -> str:
    prog: Program = []
    vregs = VRegs()

    frame = None

    if frame_mode == "stack":
        frame = build_frame_layout(fn)
        # Real prologue:
        prog.append(Push(Reg("RBP")))            # push rbp
        prog.append(Mov(Reg("RBP"), Reg("RSP"))) # mov rbp, rsp
        if frame.size:
            prog.append(Sub(Reg("RSP"), Imm(frame.size)))  # sub rsp, frame.size

    # Emit blocks
    for i, blk in enumerate(fn.blocks):
        if blk.label:
            prog.append(LabelDef(Label(blk.label)))
        next_label = fn.blocks[i+1].label if (i+1)<len(fn.blocks) and fn.blocks[i+1].label else ""
        for ins in blk.instrs:
            emit_instr(ins, next_label, vregs, prog, frame)   # pass frame down

    # Ensure ret
    has_ret = any(isinstance(i, Ret) for i in prog)
    if not has_ret:
        prog.append(Ret())

    # If stack mode, fix every Ret to epilogue form
    if frame_mode == "stack":
        patched = []
        for ins in prog:
            if isinstance(ins, Ret):
                # replace with epilogue
                if frame.size:
                    patched.append(Add(Reg("RSP"), Imm(frame.size)))  # add back
                # 'mov rsp, rbp; pop rbp'; 
                patched.append(Pop(Reg("RBP")))                      # "pop rbp"
                patched.append(Ret())
            else:
                patched.append(ins)
        prog = patched

    # RA 
    if enable_ra and frame_mode == "stack":
        prog = remap_spills_to_frame(prog, frame)

    prog = peephole_ret_rax_program(prog)

    lines = print_program(prog)
    return "\n".join(["function " + fn.name] + lines)

def emit_pseudo_x86(fn: Function, enable_ra: bool = False, frame_mode: str = "off") -> str:
    return emit_function(fn, enable_ra=enable_ra, frame_mode=frame_mode)


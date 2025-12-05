# Signed-only and minimal instruction set with virtual registers for temps.
from dataclasses import dataclass
from typing import Dict, List
from ir.ir_types import Function, Instr, Var, Const
from codegen.x86ir import (
    Program, Imm, Reg, Mem, Label, LabelDef,
    Mov, Add, Sub, IMul, Cmp, Idiv, Jcc, Jmp, Ret,
    print_program,
)
from codegen.ra import allocate_registers_on_program

# Virtual register naming

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

def opnd(v, vregs: VRegs):
    """
    Map IR values to x86-IR operands:
      Const -> Imm(42)
      temp Var (tN) -> Reg("Rk")
      named Var (x) -> Mem("x")
    """
    if isinstance(v, Const):
        return Imm(v.value)
    if isinstance(v, Var):
        if is_temp(v):
            return Reg(vregs.reg_of(v.name))
        else:
            return Mem(v.name)
    raise TypeError(f"Unknown value type: {type(v)}")


# Emit helpers

def ensure_in(acc_name: str, src, vregs: VRegs, out: Program) -> Reg:
    
    """
    Ensure 'src' is available in a register; if not, move it into acc_name.
    Returns a Reg operand.
    """

    s = opnd(src, vregs)
    if isinstance(s, Reg):
        return s
    acc = Reg(acc_name)       # virtual register like "R3"
    out.append(Mov(acc, s))   # mov  acc, s
    return acc


def emit_mov(dst, a, vregs: VRegs, out: Program):
    """
    dst temp  -> Mov(Reg("Rk"), opnd(a))
    dst named -> Mov(Mem("x"),  opnd(a))
    """
    if isinstance(dst, Var) and is_temp(dst):
        out.append(Mov(Reg(vregs.reg_of(dst.name)), opnd(a, vregs)))
    elif isinstance(dst, Var):
        out.append(Mov(Mem(dst.name), opnd(a, vregs)))
    else:
        raise TypeError("mov dst must be a Var")


def emit_binop(dst, a, op, b, vregs: VRegs, out: Program):
    # comparisons -> booleanize (0/1)
    comp_jcc = {"==":"je","!=":"jne","<":"jl","<=":"jle",">":"jg",">=":"jge"}
    if op in comp_jcc:
        # where do we store the 0/1?
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
        left = ensure_in("R3", a, vregs, out)
        out.append(Cmp(left, opnd(b, vregs)))
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
        a_src = opnd(a, vregs)
        out.append(Mov(Reg("RAX"), a_src))
        # divisor must be a reg
        divreg = ensure_in("R2", b, vregs, out)
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
        a_src = opnd(a, vregs)
        if not (isinstance(a_src, Reg) and a_src.name == acc.name):
            out.append(Mov(acc, a_src))
    elif isinstance(dst, Var):
        dst_where = Mem(dst.name)
        acc = Reg("R1")
        out.append(Mov(acc, opnd(a, vregs)))
    else:
        raise TypeError("binop dst must be Var")

    # do the op
    src_op = opnd(b, vregs)
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


def emit_unop(dst, op, a, vregs: VRegs, out: Program):
    if not isinstance(dst, Var):
        raise TypeError("unop dst must be Var")

    if op == "+":
        emit_mov(dst, a, vregs, out)
        return

    if op == "-":
        if is_temp(dst):
            acc = Reg(vregs.reg_of(dst.name))
            out.append(Mov(acc, Imm(0)))
            out.append(Sub(acc, opnd(a, vregs)))
        else:
            acc = Reg("R1")
            out.append(Mov(acc, Imm(0)))
            out.append(Sub(acc, opnd(a, vregs)))
            out.append(Mov(Mem(dst.name), acc))
        return

    if op == "!":
        where = Reg(vregs.reg_of(dst.name)) if is_temp(dst) else Mem(dst.name)
        tlabel, endlabel = vregs.fresh_cmp_labels()
        out.append(Mov(where, Imm(0)))
        left = ensure_in("R4", a, vregs, out)
        out.append(Cmp(left, Imm(0)))
        out.append(Jcc("je", Label(tlabel)))  # true when a==0
        out.append(Jmp(Label(endlabel)))
        out.append(LabelDef(Label(tlabel)))
        out.append(Mov(where, Imm(1)))
        out.append(LabelDef(Label(endlabel)))
        return

    raise NotImplementedError(f"Unsupported unop: {op}")


def emit_br(cond, tlabel: str, flabel: str, next_label: str, vregs: VRegs, out: Program):
    """
    Compare cond with 0 and branch. If the next block is the false path,
    fall through without an extra jump (cosmetic).
    """
    left = ensure_in("R5", cond, vregs, out)
    out.append(Cmp(left, Imm(0)))
    if next_label == flabel:
        out.append(Jcc("jne", Label(tlabel)))  # fall-through to false
    elif next_label == tlabel:
        out.append(Jcc("je", Label(flabel)))   # invert, fall-through to true
    else:
        out.append(Jcc("jne", Label(tlabel)))
        out.append(Jmp(Label(flabel)))

def emit_instr(ins: Instr, next_blk_label: str, vregs: VRegs, out: Program):
    k = ins.kind
    if k == "label":
        out.append(LabelDef(Label(ins.label)))
    elif k == "mov":
        emit_mov(ins.dst, ins.a, vregs, out)
    elif k == "binop":
        emit_binop(ins.dst, ins.a, ins.op, ins.b, vregs, out)
    elif k == "unop":
        emit_unop(ins.dst, ins.op, ins.a, vregs, out)
    elif k == "br":
        emit_br(ins.a, ins.tlabel, ins.flabel, next_blk_label, vregs, out)
    elif k == "jmp":
        out.append(Jmp(Label(ins.tlabel)))
    elif k == "ret":
        if ins.a is None:
            # real x86 returns don’t carry an operand
            out.append(Ret())
        else:
            # move return value into RAX, then ret
            out.append(Mov(Reg("RAX"), opnd(ins.a, vregs)))
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


def _peephole_ret_rax(lines):

    """
    if the last thing is mov R?, RAX and then ret R?, just do ret RAX
    """
    if len(lines) >= 2:
        prev, last = lines[-2].strip(), lines[-1].strip()
        if prev.startswith("mov") and last.startswith("ret"):
            _, rest = prev.split(None, 1)
            dst, src = [x.strip() for x in rest.split(",", 1)]
            if src == "RAX" and last.endswith(dst):
                lines[-2] = "ret  RAX"
                lines.pop()
    return lines


# entrypoint

def emit_function(fn: Function, enable_ra: bool = False) -> str:
    """
    Build object-level x86-IR, run register allocation, then pretty-print.
    """
    prog: Program = []     # list[Instr] objects
    vregs = VRegs()

    # Emit blocks in order
    for i, blk in enumerate(fn.blocks):
        if blk.label:
            prog.append(LabelDef(Label(blk.label)))
        next_label = fn.blocks[i+1].label if (i+1) < len(fn.blocks) and fn.blocks[i+1].label else ""
        for ins in blk.instrs:
            emit_instr(ins, next_label, vregs, prog)

    # Ensure there's a ret
    if not any(isinstance(i, Ret) for i in prog):
        prog.append(Ret())

    # Register Allocation on objects
    if enable_ra:
        prog = allocate_registers_on_program(prog)

    # Pretty print
    lines = print_program(prog)
    return "\n".join(["function " + fn.name] + lines)

def emit_pseudo_x86(fn: Function, enable_ra: bool = False) -> str:
    return emit_function(fn, enable_ra=enable_ra)

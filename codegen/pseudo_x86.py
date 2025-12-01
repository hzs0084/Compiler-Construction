# Human-readable Intel-style pseudo-assembly only
# Signed-only and minimal instruction set with virtual registers for temps.
from dataclasses import dataclass
from typing import Dict, List
from ir.ir_types import Function, Instr, Var, Const

# Virtual register naming

@dataclass
class VRegs:
    next_id: int = 1
    by_temp: Dict[str, str] = None
    cmp_seq: int = 0  # per-function sequence for comparison/boolean labels

    def __post_init__(self):
        if self.by_temp is None:
            self.by_temp = {}

    def reg_of(self, temp_name: str) -> str:
        r = self.by_temp.get(temp_name)
        if r is None:
            r = f"R{self.next_id}"
            self.by_temp[temp_name] = r
            self.next_id += 1
        return r
    
    def fresh_cmp_labels(self):
        """Return (true_label, end_label) with a monotonic, per-function id."""
        self.cmp_seq += 1
        i = self.cmp_seq
        return (f"Lcmp{i}_true", f"Lcmp{i}_end")

def is_temp(v: Var) -> bool:
    return isinstance(v, Var) and v.name.startswith("t")

def opnd(v, vregs: VRegs) -> str:
    if isinstance(v, Const):
        return str(v.value)
    if isinstance(v, Var):
        return vregs.reg_of(v.name) if is_temp(v) else f"[{v.name}]"
    raise TypeError(f"Unknown value type: {type(v)}")

# Emit helpers

def ensure_in(acc: str, src, vregs: VRegs, out: List[str]) -> str:
    s = opnd(src, vregs)
    # If it's already a virtual reg (Rk) or special RAX/RDX, return name
    if s.startswith("R") or s in ("RAX", "RDX"):
        return s
    out.append(f"mov  {acc}, {s}")
    return acc

def emit_mov(dst, a, vregs: VRegs, out: List[str]):
    # temps -> Rk, named vars -> [name]
    if isinstance(dst, Var) and is_temp(dst):
        out.append(f"mov  {vregs.reg_of(dst.name)}, {opnd(a, vregs)}")
    elif isinstance(dst, Var):
        out.append(f"mov  [{dst.name}], {opnd(a, vregs)}")
    else:
        raise TypeError("mov dst must be a Var")

def emit_binop(dst, a, op, b, vregs: VRegs, out: List[str]):
    #  Comparisons first: materialize 0/1 WITHOUT preloading 'a' 
    comp_jcc = {
        "==": "je", "!=": "jne",
        "<": "jl", "<=": "jle",
        ">": "jg", ">=": "jge",
    }
    if op in comp_jcc:
        if isinstance(dst, Var) and is_temp(dst):
            dst_where = vregs.reg_of(dst.name)
        elif isinstance(dst, Var):
            dst_where = f"[{dst.name}]"
        else:
            raise TypeError("binop dst must be Var")
        true_l = f".Ltrue_{id(dst)}"
        end_l  = f".Lend_{id(dst)}"
        true_l, end_l = vregs.fresh_cmp_labels()
        out.append(f"mov  {dst_where}, 0")
        left = ensure_in("R3", a, vregs, out)
        out.append(f"cmp  {left}, {opnd(b, vregs)}")
        out.append(f"{comp_jcc[op]} {true_l}")
        out.append(f"jmp  {end_l}")
        out.append(f"{true_l}:")
        out.append(f"mov  {dst_where}, 1")
        out.append(f"{end_l}:")
        return

    # Division: handle BEFORE any preload
    if op == "/":  # signed division only
        if isinstance(dst, Var) and is_temp(dst):
            dst_where = vregs.reg_of(dst.name)
        elif isinstance(dst, Var):
            dst_where = f"[{dst.name}]"
        else:
            raise TypeError("binop dst must be Var")

        a_src = opnd(a, vregs)
        out.append(f"mov  RAX, {a_src}")
        out.append("cqo")
        out.append(f"mov  R2, {opnd(b, vregs)}")
        out.append("idiv R2")
        if dst_where != "RAX":
            out.append(f"mov  {dst_where}, RAX")
        return

    if op == "%":
        raise NotImplementedError("Modulo (%) is not supported yet (by design).")

    # Arithmetic ops: preload 'a' then op
    if isinstance(dst, Var) and is_temp(dst):
        dst_where = vregs.reg_of(dst.name)
        acc = dst_where
        a_src = opnd(a, vregs)
        if a_src != acc:
            out.append(f"mov  {acc}, {a_src}")
    elif isinstance(dst, Var):
        dst_where = f"[{dst.name}]"
        acc = "R1"
        out.append(f"mov  {acc}, {opnd(a, vregs)}")
    else:
        raise TypeError("binop dst must be Var")
    
    #  Arithmetic ops: preload 'a' into an accumulator and operate in place
    if isinstance(dst, Var) and is_temp(dst):
        dst_where = vregs.reg_of(dst.name)
        acc = dst_where
        a_src = opnd(a, vregs)
        if a_src != acc:
            out.append(f"mov  {acc}, {a_src}")
    elif isinstance(dst, Var):
        dst_where = f"[{dst.name}]"
        acc = "R1"
        out.append(f"mov  {acc}, {opnd(a, vregs)}")
    else:
        raise TypeError("binop dst must be Var")

    if op == "+":
        out.append(f"add  {acc}, {opnd(b, vregs)}")
        if acc != dst_where:
            out.append(f"mov  {dst_where}, {acc}")
        return
    if op == "-":
        out.append(f"sub  {acc}, {opnd(b, vregs)}")
        if acc != dst_where:
            out.append(f"mov  {dst_where}, {acc}")
        return
    if op == "*":
        out.append(f"imul {acc}, {opnd(b, vregs)}")
        if acc != dst_where:
            out.append(f"mov  {dst_where}, {acc}")
        return
    # If the code comes  here with a non-arith, non-comp op:
    raise NotImplementedError(f"Unsupported binop: {op}")


def emit_unop(dst, op, a, vregs: VRegs, out: List[str]):
    if not isinstance(dst, Var):
        raise TypeError("unop dst must be Var")

    if op == "+":
        emit_mov(dst, a, vregs, out)
        return
    if op == "-":
        # no 'neg' to keep set minimal: 0 - a
        if is_temp(dst):
            acc = vregs.reg_of(dst.name)
            out.append(f"mov  {acc}, 0")
            out.append(f"sub  {acc}, {opnd(a, vregs)}")
        else:
            out.append(f"mov  R1, 0")
            out.append(f"sub  R1, {opnd(a, vregs)}")
            out.append(f"mov  [{dst.name}], R1")
        return
    if op == "!":
        where = vregs.reg_of(dst.name) if (isinstance(dst, Var) and is_temp(dst)) else f"[{dst.name}]"
        true_l, end_l = vregs.fresh_cmp_labels()   # deterministic labels
        out.append(f"mov  {where}, 0")
        left = ensure_in("R4", a, vregs, out)
        out.append(f"cmp  {left}, 0")
        out.append(f"je   {true_l}")   # not a is true when a == 0
        out.append(f"jmp  {end_l}")
        out.append(f"{true_l}:")
        out.append(f"mov  {where}, 1")
        out.append(f"{end_l}:")
        return

    raise NotImplementedError(f"Unsupported unop: {op}")

def emit_br(cond, tlabel: str, flabel: str, next_label: str, vregs: VRegs, out: List[str]):
    
    """
    Branch lowering with a tiny fall-through heuristic:
      - If next block is flabel: emit 'cmp; jne T' and fall through to F (no jmp).
      - Else if next block is tlabel: invert sense to fall through to T (emit 'cmp; je F').
      - Else: emit 'cmp; jne T' and 'jmp F'.
    """

    left = ensure_in("R5", cond, vregs, out)
    out.append(f"cmp  {left}, 0")
    if next_label == flabel:
        out.append(f"jne  {tlabel}")
        # fall-through to false
    elif next_label == tlabel:
        out.append(f"je   {flabel}")  # invert so  fall through to true
    else:
        out.append(f"jne  {tlabel}")
        out.append(f"jmp  {flabel}")

def emit_instr(ins: Instr, next_blk_label: str, vregs: VRegs, out: List[str]):
    k = ins.kind
    if k == "label":
        out.append(f"{ins.label}:")
    elif k == "mov":
        emit_mov(ins.dst, ins.a, vregs, out)
    elif k == "binop":
        emit_binop(ins.dst, ins.a, ins.op, ins.b, vregs, out)
    elif k == "unop":
        emit_unop(ins.dst, ins.op, ins.a, vregs, out)
    elif k == "br":
        emit_br(ins.a, ins.tlabel, ins.flabel, next_blk_label, vregs, out)
    elif k == "jmp":
        out.append(f"jmp  {ins.tlabel}")
    elif k == "ret":
        # Human-readable pseudo-return
        if ins.a is None:
            out.append("ret  0")
        else:
            out.append(f"ret  {opnd(ins.a, vregs)}")
    else:
        raise NotImplementedError(k)
    
def _dedupe_adjacent(lines):
    
    """Drop exact duplicate consecutive instructions (cosmetic peephole)."""

    out = []
    last = None
    for ln in lines:
        if ln == last and ln.startswith("mov"):
            # only delete duplicate movs and keep labels/branches etc.
            continue
        out.append(ln)
        last = ln
    return out

def _peephole_copies(lines):
    out = []
    alias = {}  # reg -> source it equals
    for ln in lines:
        s = ln.strip()
        if s.startswith("mov") and "," in s:
            dst, src = [x.strip() for x in s[4:].split(",", 1)]
            # drop 'mov Rx, Rx'
            if dst == src:
                continue
            # track simple reg->reg copies
            if dst.startswith("R") and src.startswith("R"):
                alias[dst] = alias.get(src, src)
                out.append(f"mov  {dst}, {alias[dst]}")
                continue
            # any write to a reg breaks its alias
            if dst.startswith("R"):
                alias.pop(dst, None)
        else:
            # writes through ALU kill alias on the dest
            if s[:3] in ("add", "sub", "imu"):  # imul
                parts = s.split()
                if len(parts) >= 2 and parts[1].endswith(","):
                    dst = parts[1].rstrip(",")
                    if dst.startswith("R"):
                        alias.pop(dst, None)
            elif s.startswith("ret"):
                pass
        out.append(ln)
    return out

def _peephole_ret_rax(lines):
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

def emit_function(fn: Function) -> str:
    
    """
    Produce human-readable Intel-style assembly:
      - Temps -> R1.. virtual regs (first-use order)
      - Named variables -> [name]
      - Labels printed verbatim
      - Signed division only (idiv), modulo not supported (yet)
    """

    out: List[str] = [f"function {fn.name}"]
    vregs = VRegs()

    # print blocks in existing order and use next block label for fall-through
    for i, blk in enumerate(fn.blocks):
        if blk.label:
            out.append(f"{blk.label}:")
        next_label = fn.blocks[i+1].label if (i+1) < len(fn.blocks) and fn.blocks[i+1].label else ""
        for ins in blk.instrs:
            emit_instr(ins, next_label, vregs, out)

    # if no explicit ret was seen, add a pseudo-ret
    if not any(i.kind == "ret" for b in fn.blocks for i in b.instrs):
        out.append("ret  0")

    # cosmetic peephole by removing adjacent duplicate movs
    out[:] = _dedupe_adjacent(out)
    out[:] = _peephole_ret_rax(out)

    return "\n".join(out)

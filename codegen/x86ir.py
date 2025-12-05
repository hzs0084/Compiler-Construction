# codegen/x86ir.py
from dataclasses import dataclass
from typing import List, Optional, Union

# Operands

@dataclass(frozen=True)
class Imm:
    value: int

@dataclass(frozen=True)
class Reg:
    name: str          # "R1", "R2", "RAX", "RDX", ...
    fixed: Optional[str] = None  # e.g., precolored: fixed="rax"

@dataclass(frozen=True)
class Mem:
    name: str          # "[x]" style will be printed; logical name only e.g. "x" or "spill_R1"

@dataclass(frozen=True)
class Label:
    name: str

Operand = Union[Imm, Reg, Mem]

# Instructions

@dataclass
class Instr:
    pass

@dataclass
class LabelDef(Instr):
    label: Label

@dataclass
class Mov(Instr):
    dst: Operand
    src: Operand

@dataclass
class Add(Instr):
    dst: Reg
    src: Operand

@dataclass
class Sub(Instr):
    dst: Reg
    src: Operand

@dataclass
class IMul(Instr):
    dst: Reg
    src: Operand

@dataclass
class Cmp(Instr):
    a: Operand
    b: Operand

@dataclass
class Idiv(Instr):
    src: Reg  # divisor must be a reg (we’ll enforce during lowering/RA)

@dataclass
class Jcc(Instr):
    cc: str       # "je","jne","jl","jg","jle","jge"
    target: Label

@dataclass
class Jmp(Instr):
    target: Label

@dataclass
class Ret(Instr):
    val: Optional[Operand] = None

Program = List[Instr]

# Pretty printer (Intel-like)

def _op(o: Operand) -> str:
    if isinstance(o, Imm):
        return str(o.value)
    if isinstance(o, Reg):
        return o.name.lower() if o.name.startswith(("R", "RA", "RD")) else o.name
    if isinstance(o, Mem):
        return f"[{o.name}]"
    raise TypeError(o)

def _lbl(l: Label) -> str:
    return l.name

def print_program(p: Program) -> List[str]:
    out: List[str] = []
    for ins in p:
        if isinstance(ins, LabelDef):
            out.append(f"{_lbl(ins.label)}:")
        elif isinstance(ins, Mov):
            out.append(f"mov  {_op(ins.dst)}, {_op(ins.src)}")
        elif isinstance(ins, Add):
            out.append(f"add  {_op(ins.dst)}, {_op(ins.src)}")
        elif isinstance(ins, Sub):
            out.append(f"sub  {_op(ins.dst)}, {_op(ins.src)}")
        elif isinstance(ins, IMul):
            out.append(f"imul {_op(ins.dst)}, {_op(ins.src)}")
        elif isinstance(ins, Cmp):
            out.append(f"cmp  {_op(ins.a)}, {_op(ins.b)}")
        elif isinstance(ins, Idiv):
            out.append(f"idiv {_op(ins.src)}")
        elif isinstance(ins, Jcc):
            out.append(f"{ins.cc} {_lbl(ins.target)}")
        elif isinstance(ins, Jmp):
            out.append(f"jmp  {_lbl(ins.target)}")
        elif isinstance(ins, Ret):
                out.append("ret")
                continue
        else:
            raise NotImplementedError(type(ins))
    return out

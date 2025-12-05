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

@dataclass
class FrameRef:
    offset: int  # negative (e.g., -8, -16, …)

Operand = Union[Imm, Reg, Mem, FrameRef]

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


@dataclass 
class Push(Instr): 
    reg: Reg

@dataclass
class Pop(Instr):  
    reg: Reg

Program = List[Instr]

# Pretty printer (Intel-like)

def _op(o: Operand) -> str:
    if isinstance(o, Imm):
        return str(o.value)
    if isinstance(o, Reg):
        return o.name.lower()  # keep as is
    if isinstance(o, Mem):
        return f"[{o.name}]"
    if isinstance(o, FrameRef):
        k = -o.offset
        return f"[rbp-{k}]" if k != 0 else "[rbp]"
    raise TypeError(o)

def _lbl(l: Label) -> str:
    return l.name

def fmt(op):
    if isinstance(op, FrameRef):
        k = -op.offset
        return f"[rbp-{k}]" if k != 0 else "[rbp]"
    # existing: Imm, Reg, Mem, Label, etc.


def print_program(p: Program) -> List[str]:
    out: List[str] = []
    for ins in p:
        if isinstance(ins, LabelDef):
            out.append(f"{ins.label.name}:")
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
            out.append(f"{ins.cc} {ins.target.name}")
        elif isinstance(ins, Jmp):
            out.append(f"jmp  {ins.target.name}")
        elif isinstance(ins, Ret):
            out.append("ret")
        elif isinstance(ins, Push):
            out.append(f"push {_op(ins.reg)}")
        elif isinstance(ins, Pop):
            out.append(f"pop  {_op(ins.reg)}")
        else:
            raise NotImplementedError(type(ins))
    return out

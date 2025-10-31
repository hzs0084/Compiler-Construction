from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict

# Values
@dataclass
class Const: value: int
@dataclass
class Var:   name: str
Value = Union[Const, Var]

# Ops we care about now
BINOPS = {"+","-","*","/","%","==","!=", "<","<=",">",">=","&&","||"}
UNOPS  = {"+","-","!"}

# Instruction
@dataclass
class Instr:
    # kinds: "label","mov","binop","unop","br","jmp","ret"
    kind: str
    dst: Optional[Var] = None
    op:  Optional[str] = None
    a:   Optional[Value] = None
    b:   Optional[Value] = None
    # branch targets
    tlabel: Optional[str] = None
    flabel: Optional[str] = None
    # for labels
    label: Optional[str] = None

    def has_side_effect(self) -> bool:
        # later add "store"/"call" here
        return False

# Basic block / Function
@dataclass
class Block:
    label: str
    instrs: List[Instr] = field(default_factory=list)

@dataclass
class Function:
    name: str
    blocks: List[Block] = field(default_factory=list)
    succ: Dict[str, List[str]] = field(default_factory=dict)
    pred: Dict[str, List[str]] = field(default_factory=dict)

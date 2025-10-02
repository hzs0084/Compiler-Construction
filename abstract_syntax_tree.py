from dataclasses import dataclass
from typing import List, Optional, Union

# Program structure
@dataclass
class Program:
    functions: List["Function"]
    pass

@dataclass
class Function:
    name: str
    body: "Block"
    pass

@dataclass
class Block:
    items: List[Union["VarDecl", "Stmt"]]
    pass

@dataclass
class VarDecl:
    names: List[str]  
    pass

# Statements
class Stmt:
    pass

@dataclass
class Return(Stmt):
    expr: "Expr"
    pass

@dataclass
class If(Stmt):
    cond: "Expr"
    then_branch: Block
    else_branch: Optional[Block]
    pass

@dataclass
class While(Stmt):
    cond: "Expr"
    body: Block
    pass

@dataclass
class ExprStmt(Stmt):
    expr: "Expr"
    pass

# Expressions
class Expr:
    pass

@dataclass
class Assign(Expr):
    name: str
    value: Expr
    pass

@dataclass
class Binary(Expr):
    op: str
    left: Expr
    right: Expr
    pass

@dataclass
class Unary(Expr):
    op: str
    expr: Expr
    pass

@dataclass
class Var(Expr):
    name: str
    pass

@dataclass
class IntLit(Expr):
    value: int
    pass

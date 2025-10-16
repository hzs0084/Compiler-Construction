from dataclasses import dataclass
from typing import List, Union, Optional

@dataclass
class Program:
    functions: List["Function"]

@dataclass
class Function:
    name: str
    body: "Block"

# Statements
class Stmt: 
    pass

@dataclass
class Block:
    items: List[Union[Stmt]]

@dataclass
class ExprStmt(Stmt):
    expr: "Expr"

@dataclass
class Return(Stmt):
    expr: "Expr"

# Expressions
class Expr:
    pass

@dataclass
class Assign(Expr):
    name: str
    value: Expr

@dataclass
class IntLit(Expr):
    value: int

@dataclass
class Var(Expr):
    name: str

@dataclass
class Unary(Expr):
    op: str
    expr: Expr

@dataclass
class Binary(Expr):
    op: str
    left: Expr
    right: Expr

# print something here to debuggin purposes

# https://github.com/asottile/astpretty

def pretty(node, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(node, Program):
        inner = "\n".join(pretty(f, indent + 1) for f in node.functions)
        return f"{pad}Program\n{inner}"
    if isinstance(node, Function):
        inner = pretty(node.body, indent + 1)
        return f"{pad}Function name={node.name}\n{inner}"
    if isinstance(node, Block):
        if not node.items:
            return f"{pad}Block (empty)"
        inner = "\n".join(pretty(it, indent + 1) for it in node.items)
        return f"{pad}Block\n{inner}"
    # Fallback for now
    return f"{pad}{node.__class__.__name__}({node})"
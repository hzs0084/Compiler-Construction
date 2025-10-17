from dataclasses import dataclass
from typing import List, Union, Optional

@dataclass
class Program:
    functions: List["Function"]

@dataclass
class Function:
    name: str
    body: "Block"

    # helpers for symbol table
    start_line: int
    start_col: int
    end_line: int
    end_col: int

# Statements
class Stmt: 
    pass

@dataclass
class Block:
    items: List[Union["VarDecl","Stmt"]]

@dataclass
class VarDecl:
    names: List[str]     # e.g., ['x', 'y']

@dataclass
class ExprStmt(Stmt):
    expr: "Expr"

@dataclass
class Return(Stmt):
    expr: "Expr"

@dataclass
class If(Stmt):
    cond: "Expr"
    then_branch: "Block"
    else_branch: Optional["Block"] = None  #None if there's no else branch in the loop

@dataclass
class While(Stmt):
    cond: "Expr"
    body: "Block"

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
        return f"{pad}Program\n" + "\n".join(pretty(f, indent+1) for f in node.functions)
    if isinstance(node, Function):
        return f"{pad}Function name={node.name}\n" + pretty(node.body, indent+1)
    if isinstance(node, Block):
        if not node.items: return f"{pad}Block (empty)"
        return f"{pad}Block\n" + "\n".join(pretty(it, indent+1) for it in node.items)
    if isinstance(node, VarDecl):
        return f"{pad}VarDecl names={node.names}"
    if isinstance(node, If):
        out = f"{pad}If\n{pretty(node.cond, indent+1)}\n{pretty(node.then_branch, indent+1)}"
        if node.else_branch:
            out += "\n" + pretty(node.else_branch, indent+1)
        return out
    if isinstance(node, While):
        return f"{pad}While\n{pretty(node.cond, indent+1)}\n{pretty(node.body, indent+1)}"
    if isinstance(node, Return):
        return f"{pad}Return\n{pretty(node.expr, indent+1)}"
    if isinstance(node, ExprStmt):
        return f"{pad}ExprStmt\n{pretty(node.expr, indent+1)}"
    if isinstance(node, Assign):
        return f"{pad}Assign {node.name}\n{pretty(node.value, indent+1)}"
    if isinstance(node, Binary):
        return f"{pad}Binary '{node.op}'\n{pretty(node.left, indent+1)}\n{pretty(node.right, indent+1)}"
    if isinstance(node, Unary):
        return f"{pad}Unary '{node.op}'\n{pretty(node.expr, indent+1)}"
    if isinstance(node, Var):
        return f"{pad}Var {node.name}"
    if isinstance(node, IntLit):
        return f"{pad}IntLit {node.value}"
    return f"{pad}{node.__class__.__name__}"

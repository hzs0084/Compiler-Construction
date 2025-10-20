from typing import *
import abstract_syntax_tree as AST
from errors import SemanticError

class Scope:
    def __init__(self, parent: Optional["Scope"] = None):
        self.parent = parent
        self.names: Dict[str, str] = {}    #name -> type string for example "int"

    def declare(self, name:str, typ:str):
        if name in self.names:
            raise SemanticError(f"redeclaraion of '{name}' in the same scope")
        
        self.names[name] = typ

    def lookup(self, name:str) -> Optional[str]:
        s: Optional[Scope] = self
        while s is not None:
            if name in s.names:
                return s.names[name]
            s = s.parent
        return None

def analyze(program: AST.Program) -> None:

    # do one top level check per function so that each has its own scope

    for fn in program.functions:
        analyze_function(fn)


def analyze_function(fn: AST.Function) -> None:

    # Function body scope
    analyze_block(fn.body, Scope())

def analyze_block(block: AST.Block, scope: Scope) -> None:

    # Enter a new nested scope for this block

    inner = Scope(scope)

    for item in block.items:
        if isinstance(item, AST.VarDecl):
            # declare each name in current block scope
            # Vardecl posistions are here but not required

            for name in item.names:
                inner.declare(name, "int")

        elif isinstance(item, AST.Block):
            analyze_block(item, inner)

        elif isinstance(item, AST.Stmt):
            analyze_stmt(item, inner)

        else:
            # unknow type and can ignore for now
            pass

def analyze_stmt(stmt: AST.Stmt, scope: Scope) -> None:
    from abstract_syntax_tree import Return, ExprStmt, If, While, Block
    if isinstance(stmt, Return):
        analyze_expr(stmt.expr, scope)
    elif isinstance(stmt, ExprStmt):
        analyze_expr(stmt.expr, scope)
    elif isinstance(stmt, Block):
        analyze_block(stmt, scope)
    elif isinstance(stmt, If):
        # condition
        analyze_expr(stmt.cond, scope)
        # then
        analyze_block(stmt.then_branch, scope)
        # else
        if stmt.else_branch:
            analyze_block(stmt.else_branch, scope)
    elif isinstance(stmt, While):
        analyze_expr(stmt.cond, scope)
        analyze_block(stmt.body, scope)
    else:
        # Future statements
        pass


def analyze_expr(expr: AST.Expr, scope: Scope) -> str:
    # Returns the expression type as a string ("int" for our subset)
    from abstract_syntax_tree import IntLit, Var, Unary, Binary, Assign
    if isinstance(expr, IntLit):
        return "int"
    if isinstance(expr, Var):
        typ = scope.lookup(expr.name)
        if typ is None:
            # later add positions to Var, mention (line,col) here
            raise SemanticError(f"use of undeclared identifier '{expr.name}'")
        return typ
    if isinstance(expr, Unary):
        _ = analyze_expr(expr.expr, scope)
        return "int"
    if isinstance(expr, Binary):
        _ = analyze_expr(expr.left, scope)
        _ = analyze_expr(expr.right, scope)
        return "int"
    if isinstance(expr, Assign):
        # LHS must bealready declared (in current or any outer scope)
        typ = scope.lookup(expr.name)
        if typ is None:
            raise SemanticError(f"assignment to undeclared identifier '{expr.name}'")
        _ = analyze_expr(expr.value, scope)
        return "int"
    raise SemanticError(f"unknown expression node: {expr.__class__.__name__}")

# This allows shadowing: a name declared in an inner block can have the same name as an outer one (typical C behavior).

# It enforces “declare before use” naturally so that items are traversed in order.

# Ref: https://stackoverflow.com/questions/67555064/typeerror-specialgenericalias-object-does-not-support-item-assignment
"""
https://stackoverflow.com/questions/5893163/what-is-the-purpose-of-the-single-underscore-variable-in-python

"""

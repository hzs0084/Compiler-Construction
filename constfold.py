# constfold.py
from dataclasses import replace
from typing import Tuple
import abstract_syntax_tree as AST

# ----- helpers -----
def _is_const(e: AST.Expr) -> bool:
    return isinstance(e, AST.IntLit)

def _val(e: AST.Expr) -> int:
    assert isinstance(e, AST.IntLit)
    return e.value

def _as_bool(v: int) -> int:
    return 1 if v != 0 else 0

# returns a (possibly) new Expr (folded)
def fold_expr(e: AST.Expr) -> AST.Expr:
    from abstract_syntax_tree import IntLit, Var, Unary, Binary, Assign
    if isinstance(e, IntLit) or isinstance(e, Var):
        return e

    if isinstance(e, Unary):
        ee = fold_expr(e.expr)
        if isinstance(ee, IntLit):
            if e.op == "+":
                return ee
            if e.op == "-":
                return IntLit(-ee.value)
            if e.op == "!":
                return IntLit(_as_bool(0 if ee.value else 1))  # logically: !x -> 1 if x==0 else 0
        return replace(e, expr=ee)

    if isinstance(e, Binary):
        left = fold_expr(e.left)

        # Short-circuit aware folding for || and &&
        if e.op == "||":
            if isinstance(left, IntLit):
                if _as_bool(left.value) == 1:
                    return IntLit(1)
                # left is false -> result is right-as-bool
                right = fold_expr(e.right)
                if isinstance(right, IntLit):
                    return IntLit(_as_bool(right.value))
                return replace(e, left=left, right=right)
            right = fold_expr(e.right)
            return replace(e, left=left, right=right)

        if e.op == "&&":
            if isinstance(left, IntLit):
                if _as_bool(left.value) == 0:
                    return IntLit(0)
                # left is true -> result is right-as-bool
                right = fold_expr(e.right)
                if isinstance(right, IntLit):
                    return IntLit(_as_bool(right.value))
                return replace(e, left=left, right=right)
            right = fold_expr(e.right)
            return replace(e, left=left, right=right)

        # Non-short-circuiting binary ops
        right = fold_expr(e.right)

        if isinstance(left, IntLit) and isinstance(right, IntLit):
            a, b = left.value, right.value
            if e.op == "+":  return IntLit(a + b)
            if e.op == "-":  return IntLit(a - b)
            if e.op == "*":  return IntLit(a * b)
            if e.op == "/":  return IntLit(a // b) if b != 0 else e
            if e.op == "%":  return IntLit(a %  b) if b != 0 else e
            if e.op == "!": return IntLit(1 if ee.value == 0 else 0)
            if e.op == "==": return IntLit(1 if a == b else 0)
            if e.op == "!=": return IntLit(1 if a != b else 0)
            if e.op == "<":  return IntLit(1 if a <  b else 0)
            if e.op == "<=": return IntLit(1 if a <= b else 0)
            if e.op == ">":  return IntLit(1 if a >  b else 0)
            if e.op == ">=": return IntLit(1 if a >= b else 0)

        return replace(e, left=left, right=right)

    if isinstance(e, Assign):
        # Fold RHS only; LHS is a name (we don't fold across assignments)
        rhs = fold_expr(e.value)
        return replace(e, value=rhs)

    # Future nodes: Call, etc.
    return e

# ----- statement & block folding -----
def fold_stmt(s: AST.Stmt) -> AST.Stmt:
    from abstract_syntax_tree import Return, ExprStmt, If, While, Block
    if isinstance(s, Return):
        return replace(s, expr=fold_expr(s.expr))
    if isinstance(s, ExprStmt):
        return replace(s, expr=fold_expr(s.expr))
    if isinstance(s, If):
        cond = fold_expr(s.cond)
        thenb = fold_block(s.then_branch)
        elseb = fold_block(s.else_branch) if s.else_branch else None
        return replace(s, cond=cond, then_branch=thenb, else_branch=elseb)
    if isinstance(s, While):
        cond = fold_expr(s.cond)
        body = fold_block(s.body)
        return replace(s, cond=cond, body=body)
    if isinstance(s, AST.Block):
        return fold_block(s)
    return s

def fold_block(b: AST.Block) -> AST.Block:
    new_items = []
    for item in b.items:
        if isinstance(item, AST.VarDecl):
            new_items.append(item)  # decls unchanged
        elif isinstance(item, AST.Stmt) or isinstance(item, AST.Block):
            new_items.append(fold_stmt(item))
        else:
            new_items.append(item)
    return replace(b, items=new_items)

def fold_program(p: AST.Program) -> AST.Program:
    new_funcs = []
    for fn in p.functions:
        new_body = fold_block(fn.body)
        new_funcs.append(replace(fn, body=new_body))
    return replace(p, functions=new_funcs)

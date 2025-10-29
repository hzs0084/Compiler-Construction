import re

# Regex for "dst = INT BINOP INT"
_BIN = re.compile(
    r'^\s*(?P<dst>[A-Za-z_]\w*)\s*=\s*'
    r'(?P<a>-?\d+)\s*'
    r'(?P<op>\+|-|\*|/|%|==|!=|<=|<|>=|>|&&|\|\|)\s*'
    r'(?P<b>-?\d+)\s*$'
)

# Regex for "dst = UNOP INT"  (supports +, -, !)
_UN = re.compile(
    r'^\s*(?P<dst>[A-Za-z_]\w*)\s*=\s*'
    r'(?P<op>\+|-|!)\s*'
    r'(?P<a>-?\d+)\s*$'
)


def _fold_bin(a: int, op: str, b:int):

    # integer only semantics and return None to signal don't fold for example division by 0

    if op == '+': return a + b
    if op == '-' : return a - b
    if op == '*' : return a * b
    if op == '/' : return a // b if b!= 0 else None
    if op == '%' : return a % b if b != 0 else None
    if op == '==' : return 1 if a == b else 0
    if op == '!=' : return 1 if a != b else 0
    if op == '<'  : return 1 if a < b else 0
    if op == '<=' : return 1 if a <= b else 0
    if op == '>'  : return 1 if a > b else 0
    if op == '>=' : return 1 if a >= b else 0
    if op == '&&' : return 1 if (a != 0 and b != 0) else 0
    if op == '||' : return 1 if (a != 0 or b != 0)else 0

    return None

def _fold_un(op:str, a: int):

    if op == '+': return +a
    if op == '-': return -a
    if op == '!': return 0 if a else 1

    return None

def fold_tac(lines: list[str]) -> list[str]:

    """Return a new TAC list with simple constant expressions folded"""

    out: list[str] = []

    for ln in lines:
        m = _BIN.match(ln)
        if m:
            a = int(m.group('a'), 10)
            b = int(m.group('b'), 10)
            res = _fold_bin(a, m.group('op'), b)
            if res is not None:
                out.append(f"{m.group('dst')} = {res}")
                continue

        m = _UN.match(ln)
        if m:
            a = int(m.group('a'), 10)
            res = _fold_un(m.group('op'), a)
            if res is not None:
                out.append(f"{m.group('dst')} = {res}")
                continue
            out.append(ln)
    return out
    
def debug_diff(before: list[str], after: list[str]) -> str:
    """Just to show only changes lines side by side for quick eyeballing"""

    rows = []
    n = max(len(before), len(after))
    for i in range(n):
        b = before[i] if i < len(before) else ""
        a = after[i] if i < len(after) else ""

        if b != a:
            rows.append(f"-- {b}\n+ {a}")

    return "\n".join(rows)













def fold_binary(node):

    # only folds if BOTH children of the AST tree are already IntLit

    if not isinstance(node, AST.Binary):
        return node
    
    # evaluating two childern of left and right so

    L, R = node.left, node.right

    if is_int(L) and is_int(R):
        a, b = L.value, R.value
        op = node.op

        if op == "+": return AST.IntLit(a + b)
        if op == '-': return AST.IntLit(a - b)
        if op == '*': return AST.IntLit(a * b)
        if op == '/':
            if b != 0:
                return AST.IntLit(a // b)
            # skip divide-by-zero folding: keep original node
            return node
        if op == '%':
            if b != 0:
                return AST.IntLit(a % b)
            return node
        if op == '==': return AST.IntLit(1 if a == b else 0)
        if op == '!=': return AST.IntLit(1 if a != b else 0)
        if op == '<':  return AST.IntLit(1 if a <  b else 0)
        if op == '<=': return AST.IntLit(1 if a <= b else 0)
        if op == '>':  return AST.IntLit(1 if a >  b else 0)
        if op == '>=': return AST.IntLit(1 if a >= b else 0)
        if op == '&&': return AST.IntLit(1 if (a != 0 and b != 0) else 0)
        if op == '||': return AST.IntLit(1 if (a != 0 or  b != 0) else 0)
    return node
    
def fold_expr(expr):

    if isinstance(expr, AST.Unary):
        return fold_unary(expr)
    
    if isinstance(expr, AST.Binary):
        return fold_binary(expr)
    
    if isinstance(expr, AST.Assign):
        return AST.Assign(expr.name, expr.value)
    
    return expr


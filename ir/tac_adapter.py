# ir/tac_adapter.py
import re
from typing import List, Tuple
from ir.ir_types import *
from ir.pretty import dump_blocks

# TAC -> IR 

# LABEL: a standalone label line like "L0:" or "loop_start:"
_LABEL     = re.compile(r'^\s*(?P<lab>[A-Za-z_]\w*):\s*$')

# IFFALSE: conditional branch "ifFalse <cond> goto <Label>"
# - <cond> is a var or integer literal; target label in group 'L'
# - Example: "ifFalse t3 goto Lend"
_IFFALSE   = re.compile(r'^\s*ifFalse\s+(?P<cond>[A-Za-z_]\w*|-?\d+)\s+goto\s+(?P<L>[A-Za-z_]\w*)\s*$')

# GOTO: unconditional jump "goto <Label>"
# - Example: "goto L2"
_GOTO      = re.compile(r'^\s*goto\s+(?P<L>[A-Za-z_]\w*)\s*$')

# RETURN: function return "return <value>"
# - <value> is a var or integer literal
# - Example: "return t7" or "return 0"
_RETURN    = re.compile(r'^\s*return\s+(?P<v>[A-Za-z_]\w*|-?\d+)\s*$')


# ASSIGNBIN: binary op assignment "dst = a <op> b"
# - dst, a, b are vars or ints; <op> in {+,-,*,/,%,==,!=,<=,<,>=,>,&&,||}
# - Named groups: 'dst', 'a', 'op', 'b'
# - Example: "t1 = x + 7", "t2 = a && b", "t3 = i <= 10"
_ASSIGNBIN = re.compile(r'^\s*(?P<dst>[A-Za-z_]\w*)\s*=\s*(?P<a>[A-Za-z_]\w*|-?\d+)\s*(?P<op>\+|-|\*|/|%|==|!=|<=|<|>=|>|&&|\|\|)\s*(?P<b>[A-Za-z_]\w*|-?\d+)\s*$')


# ASSIGNUN: unary op assignment "dst = <op> a"
# - <op> in {+, -, !}; a is var or int
# - Example: "t0 = - x", "t1 = ! t0"
_ASSIGNUN  = re.compile(r'^\s*(?P<dst>[A-Za-z_]\w*)\s*=\s*(?P<op>\+|-|!)\s*(?P<a>[A-Za-z_]\w*|-?\d+)\s*$')

# ASSIGN: simple copy/const move "dst = src"
# - Covers both var-to-var and const-to-var moves
# - Example: "y = x", "x = 0"
_ASSIGN    = re.compile(r'^\s*(?P<dst>[A-Za-z_]\w*)\s*=\s*(?P<src>[A-Za-z_]\w*|-?\d+)\s*$')


# COMMENT: any line starting with '#' (including leading spaces)
# keep those so to re-emit function/decl comments in output
_COMMENT   = re.compile(r'^\s*#')   # keep to re-emit later


# DECLCMT: a '# decl …' comment line (declaration header)
_DECLCMT   = re.compile(r'^\s*#\s*decl\b')

FALLTHRU = "__FALLTHRU__"  # placeholder for ifFalse fallthrough


# Helper: turn a token string into an IR Value.
# Examples: "42" -> Const(42), "-7" -> Const(-7), "t3" -> Var("t3"), "x" -> Var("x")
def _val(tok: str) -> Value:
    return Const(int(tok)) if tok.lstrip('-').isdigit() else Var(tok)


"""
PRE:  tac_lines is a list of TAC strings (labels, ifFalse, goto, x=y, x=a+b, return v).
POST: Returns (linear_ir, header_comments). linear_ir is a list of IR Instr
      in source order and header_comments keeps top-of-function comments (# function, # decl).
NOTE: Uses simple regex patterns; unknown lines are ignored (adapter is forgiving).       `ifFalse cond goto L` is lowered to `br cond ? FALLTHRU : L` (builder resolves FALLTHRU).
"""

def tac_to_linear_ir(func_name: str, tac_lines: List[str]) -> Tuple[List[Instr], List[str]]:
    """Returns IR instructions and a list of header comment lines to preserve."""
    header_comments: List[str] = []
    ir: List[Instr] = []

    for ln in tac_lines:
        if _COMMENT.match(ln):
            # keep function/decl comments, ignore others
            header_comments.append(ln)
            continue

        m = _LABEL.match(ln)
        if m:
            ir.append(Instr(kind="label", label=m.group("lab"))); continue

        m = _IFFALSE.match(ln)
        if m:
            cond = _val(m.group("cond"))
            L    = m.group("L")
            # br cond ? fallthrough : L
            ir.append(Instr(kind="br", a=cond, tlabel=FALLTHRU, flabel=L))
            continue

        m = _GOTO.match(ln)
        if m:
            ir.append(Instr(kind="jmp", tlabel=m.group("L"))); continue

        m = _RETURN.match(ln)
        if m:
            ir.append(Instr(kind="ret", a=_val(m.group("v")))); continue

        m = _ASSIGNBIN.match(ln)
        if m:
            ir.append(Instr(kind="binop", dst=Var(m.group("dst")), op=m.group("op"),
                            a=_val(m.group("a")), b=_val(m.group("b"))))
            continue

        m = _ASSIGNUN.match(ln)
        if m:
            ir.append(Instr(kind="unop", dst=Var(m.group("dst")), op=m.group("op"),
                            a=_val(m.group("a"))))
            continue

        m = _ASSIGN.match(ln)
        if m:
            dst, src = m.group("dst"), m.group("src")
            ir.append(Instr(kind="mov", dst=Var(dst), a=_val(src)))
            continue

        # unknown line: ignore quietly or raise
        # print("[warn] unrecognized TAC:", ln) later for better error handling 

    return ir, header_comments

# IR -> TAC 

def _str_val(v: Value) -> str:
    return str(v.value) if isinstance(v, Const) else v.name

"""
PRE:  fn has well-formed blocks/terminators and header_comments are optional leading lines.
POST: Returns TAC-like strings for printing/debugging. One label per block is emitted.
"""
def ir_to_tac(fn: Function, header_comments: List[str]) -> List[str]:
    out: List[str] = []
    out.extend(header_comments)  # keep the "# function", "# decl ..." lines once
    seen_header = True

    for b in fn.blocks:
        # print the real label
        out.append(f"{b.label}:")
        for ins in b.instrs:
            if ins.kind == "label":
                # already emitted block label
                continue
            if ins.kind == "mov":
                out.append(f"{ins.dst.name} = {_str_val(ins.a)}")
            elif ins.kind == "binop":
                out.append(f"{ins.dst.name} = {_str_val(ins.a)} {ins.op} {_str_val(ins.b)}")
            elif ins.kind == "unop":
                out.append(f"{ins.dst.name} = {ins.op} {_str_val(ins.a)}")
            elif ins.kind == "br":
                # TAC is right now "ifFalse cond goto Lfalse"
                out.append(f"ifFalse {_str_val(ins.a)} goto {ins.flabel}")
            elif ins.kind == "jmp":
                out.append(f"goto {ins.tlabel}")
            elif ins.kind == "ret":
                out.append(f"return {_str_val(ins.a)}")
            else:
                # ignore
                pass
    return out

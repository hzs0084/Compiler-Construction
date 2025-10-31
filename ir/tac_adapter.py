# ir/tac_adapter.py
import re
from typing import List, Tuple
from ir.ir_types import *

# TAC -> IR 

_LABEL     = re.compile(r'^\s*(?P<lab>[A-Za-z_]\w*):\s*$')
_IFFALSE   = re.compile(r'^\s*ifFalse\s+(?P<cond>[A-Za-z_]\w*|-?\d+)\s+goto\s+(?P<L>[A-Za-z_]\w*)\s*$')
_GOTO      = re.compile(r'^\s*goto\s+(?P<L>[A-Za-z_]\w*)\s*$')
_RETURN    = re.compile(r'^\s*return\s+(?P<v>[A-Za-z_]\w*|-?\d+)\s*$')
_ASSIGNBIN = re.compile(r'^\s*(?P<dst>[A-Za-z_]\w*)\s*=\s*(?P<a>[A-Za-z_]\w*|-?\d+)\s*(?P<op>\+|-|\*|/|%|==|!=|<=|<|>=|>|&&|\|\|)\s*(?P<b>[A-Za-z_]\w*|-?\d+)\s*$')
_ASSIGNUN  = re.compile(r'^\s*(?P<dst>[A-Za-z_]\w*)\s*=\s*(?P<op>\+|-|!)\s*(?P<a>[A-Za-z_]\w*|-?\d+)\s*$')
_ASSIGN    = re.compile(r'^\s*(?P<dst>[A-Za-z_]\w*)\s*=\s*(?P<src>[A-Za-z_]\w*|-?\d+)\s*$')
_COMMENT   = re.compile(r'^\s*#')   # keep to re-emit later
_DECLCMT   = re.compile(r'^\s*#\s*decl\b')

FALLTHRU = "__FALLTHRU__"  # placeholder for ifFalse fallthrough

def _val(tok: str) -> Value:
    return Const(int(tok)) if tok.lstrip('-').isdigit() else Var(tok)

def tac_to_linear_ir(func_name: str, tac_lines: List[str]) -> Tuple[List[Instr], List[str]]:
    """Returns IR instructions and a list of header comment lines to preserve."""
    header_comments: List[str] = []
    ir: List[Instr] = []

    for ln in tac_lines:
        if _COMMENT.match(ln):
            # keep function/decl comments, ignore others if you want
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

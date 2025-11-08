# ir/pretty.py
from ir.ir_types import Function, Instr, Const, Var

def _sv(v):
    if v is None: return ""
    return str(v.value) if isinstance(v, Const) else v.name

def _line(ins: Instr) -> str:
    k = ins.kind
    if k == "label": return f"{ins.label}:"
    if k == "mov":   return f"{ins.dst.name} = {_sv(ins.a)}"
    if k == "binop": return f"{ins.dst.name} = {_sv(ins.a)} {ins.op} {_sv(ins.b)}"
    if k == "unop":  return f"{ins.dst.name} = {ins.op} {_sv(ins.a)}"
    if k == "br":    return f"br {_sv(ins.a)} ? {ins.tlabel} : {ins.flabel}"
    if k == "jmp":   return f"jmp {ins.tlabel}"
    if k == "ret":   return f"return {_sv(ins.a)}"
    return f";; {k}"  # fallback

def dump_blocks(fn: Function, show_cfg: bool = False) -> str:
    lines = [f"# function {fn.name} (IR blocks)"]
    for b in fn.blocks:
        lines.append(f"{b.label}:")
        for ins in b.instrs:
            if ins.kind == "label":
                continue  # we already print block labels
            lines.append(f"  {_line(ins)}")
        if show_cfg:
            succs = ", ".join(fn.succ.get(b.label, []))
            lines.append(f"  ;; succ: [{succs}]")
    return "\n".join(lines)

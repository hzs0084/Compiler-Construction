from ir.ir_types import *
def _is_c(x): return isinstance(x, Const)

def _bin(op,a,b):
    if op=="+":return a+b
    if op=="-":return a-b
    if op=="*":return a*b
    if op=="/":return a//b if b!=0 else None
    if op=="%":return a%b  if b!=0 else None
    if op=="==":return 1 if a==b else 0
    if op=="!=":return 1 if a!=b else 0
    if op=="<": return 1 if a<b  else 0
    if op=="<=":return 1 if a<=b else 0
    if op==">": return 1 if a>b  else 0
    if op==">=":return 1 if a>=b else 0
    if op=="&&":return 1 if (a!=0 and b!=0) else 0
    if op=="||":return 1 if (a!=0 or  b!=0) else 0
    return None

def _un(op,a):
    if op=="+": return +a
    if op=="-": return -a
    if op=="!": return 0 if a else 1
    return None


"""
PRE:  fn is block-structured. Some operands may already be Const via const-prop.
POST: Rewrites:
      - binop(Const,Const) -> mov dst, Const(result)
      - unop(Const)        -> mov dst, Const(result)
      - br(Const)          -> jmp taken_target
      Returns True if any rewrite occurred.
NOTE: Division/mod by zero are NOT folded.
"""

def const_fold_function(fn: Function) -> bool:
    changed=False
    for b in fn.blocks:
        new=[]
        for ins in b.instrs:
            if ins.kind=="binop" and _is_c(ins.a) and _is_c(ins.b):
                v=_bin(ins.op, ins.a.value, ins.b.value)
                if v is not None:
                    new.append(Instr(kind="mov", dst=ins.dst, a=Const(v))); changed=True; continue
            if ins.kind=="unop" and _is_c(ins.a):
                v=_un(ins.op, ins.a.value)
                if v is not None:
                    new.append(Instr(kind="mov", dst=ins.dst, a=Const(v))); changed=True; continue
            if ins.kind=="br" and _is_c(ins.a):
                target = ins.tlabel if ins.a.value!=0 else ins.flabel
                new.append(Instr(kind="jmp", tlabel=target)); changed=True; continue
            new.append(ins)
        b.instrs=new
    return changed

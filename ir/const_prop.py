from typing import Dict
from ir.ir_types import *

def _const_of(v: Value, env: Dict[str, Const]) -> Value:
    if isinstance(v, Var):
        c = env.get(v.name)
        return c if c is not None else v
    return v # already constant

def const_propagate_function(fn: Function) -> bool:
    changed = False
    for b in fn.blocks: # 
        env: Dict[str, Const] = {}
        new: list[Instr] = []

        for ins in b.instrs:
            k = ins.kind
            if k == "mov":
                a = _const_of(ins.a, env)
                # update the line if substituition was performed
                if a is not ins.a:
                    ins = Instr(kind="mov", dst = ins.dst, a = a)
                    changed = True
                # track constant binding if RHS is Const
                if isinstance(ins.dst, Var):
                    if isinstance(a, Const):
                        env[ins.dst.name] = a
                    else:
                        env.pop(ins.dst.name, None)
                new.append(ins)

            elif k == "binop":
                a = _const_of(ins.a, env)
                bval = _const_of(ins.b, env)
                if a is not ins.a or bval is not ins.b:
                    ins = Instr(kind = "binop", dst = ins.dst, op = ins.op, a = a, b = bval)
                    changed = True

                # def kills const binding unless folded later

                if isinstance(ins.dst, Var):
                    env.pop(ins.dst.name, None)
                new.append(ins)

            elif k == "unop":
                a = _const_of(ins.a, env)
                if a is not ins.a:
                    ins = Instr(kind = "unop", dst = ins.dst, op = ins.op, a = a)
                    changed = True

                if isinstance(ins.dst, Var):
                    env.pop(ins.dst.name, None)
                new.append(ins)

            elif k == "br":
                a = _const_of(ins.a, env)
                if a is not ins.a:
                    ins = Instr(kind = "br", a = a, tlabel = ins.tlabel, flabel = ins.flabel)
                    changed = True
                new.append(ins)

            elif k in {"jmp", "ret"}:
                # barrier: clear env to stay local and safe

                if k == "ret" and ins.a is not None:
                    a = _const_of(ins.a, env)

                    if a is not ins.a:
                        ins = Instr(kind = "ret", a = a)
                        changed = True
                new.append(ins)

                env.clear()

            else:

                new.append(ins)

        b.instrs = new
    
    return changed
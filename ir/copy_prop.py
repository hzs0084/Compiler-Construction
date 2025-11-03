from  typing import Dict, List
from ir.ir_types import Instr, Var, Const, Function

def _root(v: Var, env: Dict[str, str]) -> Var:
    # Followw chains x -> y -> z to the end

    name  = v.name
    seen = set()
    while name in env and name not in seen:
        seen.add(name)
        name = env[name]
    return Var(name)

def _subst_val(val, env: Dict[str, str]):
    if isinstance(val, Var):
        return _root(val, env)
    return val  # Const or None

def _kill(env: Dict[str, str], dst_name: str):
    # kill dst's own mapping and any mapping that points to dst
    env.pop(dst_name, None)
    to_del = [k for k, v in env.items() if v == dst_name]
    for k in to_del:
        env.pop(k, None)

def copy_propagate_function(fn: Function) -> bool:
    changed = False
    for b in fn.blocks:
        env: Dict[str, str] = {}  # var -> alias var
        new: List[Instr] = []
        for ins in b.instrs:
            k = ins.kind

            if k == "mov":
                # y = x  -> record alias; y = 5 -> not copy-prop
                if isinstance(ins.a, Var) and isinstance(ins.dst, Var):
                    a = _subst_val(ins.a, env)  # compress chains
                    if a.name != ins.a.name:
                        ins = Instr(kind="mov", dst=ins.dst, a=a)
                        changed = True
                    _kill(env, ins.dst.name)
                    env[ins.dst.name] = a.name
                else:
                    # y = Const -> kill aliases of y
                    if isinstance(ins.dst, Var):
                        _kill(env, ins.dst.name)
                new.append(ins)

            elif k == "binop":
                a = _subst_val(ins.a, env)
                bval = _subst_val(ins.b, env)
                if a is not ins.a or bval is not ins.b:
                    ins = Instr(kind="binop", dst=ins.dst, op=ins.op, a=a, b=bval)
                    changed = True
                if isinstance(ins.dst, Var):
                    _kill(env, ins.dst.name)
                new.append(ins)

            elif k == "unop":
                a = _subst_val(ins.a, env)
                if a is not ins.a:
                    ins = Instr(kind="unop", dst=ins.dst, op=ins.op, a=a)
                    changed = True
                if isinstance(ins.dst, Var):
                    _kill(env, ins.dst.name)
                new.append(ins)

            elif k == "br":
                a = _subst_val(ins.a, env)
                if a is not ins.a:
                    ins = Instr(kind="br", a=a, tlabel=ins.tlabel, flabel=ins.flabel)
                    changed = True
                new.append(ins)
                env.clear()  # barrier

            elif k == "jmp":
                new.append(ins)
                env.clear()  # barrier

            elif k == "ret":
                a = _subst_val(ins.a, env)
                if a is not ins.a:
                    ins = Instr(kind="ret", a=a)
                    changed = True
                new.append(ins)
                env.clear()  # barrier

            else:
                new.append(ins)

        b.instrs = new
    return changed


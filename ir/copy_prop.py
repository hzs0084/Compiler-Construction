from typing import Dict, List
from ir.ir_types import Instr, Var, Const, Function

# Follow alias chain x->y->z; stop on cycles.
# Follow alias chain x->y->z; stop on cycles; compress path on the way back.
def _root(v: Var, env: Dict[str, str]) -> Var:
    name = v.name
    seen: list[str] = []
    steps = 0
    MAX_STEPS = max(32, len(env) + 1)  # dynamic safety cap

    while name in env:
        nxt = env[name]
        if nxt == name or name in seen:                   # self-alias, trivial root
            break                                         # cycle detected (a->...->a)
        seen.append(name)
        name = nxt
        steps += 1
        if steps > MAX_STEPS:             # pathological chain guard
            break

    # Path compression: flatten x->y->...->root to x->root for all seen
    for s in seen:
        env[s] = name
    return Var(name)

def _subst_val(val, env: Dict[str, str]):
    return _root(val, env) if isinstance(val, Var) else val

# Kill dst's mapping and any aliases pointing to dst (break chains).
def _kill(env: Dict[str, str], dst_name: str):
    env.pop(dst_name, None)  # remove dst -> ?
    for k, v in list(env.items()):  # remove ? -> dst
        if v == dst_name:
            env.pop(k, None)

def _same_val(v1, v2) -> bool:
    if v1 is v2:
        return True
    if type(v1) is not type(v2):
        return False
    # Var/Const structural equality
    if isinstance(v1, Var):
        return v1.name == v2.name
    if isinstance(v1, Const):
        return v1.value == v2.value
    return False

def copy_propagate_function(fn: Function) -> bool:
    """
    PRE:  fn has valid blocks/CFG. Instructions include mov/binop/unop/br/jmp/ret.
    POST: Local (per-block) copy propagation:
        - Tracks y = x aliases; substitutes uses (compress chains)
        - Kills aliases on redefinition and reverse-links to the redefined var
        - Clears env on br/jmp/ret barriers
    RET : True if any substitution occurred.
    """
    changed = False
    for b in fn.blocks:
        env: Dict[str, str] = {}   # var -> alias var
        new: List[Instr] = []
        for ins in b.instrs:
            if len(env) > 5000:
                raise RuntimeError(f"[copyprop] env too large ({len(env)}); possible alias leak")

            k = ins.kind

            if k == "mov":
                src = _subst_val(ins.a, env)

                # changed only if the *value* differs, not just the object
                if not _same_val(src, ins.a):
                    ins = Instr(kind="mov", dst=ins.dst, a=src)
                    changed = True

                # kill knowledge about dst
                if isinstance(ins.dst, Var):
                    _kill(env, ins.dst.name)

                # record alias only for var->var and not self
                if isinstance(src, Var) and isinstance(ins.dst, Var) and src.name != ins.dst.name:
                    if env.get(src.name) == ins.dst.name:   # break 2-cycle
                        env.pop(src.name, None)
                    env[ins.dst.name] = src.name

                new.append(ins)

            elif k == "binop":
                a = _subst_val(ins.a, env)
                bval = _subst_val(ins.b, env)
                if not _same_val(a, ins.a) or not _same_val(bval, ins.b):
                    ins = Instr(kind="binop", dst=ins.dst, op=ins.op, a=a, b=bval)
                    changed = True
                if isinstance(ins.dst, Var):
                    _kill(env, ins.dst.name)
                new.append(ins)

            elif k == "unop":
                a = _subst_val(ins.a, env)
                if not _same_val(a, ins.a):
                    ins = Instr(kind="unop", dst=ins.dst, op=ins.op, a=a)
                    changed = True
                if isinstance(ins.dst, Var):
                    _kill(env, ins.dst.name)
                new.append(ins)

            elif k == "br":
                a = _subst_val(ins.a, env)
                if not _same_val(a, ins.a):
                    ins = Instr(kind="br", a=a, tlabel=ins.tlabel, flabel=ins.flabel)
                    changed = True
                new.append(ins)
                env.clear()

            elif k == "ret":
                a = _subst_val(ins.a, env)
                if not _same_val(a, ins.a):
                    ins = Instr(kind="ret", a=a)
                    changed = True
                new.append(ins)
                env.clear()

            else:
                new.append(ins)


        b.instrs = new
    return changed
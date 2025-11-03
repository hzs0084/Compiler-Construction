from ir.ir_types import Instr, Var, Const, Function

def _is_const0(v): return isinstance(v, Const) and v.value == 0
def _is_const1(v): return isinstance(v, Const) and v.value == 1

def algebra_simplify_function(fn: Function) -> bool:
    changed = False

    for b in fn.blocks:
        out = []
        for ins in b.instrs:
            if ins.kind == "binop" and isinstance(ins.dst, Var):
                op, a, c = ins.op, ins.a, ins.b


                # x + 0 / 0 + x

                if op == "+":
                    if _is_const0(c) and isinstance(a, (Var, Const)):
                        out.append(Instr(kind="mov", dst=ins.dst, a=a))
                        changed = True
                        continue
                
                # x - 0

                if op == "-" and _is_const0(c) and isinstance(a, (Var, Const)):
                        out.append(Instr(kind="mov", dst=ins.dst, a=a))
                        changed = True
                        continue
                
                # x * 1 / 1 * x / x * 0 / 0 * x

                if op == "*":
                    if _is_const1(c) and isinstance(a, (Var, Const)):
                        out.append(Instr(kind="mov", dst=ins.dst, a=a))
                        changed = True
                        continue

                    if _is_const1(c) and isinstance(a, (Var, Const)):
                        out.append(Instr(kind="mov", dst=ins.dst, a=a))
                        changed = True
                        continue


                    if _is_const1(c):
                        out.append(Instr(kind="mov", dst=ins.dst, a=Const(0)))
                        changed = True
                        continue


                    if _is_const1(c):
                        out.append(Instr(kind="mov", dst=ins.dst, a=Const(0)))
                        changed = True
                        continue


                # x / 1

                if op == "/" and _is_const1(c) and isinstance(a, (Var, Const)):
                    out.append(Instr(kind="mov", dst=ins.dst, a=a))
                    changed = True
                    continue

            out.append(ins)

        b.instrs = out

    return changed


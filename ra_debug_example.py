# ra_debug_example.py
#
# Tiny hand-written pseudo-x86 program so can step through RA.
# This matches the example've been talking about:
#
#   L0:
#     mov R1, [a]
#     mov R2, [b]
#     add R1, R2
#     mov RAX, R1
#     ret
#
# don't care about real [rbp-8] etc here, just that R1/R2/RAX are vregs.

from codegen.x86ir import Reg, Mem, Mov, Add, Label, LabelDef, Ret
from codegen.ra import liveness, build_igraph, allocate_registers_on_program
from codegen.x86ir import Program  # still useful as a *type*, not a constructor

def make_example_program() -> Program:
    # Program is just "list[Instr]" – so build a normal list.
    p: Program = [
        LabelDef(Label("L0")),          # 0
        Mov(Reg("R1"), Mem("a")),       # 1: R1 = [a]
        Mov(Reg("R2"), Mem("b")),       # 2: R2 = [b]
        Add(Reg("R1"), Reg("R2")),      # 3: R1 = R1 + R2
        Mov(Reg("RAX"), Reg("R1")),     # 4: RAX = R1
        Ret(),                          # 5: ret
    ]
    return p

def main():
    p = make_example_program()

    print("=== Original program ===")
    for i, ins in enumerate(p):
        print(f"{i:2}: {ins}")

    # 1) Liveness
    IN, OUT, R, W = liveness(p)

    print("\n=== Liveness (R/W/IN/OUT) ===")
    for i, ins in enumerate(p):
        print(f"{i:2}: {ins}")
        print(f"      R   = {R[i]}")
        print(f"      W   = {W[i]}")
        print(f"      IN  = {IN[i]}")
        print(f"      OUT = {OUT[i]}")

    # 2) Interference graph
    G = build_igraph(p, IN, OUT, R, W)

    print("\n=== Interference graph ===")
    for v, nbrs in G.items():
        print(f"  {v} -> {sorted(nbrs)}")

    # 3) Allocate registers
    p2 = allocate_registers_on_program(p)

    print("\n=== After RA (physical regs + spills) ===")
    for i, ins in enumerate(p2):
        print(f"{i:2}: {ins}")

if __name__ == "__main__":
    main()
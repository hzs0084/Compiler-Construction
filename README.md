
---


# Tiny C Compiler – COMP 6210

A semester-long project implementing a tiny compiler in Python for a restricted subset of C.

The compiler goes from **source C** all the way to **optimized IR** and **Intel-style pseudo-x86 assembly** with optional register allocation and stack frames.

---

## 1. Features

- **Front end**
  - Hand-written lexer (`lexer.py`)
  - Recursive-descent parser (`parser.py`)
  - Typed AST (`abstract_syntax_tree.py`)
  - Semantic analysis with nested scopes and symbol tables (`semantic.py`)

- **Intermediate representations**
  - Human-readable three-address code (TAC) (`tac.py`)
  - Internal IR with `Instr`/`Block`/`Function` (`ir/`)

- **Optimizations (IR level)**
  - Constant propagation
  - Constant folding
  - Unreachable code elimination
  - Dead store elimination
  - Copy propagation
  - Simple algebraic simplifications

- **Code generation**
  - Pseudo-x86 IR (`codegen/x86ir.py`)
  - Lowering from IR to pseudo-x86 (`codegen/pseudo_x86.py`)
  - Optional stack frames for locals
  - Graph-coloring register allocation and spilling (`codegen/ra.py`)

- **Debugging / inspection**
  - Dump tokens, AST, symbol tables, TAC, IR blocks, and CFG
  - Run individual optimization passes and trace them one by one

---

## 2. Language Subset

- Only `int` type (for both variables and function return).
- No function parameters and no function calls (yet).
- Statements:
  - Variable declarations: `int x;`, `int x, y;`
  - `if` / `if-else`
  - `while`
  - `return expr;`
  - Expression statements: `x = x + 1;`
- Expressions:
  - Binary: `+`, `-`, `*`, `/`, `%`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `&&`, `||`
  - Unary: `!`, unary `-`, unary `+`
  - Parentheses, variables, integer literals

Modulo `%` is accepted syntactically but not fully supported in codegen yet.

---

## 3. Project Layout

- `compiler.py` – **main CLI entry point**
- `lexer.py` – tokenization
- `parser.py` – recursive-descent parser
- `abstract_syntax_tree.py` – AST node definitions
- `semantic.py` – scopes, symbol tables, semantic checks
- `errors.py` – custom `LexerError`, `ParserError`, `SemanticError`

IR and optimization:

- `tac.py` – TAC generation from AST
- `ir/ir_types.py` – internal IR value and instruction types
- `ir/tac_adapter.py` – TAC ↔ IR conversion
- `ir/builder.py` – basic block & CFG builder
- `ir/pretty.py` – IR / CFG printing utilities
- `ir/const_prop.py`, `ir/const_fold.py`, `ir/dce.py`,
  `ir/fuse.py`, `ir/copy_prop.py`, `ir/algebra.py` – optimization passes
- `ir/pipeline.py` – `optimize_function(fn, opt_level)`
- `ir/passes.py` – named pass mapping + `run_passes(...)`

Code generation:

- `codegen/x86ir.py` – pseudo-x86 dataclasses + printer
- `codegen/pseudo_x86.py` – IR → pseudo-x86 lowering, frame layout, prologue/epilogue
- `codegen/ra.py` – liveness, interference graph, greedy coloring, spilling

Tests:

- `tests/lexer_output_testing/`
- `tests/parser/{valid,invalid}/`
- `tests/semantic/{valid,invalid}/`
- `tests/tac_test/`
- `tests/optimization/*`
- `tests/codegen-x86/`

---

## 4. Usage

From the project root:

```bash
python3 compiler.py [options] input.c
```

### 4.1 Front-end and TAC

```bash
# Just lex the file and print tokens
python3 compiler.py -l input.c

# Parse and pretty-print the AST
python3 compiler.py -p input.c

# Run semantic analysis (will exit on error)
python3 compiler.py -s input.c

# Print function symbol tables
python3 compiler.py --symtab input.c

# Generate TAC (no optimization)
python3 compiler.py --tac input.c
```

### 4.2 Optimization Controls

```bash
# Use built-in optimization pipeline at level 1+
python3 compiler.py -O1 --tac input.c
python3 compiler.py -O2 --tac input.c
python3 compiler.py -O3 --tac input.c

# Quick alias: enable constant folding (treated like -O1+)
python3 compiler.py --constfold --tac input.c

# Manually choose passes (order matters)
python3 compiler.py --passes constprop,constfold,dse,copyprop,algebra --tac input.c

# Trace IR after each named pass
python3 compiler.py --passes constprop,constfold --trace-passes --tac input.c
```

Available pass names (for `--passes`):
    - `constprop`
    - `constfold`
    - `drop_unreachable`
    - `dse`
    - `copyprop`
    - `algebra`

### 4.3 IR / CFG Debugging

```bash
# Dump basic blocks after CFG construction
python3 compiler.py --tac --dump-blocks input.c

# Also show CFG successors along with each block
python3 compiler.py --tac --dump-blocks --dump-cfg input.c

# Show blocks after the optimization pipeline
python3 compiler.py --tac -O2 --dump-blocks-after input.c
```

## 5 Pseudo-x86 Output and Register Allocation

To lower to Intel-style pseudo-x86L

```bash
# Simple pseudo-x86 (virtual registers, no stack frame)
python3 compiler.py --emit-pseudo-x86 input.c

# Pseudo-x86 with stack frame for locals (rbp/rsp based)
python3 compiler.py --emit-pseudo-x86 --frame stack input.c

# Pseudo-x86 + stack frame + register allocation
python3 compiler.py --emit-pseudo-x86 --frame stack --ra input.c
```

Notes:
- `--emit-pseudo-x86` prints a minimal function header followed by instructions:
    - `function main`
    - `push rbp`, `mov rbp, rsp`, etc. when `--frame stack` is used. 

- Temporaries are lowered into virtual registers R1, R2, ... <br>
With `--ra` these are replaced by caller-saved x86 registers, with spills stored on the stack. 


## 6. Examples

```bash
# Basic TAC with optimizations
python3 compiler.py -O2 --tac tests/optimization/ir_unreach/nested_if_const.c

# Visualize CFG before and after optimization
python3 compiler.py --tac --dump-blocks tests/optimization/ir_unreach/nested_if_const.c
python3 compiler.py -O2 --tac --dump-blocks-after tests/optimization/ir_unreach/nested_if_const.c

# Compare TAC vs pseudo-x86
python3 compiler.py -O2 --tac tests/codegen-x86/simple.c
python3 compiler.py -O2 --emit-pseudo-x86 --frame stack --ra tests/codegen-x86/simple.c
```

## 7. Limitations / Future Work

    - No function parameters or calls yet
    - No arrays, pointers, or structs. 
    - % is not wired all the way through code generation.
    - No real assembler or linker and output is pseudo-x86 and direct execution. 


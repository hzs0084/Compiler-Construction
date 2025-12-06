## 0. Project Metadata
**Author:** Hemant Sherawat  
**Course:** COMP 6210 — Compiler Construction  
**Project:** Tiny C Compiler (Python-based)
**Project Timeline:** 
<ol>
  <li>Sep 11 - Lexar</li>
  <li>Oct 02 - Parser</li>
  <li>Oct 16 - Three Addr Code</li>
  <li>Oct 30 - Optimization</li>
  <li>Nov 13 - Low-Level IR / x86 Assembly</li>
  <li>Dec 04 - Register Allocation</li>
</ol>

**Goal:** Build a compiler for a small subset of C that:
- lexes and parses the source program
- builds an AST and runs semantic checks/ scopr resolution
- lowers to three-address code (TAC)
- converts TAC to an internal IT with basic blocks + CFG
- runs a small suite of optimization pases
- emits Intel-style pseudo with optional register allocation and stack frames


## 1. High-Level Overview

The current end-to-end pipeline:


1. **Lexing** (`lexer.py`)
   - Input: tokens  
   - Output: token stream

2. **Parsing** (`parser.py`)
   - Input: tokens
   - Output: AST for the entire program

3. **Semantic Analysis** (`semantic.py`) 
   - Builds symbol tables using a 'Scope' hierarchy
   - Checks redeclarations, use-before-declare, and block scoping
   - Treats each function as its own top-level scope with nested block scopes

4. **TAC (external IR)** (`tac.py`)
   - Lowers the AST to human-readable three-address code 
   - TAC is the "user-facing" IR (what CLI shows with --tac)

5. **TAC → Internal IR** (`ir/tac_adapter.py`)
   - Parses TAC lines into `Instr` objects  (`ir/ir_types.py`)
   - Produces a linear list of instructions per function

6. **Basic Blocks & CFG** (`ir/builder.py`)
   - Splits the linear IR into basic blocks
   - Builds a control-flow graph (sucessors and predecessors)
   - Ensures each block has exactly one terminator (`br`, `jmp`, or `ret`) 

7. **IR Optimizations** (`ir/pipeline.py`) / (`ir/passes.py`) 
   - Constant Propagation
   - Constant Folding 
   - Dead Code Elimination: unreachable + dead store 
   - Copy Propagation
   - Simple Algebraic Simplification

8. **Pseuco-x86 Codegen**: `codegen/pseudo_x86.py`, `codegen/x86ir.py`
   - Lowers IR to a pseudo-x86 instruction stream (Intel-style, 2-operand)
   - Uses virtual registers (`R1`, `R2`, `R3`, ...)

9. **Register Allocation (RA)**: `codegen/ra.py`
   - Performs liveness analysis and graph-coloring RA on virtual registers
   - Rewrites spilled temps to stack slots
   - Integrates with frame layout when `--frame stack` and `--ra` are enabled


---

## 2. Language Subset

### 2.1 Lexical elements (tokens)

- **Keywords:** `int`, `return`, `if`, `else`, `while`
- **Identifiers:** `[a-zA-Z_][a-zA-Z0-9_]*`
- **Integer literals:** base-10 nonnegative integers
- **Operators:** `+ - * / % ! = == != < <= > >= && ||`
- **Punctuation:** `; , ( ) { }`
- **Whitespace/comments:** ignored (optionally support `// ...` if desired)

### 2.2 Grammar (EBNF-style)

Using: `{X}` = zero or more; `[X]` = optional; `|` = choice; parentheses for grouping.


### Program & Functions

Program -> FunctionList <br>
FunctionList -> Function | Function FunctionList <br>
Function -> Type ID "(" ")" Block <br><br>
Type     -> int <br>


Block -> "{" ItemList "}" <br>
ItemList -> ε | Item ItemList <br>
Item -> Declaration | Statement <br><br>
Declaration -> Type ID { "," ID } ";" <br>
Statement      ->  ReturnStmt
               | IfStmt
               | WhileStmt
               | ExprStmt
               | Block <br>

ReturnStmt     ->  "return" Expression ";" <br>
IfStmt         ->  "if" "(" Expression ")" Block [ "else" Block ]<br>
WhileStmt      ->  "while" "(" Expression ")" Block<br>
ExprStmt       ->  Expression ";"<br>

Expression     -> Assignment <br>
Assignment     -> ID "=" Assignment 
               | LogicalOr <br>

LogicalOr      -> LogicalAnd { "||" LogicalAnd } <br>
LogicalAnd     -> Equality   { "&&" Equality } <br>
Equality       -> Relational { ("==" | "!=") Relational } <br>
Relational     -> Additive   { ("<" | "<=" | ">" | ">=") Additive } <br>
Additive       -> Multiplicative { ("+" | "-") Multiplicative } <br>
Multiplicative -> Unary { ("*" | "/" | "%") Unary }<br>
Unary          -> ("!" | "-" | "+") Unary | Primary<br>
Primary        -> "(" Expression ")" | ID | num<br>

Notes:
- Only `int` type is supported (functions and variables).
- Function have no parameters and return int.
- No function calls, arrays, pointers, or structs
- `%` exists syntactically but is not supported end-to-end in codegen (by design).



## 3. Parser & AST

### 3.1 Parser

- A recurisive-descent parse with small helpers:
   - `_current()`, `_check(kind, [text])`, `_match(kind, [text])`, `_expect(kind, [text], msg)`
- Produces AST nodes from `abstract_syntac_tree.py`.
- On failure, raises `ParserError` with a message, line, and column.

### 3.2 AST Structure

Key Node types (simplified)

- `Program(functions: List[Function])`  
- `Function(name: str, body: Block, start_line/col, end_line/col)`  
- `Block(items: List[DeclOrStmt])`
- `VarDecl(names: List[str], positions: List[(line, col)])`

Statement nodes:
- `ExprStmt(expr)`
- `Return(expr)`  
- `If(cond, then_branch, else_branch?)`  
- `While(cond, body)`  

Expressions:
- `IntLit(value)`  
- `Var(name)`  
- `Unary(op, expr)`  
- `Binary(op, left, right)`  
- `Assign(name, value)`  // right-assoc semantics

The AST is deliberately minimal and well-typed to make later stages simpler.

---

## 4. Semantic Analysis

### 4.1 Scope Representation (`semantic.py`)

- `Scope` objects form a linked tree:
   - `Scope.parent` points to the enclosing scope
   - `Scope.names: Dict[str, str]` maps identifiers to type strings (e.g., `"x" -> "int"`)

### 4.2 Checks Performed

-  **Function Symbols**: top-level pass over `Program` to record all function names.
- **Variable declaraions**: 
   - Rejects redeclarations within the same scope
   - Allows shadowing in nested scops via `parent` chain
- Use-before-declare:
   - Every `Var` expression is looked up in the nearest enclosing `Scope`
   - Failure raises `SemanticError`
- Return Checks:
   - Ensures `return` expressions exist and are type-copmatible with `int` (trivial for now)
Semantic errors are reported with meagning full messages pointing to the offending node. 

---

## 5. Three-Address Code(TAC) - External IR

### 5.1 TAC Format(`tac.py`)

The TAC is a simple textual IR used for debugging. 

Instruction shapes (informal):
   - `t = a op b` – binary arithmetic / comparison
   - `t = op a` – unary (!, unary -, unary +)
   - `x = y` – copy
   - Labels: `L0:`
   - Conditional branch: `ifFalse c goto L2`
   - Unconditional jump: `goto L3`
   - `return x`
   

### Role of TAC

- TAC is 
   - Easy to print and inspect
   - Stable even as the internal IR changes
- The optimizer does **not** modify raw RAC directly:
   - TAC -> IR (`ir/tac_adapter.py`)
   - IR optimized
   - IR -> TAC again for display


## 6. Internal IR, Basic Blocks, and CFG

Values: 

- `Const(value: int)`
- `Var(name: str)` and `Value = Union[Const, Var]`

Instructions:

```python

@dataclass
class Instr:
    kind: str         # "label", "mov", "binop", "unop", "br", "jmp", "ret"
    dst: Optional[Var] = None
    op:  Optional[str] = None
    a:   Optional[Value] = None
    b:   Optional[Value] = None
    label: Optional[str] = None   # for "label"
    true_label: Optional[str] = None
    false_label: Optional[str] = None

```

Functions and Blocks:
- `Block(label: str | None, instrs: List[Instr])`
- `Function(name: str, blocks: List[Block])`

### 6.2 TAC to IR Afapter (`ir/tac_adapter.py`)

- TAC to IR:
   - Regex/pattern-based parser for each TAC line
   - Converts to `Instr` objects
   - `ifFalse cond goto L` is represented as a `br` with a FALLTHRU placeholder; later resolved

- IR to TAC:
   - Pretty prints the IR back into human-readable TAC
   - Used to keep the CLI behavior stable even as internal representation changes


### 6.3 Building Basic Blocks & CFG (`ir/builder.py`)

Block formation rules:
   - Start with `_entry` if the first TAC line isn't a label.
   - Each label starts a new block. 
   - Terminating instructions(`br`, `jmp`, `ret`) end blocks.

CFG construction:

- For each block, compute:
- `succ[block]`: list of successor blocks
- `pred[block]`: list of predecessor blocks

`ir/pretty.py` implements `dump_blocks` to show blocks (and optionally CFG successors) for debugging.

## 7. Optimizations Pipeline

### 7.1 Constant Propagation (`ir/const_prop.py`)

   - Track variable -> constant mappings within each block.

   - Replace uses of variables with known constant values

   - Correctly invalidaties mappings on writes and across control flow boundaries.

   - Returns `True` if any change is made.

### 7.2 Constant Folding (`ir/const_fold.py`)

   - Folds binary/unary operations when operands are known `Const`:

      - `3 + 4` -> `7`

      - `!0` -> `1`

      - `1 && 0` -> `0`, etc
   - Simplifies trivial operations like:

      - `x + 0`, `x * 1` where safe and implemented

### 7.3 Dead Code Elimination (`ir/dce.py`)

Two Parts:

   1. Unreachable elimination - `drop_unreachable(fn)`

      - Track variable -> constant mappings within each block.

      - Replace uses of variables with known constant values

   2. Dead Store elimination - `dead_store_elim(fn)`
      - For simple variables, removes assignments whose results are never used.

      - Conservative across branches to avoid unsafe elimination.

### 7.4 Straight-Line Fusion (ir/fuse.py)

   - If block A ends with an unconditional jump to B and:

      - B has exactly one predecessor (A),

      - then A and B are merged into one block.

   - Simplifies CFG and improves opportunities for other optimizations.

### 7.5 Copy Propagation (ir/copy_prop.py)

   - Tracks assignments of the form x = y.
   
   - Replaces later uses of x with y when safe.
    
   - Helps collapse chains of temporaries produced by TAC lowering.

### 7.6 Algebraic Simplifications (ir/algebra.py)

   - Performs small local rewrites such as:
   
      - Reordering commutative operations (a + b → b + a) for canonicalization.

      - Collapsing obvious arithmetic patterns where beneficial.

### 7.7 Orchestration (ir/pipeline.py, ir/passes.py)

Two ways to drive passes:

1. Optimization levels – `optimize_function(fn, opt_level)`:

   - `opt_level = 0`: no optimization.
   
   - `opt_level ≥ 1`: iteratively applies constant prop/folding, DCE, fusion, etc., until a fixed point (or a max iteration bound) is reached.
    
   - Higher levels add more aggressive passes like copy-prop and algebraic simplification.

2. Named pass lists – `ir/passes.py`:

- `PASS_FNS` maps names → functions:

   - constprop, constfold, drop_unreachable, dse, copyprop, algebra

- `run_passes(fn, ["constprop","constfold",...], trace=True, dumper=dump_blocks)` is used behind the CLI `--passes` flag.

- `--trace-passes` prints IR blocks after each named pass.

## 8. Pseudo-x86 Code Generation

### 8.1 x86 IR Model (codegen/x86ir.py)

Defines a small typed IR for x86-like code:

   - Operands:

      - `Imm(value)` – immediate integer

      - `Reg(name, fixed=None)` – registers like `"R1"`, `"rax"`, etc.

      - `Mem(name)` – abstract memory (either pseudo symbol or later mapped to `[rbp+offset]`)

      - `FrameRef(offset)` – stack slot at given `rbp` offset

   - Labels:

      - `Label(name)`

      - `LabelDef(label)`

- Instructions (subset):

   - `Mov(dst, src)`
    
   - `Add(dst, src)`
    
   - `Sub(dst, src)`
    
   - `IMul(dst, src)`
    
   - `Cmp(a, b)`
    
   - `Idiv(src)` – uses `RAX`/`RDX` convention
    
   - `Jcc(mnemonic, target)` – `je`, `jne`, `jl`, `jle`, `jg`, `jge`
    
   - `Jmp(target)`
    
   - `Ret(val=None)`
   
   - `Push(reg)`, `Pop(reg)`

`print_program(program)` converts a list of instructions into Intel-like text:

```text
label:
    mov rax, 1
    add rax, 2
    ret
```

### 8.2 Frame Layout & Stack Mode (`FrameLayout`)

`codegen/pseudo_x86.py` builds a stack frame when `frame_mode == "stack"`:

   - Scans IR for named locals (non-temporary Vars).
   
   - Assigns each a slot of 8 bytes at negative offsets from `rbp`:

      - `a -> -8`, `b -> -16`, etc.
    
   - Frame layout:
    
      - `FrameLayout.off_by_name: Dict[str, int]`

      - `FrameLayout.size: int` (total bytes)

Prologue (in stack mode):

```text
push rbp
mov rbp, rsp
sub rsp, frame_size
```

Epilogue (for each `Ret`)

```text
label:
add rsp, frame_size
pop rbp
ret
```

Named locals are accessed via `FrameRef(offset)`, which prints as `[rbp-offset]`.

### 8.3 Lowering IR to x86IR (`emit_instr`, `emit_function`)

Key ideas:

   - Temps vs named vars:

      - Temps (t0, t1, …) live in virtual registers R1, R2, …

   - Named variables either:

      - Become Mem("x") (no stack frame), or

      - Become [rbp+offset] via FrameRef when --frame stack is enabled.

   - Binary operations:

      - Comparison operations (==, !=, <, <=, >, >=) lower to:

         - mov dst, 0

         - cmp left, right

         - conditional jump to set dst = 1 on success

      - Arithmetic +, -, * use two-operand form:

         - dst := a op b is implemented by moving a into an accumulator and then applying add/sub/imul.

   - Division:

     - Integer division uses idiv:

         - Sets up RAX:RDX as dividend

         - Places quotient in RAX

         - Moves RAX into the destination if needed

      - % (remainder) is not currently supported; raising is intentional.

`emit_function(fn, enable_ra, frame_mode)`:

   - Builds an x86IR Program from the IR basic blocks.
   
   - Injects prologue/epilogue when frame_mode == "stack".
    
   - Optionally integrates register allocation (see below).
   
   - Pretty-prints as "function <name>" followed by the body.
   
`emit_pseudo_x86(fn, ...)` is the exported wrapper used in `compiler.py`.


## 9. Register Allocation (codegen/ra.py)


### 9.1 Liveness & Interference

   - Works over a linearized x86IR Program.
   
   - reads_writes(ins) returns two sets:

      - Registers read by ins
      
      - Registers written by ins

   - successors(program):
   
      - For straight-line instructions, successor is the next index.

      - For Jmp, successor is the target label.

      - For conditional Jcc, successors are both fallthrough and target.
    
**Liveness algorithm**:
    
   - Classic backward dataflow:
    
      - OUT[i] = ⋃ IN[s] for all successors s

      - IN[i] = R[i] ∪ (OUT[i] − W[i])
    
   - Iterate until fixed point.

**Interference graph**:

   - Nodes: virtual registers ("R1", "R2", …).
   
   - Edges:
    
      - Between any pair of registers live simultaneously at a program point.

      - Special handling for Idiv:
    
         - Treats "RAX" and "RDX" as pre-colored and interfering with all live regs at that point.

         - Forces RAX and RDX to interfere with each other.

### 9.2 Greedy Coloring

   - Targets caller-saved registers:

      ```text
      CALLER_SAVED = ["rax","rcx","rdx","rsi","rdi","r8","r9","r10","r11"]
      ```


   - Uses a simplified Briggs/Chaitin-style algorithm:
   
      - Remove low-degree nodes into a stack.

      - If needed, pick a high-degree node as a spill candidate.

      - Pop stack and assign a physical register not already used by neighbors.

      - Try to avoid rax / rdx unless necessary (to keep idiv flexible).

      - Spills are tracked in a set.

### 9.3 Spill Rewriting

`rewrite_with_spills(program, colors, spills)`:

   - Any virtual register not spilled is replaced by its assigned physical register.

   - Spilled registers are mapped to stack slots (through FrameRef) using a dedicated scratch register (r10) for loads/stores:

      - On read: mov r10, [spill_slot]
   
      - Use r10 in place of the spilled reg.
    
      - On write: mov [spill_slot], r10

Integration with frame layout:

   - When frame_mode == "stack" and enable_ra is true, a helper rewrites spills onto the frame defined by FrameLayout.
   
   - This produces pseudo-x86 that:

      - Uses only real x86 registers for temps
      
      - Stores spilled temps into stack locations

## 10. Testing & Debugging Aids

Directory structure under `tests/`:

   - tests/lexer_output_testing/ – sample inputs + expected token streams
   
   - tests/parser/valid and tests/parser/invalid – parsing regression tests
    
   - tests/semantic/valid and tests/semantic/invalid – semantic checks
    
   - tests/tac_test/ – TAC emission examples
    
   - tests/optimization/ – IR optimization test cases:
    
      - ir_unreach, copy-prop, const-prop, algebra-simp, etc.
    
   - tests/codegen-x86/ – pseudo-x86 output test cases

Helpful CLI flags (see README for full list):

   - -l / --lexer – print tokens
   
   - -p / --parser – print AST
    
   - -s / --semantic – run semantic checks
    
   - --symtab – print symbol tables
    
   - --tac – print TAC (pre / post optimization depending on flags)
    
   - -O N – run default optimization pipeline
    
   - --passes ..., --trace-passes – manual pass selection and tracing
    
   - --dump-blocks, --dump-cfg, --dump-blocks-after – visualize IR and CFG
    
   - --emit-pseudo-x86, --frame, --ra – x86 codegen control

## 11. Future Work & Possible Extensions

   - Add function parameters and function calls (with calling convention).
   
   - Support for more C constructs: for loops, break/continue, arrays, pointers.
    
   - More advanced optimizations:

      - SSA conversion and SSA-based optimizations
      
      - Loop-invariant code motion, common subexpression elimination
       
   - Real backend:

      - Emitting actual NASM/GAS assembly
      
      - Linking with a C runtime to run compiled programs

## 12. References

Language & Grammar

ANSI C Grammar (quut.com): https://www.quut.com/c/ANSI-C-grammar-y.html

C-- Language Specification: https://www2.cs.arizona.edu/~debray/Teaching/CSc453/DOCS/cminusminusspec.html

EBNF Notation overview: https://en.wikipedia.org/wiki/Extended_Backus%E2%80%93Naur_form

Compilers (tutorials)

Dmitry Soshkinov - https://www.youtube.com/playlist?list=PLGNbPb3dQJ_6aPNnlBvXGyNMlDtNTqN5I

Neso Academy - https://www.youtube.com/playlist?list=PLBlnK6fEyqRjT3oJxFXRgjPNzeS-LFY-q

[Lecture Notes](https://suif.stanford.edu/dragonbook/)

Articles / Series that influenced the approach

Austin Henley — Let’s make a Teeny Tiny Compiler (esp. Part 2 parsing): https://austinhenley.com/blog/teenytinycompiler2.html


Semantic Analysis & Symbol Tables

McGill CS520 slides on Symbol Tables (scoping): https://www.cs.mcgill.ca/~cs520/2020/slides/7-symbol.pdf

Marco Auberer — [Build a Compiler: Symbol Table](https://marcauberer.medium.com/build-a-compiler-symbol-table-2d4582234112)

Drifter1 — [Writing a Simple Compiler on my own — Symbol Table](https://steemit.com/programming/@drifter1/writing-a-simple-compiler-on-my-own-symbol-table-basic-structure)


TAC

[Overview on TAC](https://www.geeksforgeeks.org/compiler-design/three-address-code-compiler/#)


Optimizations

"""

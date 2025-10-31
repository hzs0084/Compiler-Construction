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
  <li>Nov 13 - Low-Level IR</li>
  <li>Dec 04 - Register Allocation</li>
</ol>

**Goal:** Build a subset-C compiler that lexes, parses, performs semantic analysis, and emits optimized three-address code, then emit x86 assembly.


## 1. Overview

This project implements a tiny compiler for a **restricted subset of C**. The pipeline:

The pipeline:

1. **Lexing** (`lexer.py`) → tokens  
2. **Parsing** (`parser.py`) → AST (recursive descent)  
3. **Semantic Analysis** (`semantic.py`) → scoped symbol checks  
4. **TAC (external IR)** (`tac.py`) → three-address code (strings)  
5. **TAC → Internal IR** (`ir/tac_adapter.py`) → `Instr` objects  
6. **Basic Blocks & CFG** (`ir/builder.py`) → blocks, successors/predecessors  
7. **IR Optimizations** (`ir/pipeline.py`)  
   - Constant Folding (`ir/const_fold.py`)  
   - Dead Code Elimination: unreachable + dead store (`ir/dce.py`)  
8. **Round-trip for debugging**: IR → TAC (`ir/tac_adapter.py`)  
9. **(Later)** Register Allocation → x86-64 emission


The goal is a learnable, “Henley-style and Dr. Mulder style of three stage process” implementation: build small, working milestones; keep code simple and readable; and be able to demonstrate each stage with a flag.

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
- Function parameters/calls can be added later; grammar is structured to extend.



## 3. Parser & AST

### 3.1 Parsing strategy

A **recursive-descent** parser closely mirrors the grammar with one method per rule (e.g., `_function`, `_block`, `_assignment`, `_additive`, …). Utility methods:

- `_current()`, `_at_end()`
- `_check(kind, [text])` (peek)
- `_match(kind, [text])` (consume if matches)
- `_expect(kind, [text], msg)` (consume or raise `ParserError` with line/col)

To have precise error messages.

### 3.2 AST nodes (core)

- `Program(functions)`  
- `Function(name, body, start_line, start_col, end_line, end_col)`  
- `Block(items)` where `items` are interleaved `VarDecl` and `Stmt`

Declarations:
- `VarDecl(names: List[str], positions: List[(line, col)])`

Statements:
- `Return(expr)`  
- `If(cond, then_branch, else_branch?)`  
- `While(cond, body)`  
- `ExprStmt(expr)`  
- (and nested `Block`)

Expressions:
- `IntLit(value)`  
- `Var(name)`  
- `Unary(op, expr)`  
- `Binary(op, left, right)`  
- `Assign(name, value)`  // right-assoc semantics

A simple `pretty()` printer helps debug structure during development.

---

## 4. Semantic Analysis

`semantic.py` implements a scoped symbol check:

- Each `{ ... }` introduces a new scope (dictionary from name → type).
- **Redeclaration in the same scope** → error.
- **Use before declare** / **assignment to undeclared** → error.
- **Shadowing** allowed (inner scope may re-use a name).

The pass traverses the AST in source order so “declare-before-use” emerges naturally.

Error type: `SemanticError("…")`.

---

## 5. Symbol Table

For design/visibility purposes, `symfunc.py` builds two textual tables:

1. **Function summary**  
   `nameOfFunctions | typeOfFunctions | function_begins | function_ends | nameOfVariables | typeOfVariables`  
   (top-level vars listed, types are `int`)

2. **Variables (nested scopes)**  
   `function | name | type | scopeLevel | declared_at`  
   where `scopeLevel=0` is the function’s top block, `1` is one `{}` deeper, etc.

Function positions come from parser-captured `start_line/col` and end `}` positions. Variable positions come from tokens captured at declaration time.

---

## 6. Intermediate Representation (TAC)

`tac.py` emits a simple three-address code:

- **Temporaries**: `t0`, `t1`, …  
- **Labels**: `L0`, `L1`, …
- **Statements**:
  - `tN = <expr>` for binary/unary ops, comparisons
  - `name = value` for assignments
  - `ifFalse <cond> goto Lk`, `goto Lm`, `Lk:`
  - `return <value>`
  - `# decl int a, b` comments for visibility

### Control flow:
- `if/else`: `ifFalse cond goto Lelse; then; goto Lend; Lelse: else; Lend:`
- `while`: `Lstart: ifFalse cond goto Lend; body; goto Lstart; Lend:`

### Short-circuit (TAC v3):
- `||` and `&&` are compiled with labels to preserve short-circuiting and yield 0/1 results.

---

## 6.5 Low-Level IR (Internal)

**Values:** `Const(k)`, `Var(name)`  
**Instructions** (subset):
- `mov dst, a`
- `binop dst, op, a, b`  (op ∈ {+, -, *, /, %, ==, !=, <, <=, >, >=, &&, ||})
- `unop dst, op, a`      (op ∈ {+, -, !})
- `br cond ? L_true : L_false`
- `jmp L`
- `return a`
- `label L` (used only during linearization; blocks print their label)

**Basic Block:** labeled list of instructions with **exactly one terminator** at the end (`br`/`jmp`/`return`).

**Function:** list of blocks + computed `succ`/`pred` maps (CFG).

## 6.6 TAC ↔ IR Adapter

- **TAC → IR** (`ir/tac_adapter.py`): small, pattern-based parser (regex) maps TAC lines like  
  `t1 = a + 7`, `x = y`, `ifFalse c goto L2`, `goto L3`, `L0:`, `return v` → IR `Instr`s.  
  For `ifFalse`, a **FALLTHRU** placeholder is used and resolved by the builder.
- **IR → TAC**: re-emits readable TAC so existing CLI/dev flow doesn’t change.

This lets us keep TAC as a user-visible debug format, but run all optimizations on the internal IR.

## 6.7 Building Basic Blocks & CFG

**Block formation** (`ir/builder.py`):
- Start with `_entry` (if first item isn’t a label).
- Split on labels and on terminators (`br`/`jmp`/`return`).
- Insert an explicit `jmp` when a block would otherwise fall through.
- Resolve `br cond ? FALLTHRU : Lfalse` to point to the next block as `L_true`.

**CFG:** compute `succ` (outgoing edges) and `pred` (incoming) per block.

## 7. IR Optimizations (Book-Aligned)

Optimizations run on the **internal IR** with basic blocks/CFG:

**Pass ordering (iterated to fixpoint):**
1. **Constant Folding** (`ir/const_fold.py`)
   - Fold `binop(Const, Const)` and `unop(Const)` → `Const`.
   - Simplify `br Const` to `jmp` (enables reachability pruning).
2. **Dead Code Elimination** (`ir/dce.py`)
   - **Unreachable block elimination**: mark-and-sweep from entry via CFG.
   - **Dead store/code**: per-block backward liveness using successor live-outs; drop `mov/binop/unop` writing to a non-live destination and having **no side effects**.

*Side-effect model:* currently no side-effecting instructions; when calls/stores are added, they’ll be marked as side-effecting so DCE preserves them.

**(Deferred to later milestone)** Register allocation (linear-scan) and x86-64 emission.


<!-- ### CLI Flags (relevant to IR)

- `--tac`         Emit TAC (after IR optimization if `-O > 0`)
- `-O <n>`        Optimization level on IR
  - `-O0`  no IR optimizations
  - `-O1`  constant folding + dead code elimination (IR)
  - (future) higher levels can add more
- `--dump-blocks`         Print IR basic blocks/terminators (pre-opt)
- `--dump-cfg`            With `--dump-blocks`, include successors
- `--dump-blocks-after`   Print IR basic blocks after optimization
 -->

## 8. CLI & Usage

~~~sh
# usage
python3 compiler.py <file.c> [flags]

Flags:
-l, --lexer Print tokens
-p, --parser Print AST (pretty)
-s, --semantic Run semantic checks
--symtab Print function and variable symbol tables
--tac Emit three-address code
-O <n> Optimization level (0=off, 1=const folding)
--constfold Enable constant folding (equivalent to -O1)
~~~

## 9. References
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

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

1. **Lexing** (`lexer.py`) → tokens  
2. **Parsing** (`parser.py`) → AST (recursive descent)  
3. **Semantic Analysis** (`semantic.py`) → scoped symbol checks  
4. **Symbol Tables (reporting)** (`symfunc.py`) → function/variable tables  
5. **Intermediate Representation** (`tac.py`) → three-address code (TAC) with labels  
6. **Optimizations** (`constfold.py`) → constant folding (+ short-circuit aware)  
7. **Driver/CLI** (`compiler.py`) → flags to run each stage and see outputs

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

This gives precise, friendly error messages.

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

## 5. Symbol Table Reporting

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

## 7. Optimizations

### Flags
- `-O0` (default): no optimization
- `-O1` or `--constfold`: enable constant folding
- (Room for `-O2`, `-O3` in future work)

### Constant Folding (`constfold.py`)
- Folds `+ - * / %`, unary `! - +`, comparisons `== != < <= > >=`
- **Short-circuit aware** folding for `&&` and `||` (never “executes” the right side if the left decides the result)
- Safe division/mod (no fold on divide/mod by 0)
- Folds within expressions, `ExprStmt`, `Return`, `If`/`While` conditions (structure preserved)
- Uses `dataclasses.replace` to keep positional metadata intact

Optimization order in driver:
1) (optional) `--semantic`  
2) (if enabled) `constfold`  
3) `--tac` emission over the (possibly) simplified AST

---

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

Compilers (books & tutorials)

Aho, Lam, Sethi, Ullman — Compilers: Principles, Techniques, and Tools (“Dragon Book”)

Keith Cooper & Linda Torczon — Engineering a Compiler

Andrew W. Appel — Modern Compiler Implementation

Terence Parr — Language Implementation Patterns

Robert Nystrom — Crafting Interpreters (great for recursive descent patterns)

LLVM Kaleidoscope tutorial (IR & codegen structure): https://llvm.org/docs/tutorial/

Articles / Series that influenced the approach

Austin Henley — Let’s make a Teeny Tiny Compiler (esp. Part 2 parsing): https://austinhenley.com/blog/teenytinycompiler2.html

Eli Bendersky — posts on parsing and AST design

“Three-Address Code” notes (various university course pages)

Semantic Analysis & Symbol Tables

McGill CS520 slides on Symbol Tables (scoping): https://www.cs.mcgill.ca/~cs520/2020/slides/7-symbol.pdf

Marco Auberer — Build a Compiler: Symbol Table

Drifter1 — Writing a Simple Compiler on my own — Symbol Table

Optimizations

Constant Folding: classic optimization notes across compiler texts (Dragon Book)

Short-circuit evaluation semantics in C (K&R, ISO C standard discussions)
"""

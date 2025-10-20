# Compiler Construction: COMP - 6210

A semester-long project building a tiny compiler in Python for a restricted subset of C.
Pipeline: Lex → Parse → AST → Semantic Analysis → Symbol Tables → TAC → Optimizations.


## Features

- Lexer: tokens for keywords, identifiers, integers, operators, punctuation

- Parser (recursive descent): functions, blocks, declarations, statements, expressions

- AST: clean nodes for functions, blocks, statements, expressions
 
- Semantic checks: redeclaration, use-before-declare, proper block scoping
 
- Symbol tables: function summary + variables with scope levels/positions
 
- TAC (Three-Address Code):
    - arithmetic, comparisons, assignments, return
    
    - control flow: if/else, while (labels + gotos)
    
    - short-circuit && and ||
    

- Optimizations:
    - -O1 / --constfold: constant folding (short-circuit aware)

## Usage

<pre><code>python3 compiler.py <file.c> [flags]
</code></pre>

## Flags

<pre><code>
-l, --lexer        Print tokens
-p, --parser       Print AST (pretty)
-s, --semantic     Run semantic checks (errors for undeclared/redeclared identifiers)
--symtab           Print function + variable symbol tables
--tac              Emit three-address code

-O <n>             Optimization level (0=off, 1=const folding)
--constfold        Enable constant folding (same as -O1)
</code></pre>


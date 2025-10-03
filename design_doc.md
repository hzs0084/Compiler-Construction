# Grammar

The goal is to start from the grammar that was used in the class then build from it


program         -> function_decl_list <br>
function_decl_list -> function_decl_list | function_decl function_decl_list <br>
function_decl        -> Type ID () {statement_list} <br>
statement_list  -> statement_list statement| statement <br>
statement       -> Type ID ; | ID = Expression; | return Expression; <br>
Expresssion     -> Expression + Term | Expression - Term | Term <br>
Term            -> Term + Value | Term / Value | Value <br>
Value           -> (Expression) | NUM | ID | -Value <br>
Type            -> int | float <br>

## Grammar (C Subset)

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



# References

[C Grammar](https://www.quut.com/c/ANSI-C-grammar-y.html) <br>
[C-- Language Specification](https://www2.cs.arizona.edu/~debray/Teaching/CSc453/DOCS/cminusminusspec.html)<br>
[Let's make a Teeny Tiny Compiler - Part 2](https://austinhenley.com/blog/teenytinycompiler2.html)








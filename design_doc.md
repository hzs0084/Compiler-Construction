# Grammar

The goal is to start from the grammar that was used in the class then build from it


program         -> function_decl_list <br>
function_decl_list -> function_decl_list | function_decl function_decl_list <br>
function_decl        -> Type ID () {statement_list} <br>
Type            -> int | float <br>
statement_list  -> statement_list | statement <br>
statement       -> Type ID ; | ID = Expression; | return Expression; <br>
Expresssion     -> Expression + Term | Expression - Term | Term <br>
Term            -> Term + Value | Term / Value | Value <br>
Value           -> (Expression) | NUM | ID | -Value <br>

# Ref: https://hegden.github.io/cs323/homeworks/PA4.pdf
#https://engineering.purdue.edu/~milind/ece468/2012fall/ps-3-sol.pdf


import abstract_syntax_tree as AST

class TACEmitter:
    def __init__(self):
        self.code: list[str] = []
        self.temp_counter = 0

    def new_temp(self) -> str:
        t = f"t{self.temp_counter}"
        self.temp_counter += 1
        return t

    def emit(self, line: str) -> None:
        self.code.append(line)

    # public
    def generate(self, program: AST.Program) -> list[str]:
        # Optional: per-function headers
        for fn in program.functions:
            self.emit(f"# function {fn.name} (int)")
            self._gen_block(fn.body)
            self.emit("")  # blank line between functions
        return self.code

    # blocks & statements 
    def _gen_block(self, block: AST.Block) -> None:
        for item in block.items:
            if isinstance(item, AST.VarDecl):
                # No storage layout yet; just a comment so you can see them
                self.emit(f"# decl int {', '.join(item.names)}")
            elif isinstance(item, AST.Stmt):
                self._gen_stmt(item)
            elif isinstance(item, AST.Block):
                self._gen_block(item)

    def _gen_stmt(self, stmt: AST.Stmt) -> None:
        from abstract_syntax_tree import Return, ExprStmt, If, While, Block
        if isinstance(stmt, Return):
            v = self._gen_expr(stmt.expr)
            self.emit(f"return {v}")
        elif isinstance(stmt, ExprStmt):
            _ = self._gen_expr(stmt.expr)  # value discarded
        elif isinstance(stmt, Block):
            self._gen_block(stmt)
        elif isinstance(stmt, If) or isinstance(stmt, While):
            # mplement control flow later
            raise NotImplementedError("TAC for if/while is in the next milestone.")
        else:
            raise NotImplementedError(f"TAC for stmt {stmt.__class__.__name__}")

    # expressions 
    def _gen_expr(self, expr: AST.Expr) -> str:
        from abstract_syntax_tree import IntLit, Var, Unary, Binary, Assign
        if isinstance(expr, IntLit):
            return str(expr.value)
        if isinstance(expr, Var):
            return expr.name
        if isinstance(expr, Unary):
            val = self._gen_expr(expr.expr)
            # normalize ops: + is a no-op
            if expr.op == "+":
                return val
            t = self.new_temp()
            if expr.op == "-":
                self.emit(f"{t} = - {val}")
            elif expr.op == "!":
                # treat as 0/1 logical not
                self.emit(f"{t} = ! {val}")
            else:
                raise NotImplementedError(f"unary op {expr.op!r}")
            return t
        if isinstance(expr, Binary):
            left = self._gen_expr(expr.left)
            right = self._gen_expr(expr.right)
            t = self.new_temp()
            self.emit(f"{t} = {left} {expr.op} {right}")
            return t
        if isinstance(expr, Assign):
            rhs = self._gen_expr(expr.value)
            self.emit(f"{expr.name} = {rhs}")
            # assignment is an expression and its value is the left value after assignment
            return expr.name
        raise NotImplementedError(f"TAC for expr {expr.__class__.__name__}")

def generate_tac(program: AST.Program) -> list[str]:
    """
    Convenience function: returns a list of TAC lines.
    """
    return TACEmitter().generate(program)
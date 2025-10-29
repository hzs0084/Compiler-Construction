# Ref: https://hegden.github.io/cs323/homeworks/PA4.pdf
#https://engineering.purdue.edu/~milind/ece468/2012fall/ps-3-sol.pdf


import abstract_syntax_tree as AST

class TACEmitter:
    def __init__(self):
        self.code: list[str] = []
        self.temp_counter = 0
        self.label_counter = 0


    def new_temp(self) -> str:
        t = f"t{self.temp_counter}"
        self.temp_counter += 1
        return t

    def new_label(self, base: str = "L") -> str:
        l = f"{base}{self.label_counter}"
        self.label_counter += 1
        return l

    def emit(self, line: str) -> None:
        self.code.append(line)

    def label(self, lab: str) -> None:
        self.emit(f"{lab}:")

    def _as_bool(self, v: str) -> str:
        t = self.new_temp()
        self.emit(f"{t} = {v} != 0")
        return t
    
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
        elif isinstance(stmt, If):
            self._gen_if(stmt)
        elif isinstance(stmt, While):
            self._gen_while(stmt)
        else:
            raise NotImplementedError(f"TAC for stmt {stmt.__class__.__name__}")

    # control flow

    def _gen_if(self, node: AST.If) -> None:
        cond = self._gen_expr(node.cond)
        if node.else_branch is None:
            L_end = self.new_label("L")
            self.emit(f"ifFalse {cond} goto {L_end}")
            self._gen_block(node.then_branch)
            self.label(L_end)
        else:
            L_else = self.new_label("L")
            L_end  = self.new_label("L")
            self.emit(f"ifFalse {cond} goto {L_else}")
            self._gen_block(node.then_branch)
            self.emit(f"goto {L_end}")
            self.label(L_else)
            self._gen_block(node.else_branch)
            self.label(L_end)

            #    might run into an issue with basic blocks

    def _gen_while(self, node: AST.While) -> None:
        Lstart = self.new_label("L")
        Lend   = self.new_label("L")
        self.label(Lstart)
        cond = self._gen_expr(node.cond)
        self.emit(f"ifFalse {cond} goto {Lend}")
        self._gen_block(node.body)
        self.emit(f"goto {Lstart}")
        self.label(Lend)
    
    def _gen_logical_or(self, left_expr: AST.Expr, right_expr: AST.Expr) -> str:
        #   result = (left || right) as 0/1 with short-circuit
        l = self._as_bool(self._gen_expr(left_expr))
        result = self.new_temp()
        self.emit(f"{result} = {l}")    # start with left's truth value
        L_end = self.new_label("L")
        # if left is true, skip right
        self.emit((f"if {result} goto {L_end}"))
        r = self._as_bool(self._gen_expr(right_expr))
        result = self.new_temp()
        self.emit(f"{result} = {r}")
        self.label(L_end)
        return result
    
    def _gen_logical_and(self, left_expr: AST.Expr, right_expr: AST.Expr) -> str:
        #   result = (left && right) as 0/1 with short-circuit
        l = self._as_bool(self._gen_expr(left_expr))
        result = self.new_temp()
        self.emit(f"{result} = {l}")    # start with left's truth value
        L_end = self.new_label("L")
        # if left is false, skip right
        self.emit((f"ifFalse {result} goto {L_end}"))
        r = self._as_bool(self._gen_expr(right_expr))
        result = self.new_temp()
        self.emit(f"{result} = {r}")
        self.label(L_end)
        return result

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
            if expr.op == "||":
                return self._gen_logical_or(expr.left, expr.right)
            if expr.op == "&&":
                return self._gen_logical_and(expr.left, expr.right)        

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
    returns a list of TAC lines.
    """
    return TACEmitter().generate(program)


"""
Refs: https://anoopsarkar.github.io/compilers-class/assets/lectures/ir.pdf

https://stackoverflow.com/questions/59256249/code-generation-for-short-circuit-boolean-operators
https://web.stanford.edu/class/archive/cs/cs143/cs143.1128/handouts/240%20TAC%20Examples.pdf
https://www.cs.columbia.edu/~aho/cs4115/Lectures/15-03-25.html
https://austinhenley.com/blog/teenytinycompiler3.html

"""
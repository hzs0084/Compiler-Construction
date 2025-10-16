from errors import ParserError
import lexer as lex
import abstract_syntax_tree as AST


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0
        pass

    # utility methods
    def _current(self):
        return self.tokens[self.i]

    def _at_end(self):
        return self._current().kind is lex.TokenKind.EOF

    def _check(self, kind, text=None):
        if self._at_end():
            return False
        
        t = self._current()

        if t.kind is not kind:
            return False
        
        if text is not None and t.lexeme != text:
            return False
        
        return True

    def _match(self, kind, text=None):
        if self._check(kind, text):
            self.i += 1
            return True
        return False

    def _expect(self, kind, text=None, msg=""):
        if not self._check(kind, text):
            t = self._current()
            expect = kind.name + (f" {text!r}" if text else "")
            got = f"{t.kind.name} {t.lexeme!r}"
            raise ParserError(f"{msg}: expected {expect}, got {got}", t.line, t.col)
        
        tok = self._current()
        self.i += 1
        return tok

    # entry

    """
    Program -> FunctionDecLList
    """
    def parse(self) -> AST.Program:
        functions = []

        # require at least one function

        if self._at_end():
            t = self._current()
            raise ParserError("expected a function, found enf od file", t.line, t.col)
        while not self._at_end():
            functions.append(self._function())
        return AST.Program(functions)

    # functions & blocks

    """
    Function -> Type ID () Block
    """
    def _function(self) -> AST.Function:
        self._expect(lex.TokenKind.KEYWORD, "int", msg= "functino must start with 'int'")
        name_tok = self._expect(lex.TokenKind.IDENT, msg= "expected function name")
        self._expect(lex.TokenKind.PUNCT, "(",msg= "expected '(' after function name ")
        self._expect(lex.TokenKind.PUNCT, ")",msg= "expected ')' after function name")
        body = self._block()
        return AST.Function(name_tok.lexeme, body)
    
    def _block_empty_only(self) -> AST.Block:

        """
        Block -> '{' '}'
        Starting with empty blocks
        """

        self._expect(lex.TokenKind.PUNCT, "{",msg= "expected '{' to start block")
        self._expect(lex.TokenKind.PUNCT, "}",msg= "expected '}' to start block")

        return AST.Block(items=[])

    def _block(self) -> AST.Block:
        self._expect(lex.TokenKind.PUNCT, "{",msg= "expected '{' to start block")
        items: list[AST.Stmt] = []
        while not self._check(lex.TokenKind.PUNCT, "}") and not self._at_end():
            items.append(self._statement())
        self._expect(lex.TokenKind.PUNCT, "}",msg= "expected '}' to start block")
        return AST.Block(items)

    def _declaration(self):
        pass

    # statements
    def _statement(self) -> AST.Stmt:
        if self._check(lex.TokenKind.KEYWORD, "return"):
            return self._return_stmt()
        if self._check(lex.TokenKind.PUNCT, "{"):
            return self._block()
        # default: expression statement
        return self._expr_stmt()

    def _return_stmt(self) -> AST.Return:
        self._expect(lex.TokenKind.KEYWORD, "return")
        expr = self._expression()
        self._expect(lex.TokenKind.PUNCT, ";", msg= "expected ';' after return statement")
        return AST.Return(expr)

    def _if_stmt(self):
        pass

    def _while_stmt(self):
        pass

    def _expr_stmt(self) -> AST.ExprStmt:
        expr = self._expression()
        self._expect(lex.TokenKind.PUNCT, ";", msg="expected ';' after expression")
        return AST.ExprStmt(expr)

    # expressions
    def _expression(self) -> AST.Expr:
        return self._additive()
    
    def _assignment(self):
        pass

    def _logical_or(self):
        pass

    def _logical_and(self):
        pass

    def _equality(self):
        pass

    def _relational(self):
        pass

    def _additive(self) -> AST.Expr:
        node = self._multiplicative()
        while True:
            if self._match(lex.TokenKind.OP, "+"):
                rhs = self._multiplicative()
                node = AST.Binary("+", node, rhs)
            elif self._match(lex.TokenKind.OP, "-"):
                rhs = self._multiplicative()
                node = AST.Binary("-", node, rhs)
            else:
                break
        return node

    def _multiplicative(self) -> AST.Expr:
        node = self._unary()
        while True:
            if self._match(lex.TokenKind.OP, "*"):
                rhs = self._unary()
                node = AST.Binary("*", node, rhs)
            elif self._match(lex.TokenKind.OP, "/"):
                rhs = self._unary()
                node = AST.Binary("/", node, rhs)
            elif self._match(lex.TokenKind.OP, "%"):
                rhs = self._unary()
                node = AST.Binary("%", node, rhs)
            else:
                break
        return node
    
    def _unary(self) -> AST.Expr:
        if self._match(lex.TokenKind.OP, "!"):
            return AST.Unary("!", self._unary())
        if self._match(lex.TokenKind.OP, "-"):
            return AST.Unary("-", self._unary())
        if self._match(lex.TokenKind.OP, "+"):
            return AST.Unary("+", self._unary())
        return self._primary()

    def _primary(self) -> AST.Expr:
        if self._match(lex.TokenKind.PUNCT, "("):
            expr = self._expression()
            self._expect(lex.TokenKind.PUNCT, ")", msg="expected ')'")
            return expr

        if self._check(lex.TokenKind.INT):
            tok = self._expect(lex.TokenKind.INT)
            return AST.IntLit(int(tok.lexeme))

        if self._check(lex.TokenKind.IDENT):
            tok = self._expect(lex.TokenKind.IDENT)
            return AST.Var(tok.lexeme)

        t = self._current()
        raise ParserError(f"expected expression, got {t.kind.name} {t.lexeme!r}", t.line, t.col)
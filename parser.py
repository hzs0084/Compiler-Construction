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
    
    def _peek_is_equals(self) -> bool:
        j = self.i + 1
        if j >= len(self.tokens):
            return False
        t = self.tokens[j]
        return t.kind is lex.TokenKind.OP and t.lexeme == "="

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

        # need the position of the keyword 'int'
        start_tok = self._current()
        self._expect(lex.TokenKind.KEYWORD, "int", msg= "functino must start with 'int'")
        name_tok = self._expect(lex.TokenKind.IDENT, msg= "expected function name")
        self._expect(lex.TokenKind.PUNCT, "(",msg= "expected '(' after function name ")
        self._expect(lex.TokenKind.PUNCT, ")",msg= "expected ')' after function name")
        body = self._block()    #takes the closing '}' inside

        end_tok = self.tokens[self.i - 1]
        return AST.Function(name_tok.lexeme,
                            body = body,
                            start_line = start_tok.line,
                            start_col=start_tok.col,
                            end_line=end_tok.line,
                            end_col=end_tok.line)
    
    def _block_empty_only(self) -> AST.Block:

        """
        Block -> '{' '}'
        Starting with empty blocks
        """

        self._expect(lex.TokenKind.PUNCT, "{",msg= "expected '{' to start block")
        self._expect(lex.TokenKind.PUNCT, "}",msg= "expected '}' to start block")

        return AST.Block(items=[])

    def _block(self) -> AST.Block:

        """
        Block → "{" Item* "}"
        Item  → Declaration | Statement
        """
        """
        inside a block, we can expect one or more items so add it to the list of items
        while it's not the end with } or at the end keep appending if it's declaration or a statement
        """
        self._expect(lex.TokenKind.PUNCT, "{",msg= "expected '{' to start block")
        items: list[AST.VarDecl | AST.Stmt] = []
        while not self._check(lex.TokenKind.PUNCT, "}") and not self._at_end():
            if self._check(lex.TokenKind.KEYWORD, "int"):
                items.append(self._declaration())
            else:
                items.append(self._statement())
        self._expect(lex.TokenKind.PUNCT, "}",msg= "expected '}' to start block")
        return AST.Block(items)

    def _declaration(self) -> AST.VarDecl:

        """
        Declaration → "int" id { "," id } ";"
        """

        """
        expect the keyword in the declaration, then expec the name of the decl, append that token to the list of
        names now start the while loop for multiple decl that would be separated by a comma
        expect to end with the ; declaration
        """
        self._expect(lex.TokenKind.KEYWORD, "int", msg= "declaration must start with 'int'")
        names: list[str] = []
        poss: list[tuple[int,int]] = []

        first = self._expect(lex.TokenKind.IDENT, msg= "expected a variable name")
        names.append(first.lexeme)
        poss.append((first.line, first.col))

        while self._match(lex.TokenKind.PUNCT, ","):
            ident = self._expect(lex.TokenKind.IDENT, msg= "expected variable name after ','")
            names.append(ident.lexeme)
            poss.append((first.line, first.col))

        self._expect(lex.TokenKind.PUNCT, ";",msg= "expected ';' after declaraation")
        return AST.VarDecl(names, poss)

    # statements
    def _statement(self) -> AST.Stmt:
        if self._check(lex.TokenKind.KEYWORD, "return"):
            return self._return_stmt()
        if self._check(lex.TokenKind.KEYWORD, "if"):
            return self._if_stmt()
        if self._check(lex.TokenKind.KEYWORD, "while"):
            return self._while_stmt()
        if self._check(lex.TokenKind.PUNCT, "{"):
            return self._block()
        # default: expression statement
        return self._expr_stmt()

    def _return_stmt(self) -> AST.Return:
        self._expect(lex.TokenKind.KEYWORD, "return")
        expr = self._expression()
        self._expect(lex.TokenKind.PUNCT, ";", msg= "expected ';' after return statement")
        return AST.Return(expr)

    def _if_stmt(self) -> AST.If:
        # IfStmt → "if" "(" Expression ")" Block [ "else" Block ]
        self._expect(lex.TokenKind.KEYWORD, "if")
        self._expect(lex.TokenKind.PUNCT, "(", "expected '(' after the if statement")
        cond = self._expression()
        self._expect(lex.TokenKind.PUNCT, ")", msg="expected ')' after condition")
        then_blk = self._block()  # blocks are required
        else_blk = None
        if self._match(lex.TokenKind.KEYWORD, "else"):
            else_blk = self._block()
        return AST.If(cond, then_blk, else_blk)


    def _while_stmt(self) -> AST.While:
        self._expect(lex.TokenKind.KEYWORD, "while")
        self._expect(lex.TokenKind.PUNCT, "(", "expected '(' after while")
        cond = self._expression()
        self._expect(lex.TokenKind.PUNCT, ")", "expected ')' after condition")
        body = self._block()       # need blocks in while
        return AST.While(cond, body)


    def _expr_stmt(self) -> AST.ExprStmt:
        expr = self._expression()
        self._expect(lex.TokenKind.PUNCT, ";", msg="expected ';' after expression")
        return AST.ExprStmt(expr)

    # expressions
    def _expression(self) -> AST.Expr:
        return self._assignment()
        #return self._additive()

    def _assignment(self) -> AST.Expr:
        # Assignment -> id "=" Assignment | LogicalOr

        if self._check(lex.TokenKind.IDENT) and self._peek_is_equals():
            name_tok = self._expect(lex.TokenKind.IDENT)
            self._expect(lex.TokenKind.OP, "=", "expected '=' in assignment")
            value = self._assignment() # This should make it right-associative recursion
            return AST.Assign(name_tok.lexeme, value)
        return self._logical_or()

    def _logical_or(self) -> AST.Expr:
        # LogicalOr → LogicalAnd { "||" LogicalAnd }
        node = self._logical_and()
        while self._match(lex.TokenKind.OP, "||"):
            rhs = self._logical_and()
            node = AST.Binary("||", node, rhs)
        return node

    def _logical_and(self) -> AST.Expr:
        # LogicalAnd → Equality { "&&" Equality }
        node = self._equality()
        while self._match(lex.TokenKind.OP, "&&"):
            rhs = self._equality()
            node = AST.Binary("&&", node, rhs)
        return node

    def _equality(self) -> AST.Expr:
        # Equality → Relational { ("==" | "!=") Relational }
        node = self._relational()
        while True:
            if self._match(lex.TokenKind.OP, "=="):
                rhs = self._relational()
                node = AST.Binary("==", node, rhs)
            elif self._match(lex.TokenKind.OP, "!="):
                rhs = self._relational()
                node = AST.Binary("!=", node, rhs)
            else:
                break
        return node

    def _relational(self) -> AST.Expr:
        # Relational → Additive { ("<" | "<=" | ">" | ">=") Additive }
        node = self._additive()
        while True:
            if self._match(lex.TokenKind.OP, "<"):
                rhs = self._additive()
                node = AST.Binary("<", node, rhs)
            elif self._match(lex.TokenKind.OP, "<="):
                rhs = self._additive()
                node = AST.Binary("<=", node, rhs)
            elif self._match(lex.TokenKind.OP, ">"):
                rhs = self._additive()
                node = AST.Binary(">", node, rhs)
            elif self._match(lex.TokenKind.OP, ">="):
                rhs = self._additive()
                node = AST.Binary(">=", node, rhs)
            else:
                break
        return node

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
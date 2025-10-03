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
        body = self._block_empty_only()
        return AST.Function(name_tok.lexeme, body)
    
    def _block_empty_only(self) -> AST.Block:

        """
        Block -> '{' '}'
        Starting with empty blocks
        """

        self._expect(lex.TokenKind.PUNCT, "{",msg= "expected '{' to start block")
        self._expect(lex.TokenKind.PUNCT, "}",msg= "expected '}' to start block")

        return AST.Block(items=[])

    def _block(self):
        pass

    def _declaration(self):
        pass

    # statements
    def _statement(self):
        pass

    def _return_stmt(self):
        pass

    def _if_stmt(self):
        pass

    def _while_stmt(self):
        pass

    def _expr_stmt(self):
        pass

    # expressions
    def _expression(self):
        pass

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

    def _additive(self):
        pass

    def _multiplicative(self):
        pass

    def _unary(self):
        pass

    def _primary(self):
        pass

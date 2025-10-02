class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0
        pass

    # utility methods
    def _current(self):
        pass

    def _at_end(self):
        pass

    def _check(self, kind, text=None):
        pass

    def _match(self, kind, text=None):
        pass

    def _expect(self, kind, text=None, msg=""):
        pass

    # entry
    def parse(self):
        pass

    # functions & blocks
    def _function(self):
        pass

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

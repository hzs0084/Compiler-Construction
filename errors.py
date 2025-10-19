class LexerError(Exception):
    
    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"Lexical Error: {message} at line {line}, column {column}")

class ParserError(Exception):

    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"Parser Error: {message} at line {line}, column {column}")

class SemanticError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(f"Semantic Error: {message}")

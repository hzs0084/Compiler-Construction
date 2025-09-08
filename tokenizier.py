import lexer

class Token:
    type: str
    value: str
    line: int
    column: int

def tokenize(Program):
    keywords = {'int', 'return'}
    token_specification = [
        ('')
    ]
from dataclasses import dataclass
from enum import Enum, auto

class TokenType(Enum):
    KEYWORD = auto()
    IDENT = auto()
    INT_LITERAL = auto()
    STRING_LITERAL = auto()
    PUNCT = auto()
    EOF = auto()

@dataclass #why data clasS?

class Token:
    type: TokenType
    lexeme: str
    line: int
    col: int  

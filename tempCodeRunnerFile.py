from dataclasses import dataclass
from enum import Enum, auto

class TokenKind(Enum):
    KEYWORD = auto()
    IDENT = auto()
    INT_LITERAL = auto()
    STRING_LITERAL = auto()
    PUNCT = auto()
    EOF = auto()

@dataclass
class Token:
    kind: TokenKind
    lexeme: str
    line: int
    col: int  

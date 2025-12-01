import re
from enum import Enum, auto
from typing import List, NamedTuple
from errors import LexerError

# https://www.geeksforgeeks.org/python/enum-auto-in-python/#

class TokenKind(Enum):
    KEYWORD = auto()
    IDENT   = auto()
    INT     = auto()
    STRING  = auto()
    OP      = auto()      # operators like ==, &&, +, -
    PUNCT   = auto()      # punctuation like ; , ( ) { }
    EOF     = auto()


class Token(NamedTuple):
    kind: TokenKind
    lexeme: str
    line: int
    col: int


KEYWORDS = {
    "int", "return", "if", "else", "while", "for", "break", "continue"
}


def remove_comments(source):
        # Remove multi-line comments /* ... */
        multiline_comment = re.compile(r'/\*.*?\*/', re.DOTALL)
        source = multiline_comment.sub('', source)
        
        # Remove single-line comments // ...
        oneline_comment = re.compile(r'//.*')
        source = oneline_comment.sub('', source)

        return source

def tokenize(source: str) -> List[Token]:
    
    """
    Turn C-like source code into a list of Token(kind, lexeme, line, col).
    Newlines/whitespace are skipped; line/col are tracked for diagnostics.
    """

    source = remove_comments(source)

    token_spec = [
        ("NEWLINE", r"\r?\n"),
        ("SKIP",    r"[ \t\f\v]+"),
        ("STRING",  r"\"([^\"\\]|\\.)*\""),
        ("INT",     r"0|[1-9]\d*"),
        ("ID",      r"[A-Za-z_]\w*"),
        ("OP",      r"==|!=|<=|>=|\|\||&&|<<|>>|\+=|-=|\*=|/=|%="
                    r"|->|::|="
                    r"|[+\-*/%<>!&|~^]"),
        ("PUNCT",   r"[;,(){}\[\]]"),  # <— includes ';'
        ("MISMATCH",r"."),
    ] 

    master_pat = re.compile("|".join(f"(?P<{name}>{pat})" for name, pat in token_spec))

    tokens: List[Token] = []
    line = 1
    line_start = 0

    # print("Tokens and their line:col outputs \n")

    for mo in master_pat.finditer(source):
        kind = mo.lastgroup
        text = mo.group()

        if kind == "NEWLINE":
            line += 1
            line_start = mo.end()
            continue
        if kind == "SKIP":
            continue
        if kind == "MISMATCH":
            col = mo.start() - line_start + 1
            raise LexerError(f"Unexpected character {text!r}", line, col)

        col = mo.start() - line_start + 1

        if kind == "ID":
            if text in KEYWORDS:
                tokens.append(Token(TokenKind.KEYWORD, text, line, col))
            else:
                tokens.append(Token(TokenKind.IDENT, text, line, col))
        elif kind == "INT":
            tokens.append(Token(TokenKind.INT, text, line, col))
        elif kind == "STRING":
            tokens.append(Token(TokenKind.STRING, text, line, col))
        elif kind == "OP":
            tokens.append(Token(TokenKind.OP, text, line, col))
        elif kind == "PUNCT":
            tokens.append(Token(TokenKind.PUNCT, text, line, col))
        else:
            # Should never happen because everything is handled above but just in case
            raise SyntaxError(f"Unhandled token {text!r} at {line}:{col}")

    tokens.append(Token(TokenKind.EOF, "", line, (len(source) - line_start) + 1))
    return tokens

"""
Edge/corner notes:

String literal support exists in lexer but parser/AST doesn’t handle strings yet

Multi-char ops like <<, >>, +=, etc. are tokenized but not parsed by the grammar.
"""

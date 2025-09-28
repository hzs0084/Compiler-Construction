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

# https://austinhenley.com/blog/teenytinycompiler1.html

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
            # Should never happen because we handled everything above
            raise SyntaxError(f"Unhandled token {text!r} at {line}:{col}")

    tokens.append(Token(TokenKind.EOF, "", line, (len(source) - line_start) + 1))
    return tokens

# class Lexer:
#     def __init__(self, source):
#         self.source = source + "\n"     #Append a new line to simplify lexing/parsing the last token/statement
#         self.cur_char = ""      # Current character in the string
#         self.cur_pos = -1       # Current position in the string
#         self.nextChar()


#     # Process the next character.
#     def nextChar(self):
#         self.cur_pos += 1
#         if self.cur_pos >= len(self.source):
#              self.cur_char = "\0" # EOF

#         else:
#              self.cur_char = self.source[self.cur_pos]

#     # Return the lookahead character.
#     def peek(self):
#         if self.cur_pos + 1 >= len(self.source):
#              return "\0"
#         return self.source[self.cur_pos + 1]

#     # Invalid token found, print error message and exit.
#     def abort(self, message):
#         sys.exit("Lexing error. " + message)
		
#     # Skip whitespace except newlines, which we will use to indicate the end of a statement.
#     def skipWhitespace(self):
#         while self.cur_char == " " or self.cur_char == "\t" or self.cur_char == "\r":
#              self.nextChar()
		
#     # Skip comments in the code.
#     def skipComment(self):
#         pass

#     # Return the next token.
#     def getToken(self):
#         # Check the first character of this token to see if we can decide what it is
#         # if it is a multiple character operator that is something like !=, number, identifier, or keyword then we will process the rest.
#         self.skipWhitespace()
#         if self.cur_char == "+":
#             token = Token(self.cur_char, TokenType.PLUS)           # Plus Token
#         elif self.cur_char == "-":
#             token = Token(self.cur_char, TokenType.MINUS)           # Minus Token
#         elif self.cur_char == "*":
#             token = Token(self.cur_char, TokenType.ASTERISK)            # Asterisk Token
#         elif self.cur_char == "/":
#             token = Token(self.cur_char, TokenType.SLASH)            # Slash Token
#         elif self.cur_char == "\n":
#             token = Token(self.cur_char, TokenType.NEWLINE)            # NewLine Token
#         elif self.cur_char == "\0":
#             token = Token(self.cur_char, TokenType.EOF)            # EOF Token
#         else:
#             self.abort("Unknown token: " + self.cur_char)            # Unknown Token

#         self.nextChar()
#         return token

# class Token:
     
#     def __init__(self, token_text, token_kind):
#          self.text = token_text     # The actual text from the token. Used for identifiers, strings, and numbers
#          self.kind = token_kind     # The token type that thsi token is classified as
    

# class TokenType(enum.Enum):
#      EOF = -1
#      NEWLINE = 0
#      NUMBER = 1
#      IDENT = 2
#      STRING = 3

#      LABEL = 101
#      GOTO = 102
#      PRINT = 103
#      INPUT = 104
#      LET = 105
#      IF = 106
#      THEN = 107
#      ENDIF = 108
#      WHILE = 109
#      REPEAT = 110
#      ENDWHILE = 111

#      EQ = 201
#      PLUS = 202
#      MINUS = 203
#      ASTERISK = 204
#      SLASH = 205
#      EQEQ = 206
#      NOTEQ = 207
#      LT = 208
#      LTEQ = 209
#      GT = 210
#      GTEQ = 211


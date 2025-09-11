import re
from typing import List
from tokens import Token, TokenType
from errors import ErrorReporter

# Small keyword set
KEYWORDS = {"int", "return", "if", "else", "while", "for", "char", "void"}


PUNCT_CHARCLASS = r'[\[\]\(\)\{\}\.&\*\+\-\~\!\/%\<\>\^\|\?\:\;\=\,\#]'

token_specification = [
    ("MULTI_LINE_COMMENT", r'/\*[\s\S]*?\*/'),            # multi-line comments (non-greedy, spans lines)
    ("SINGLE_LINE_COMMENT", r'//[^\n]*'),                  # single-line comments
    ("STRING",   r'"(?:\\.|[^"\\\n])*"'),       # minimal C string: no newlines, allow \" and \\ escapes
    ("ID",       r'[A-Za-z_][A-Za-z_0-9]*'),    # identifiers
    ("INT",      r'\d+'),                       # decimal integers (MVP)
    ("PUNCT",    PUNCT_CHARCLASS),              # 1-char punctuators
    ("NEWLINE",  r'\n'),                        # track line numbers
    ("SKIP",     r'[ \t\r\f\v]+'),              # skips the spaces/tabs/etc. (but not newlines)
    ("MISMATCH", r'.'),                         # any other single char -> error
]

# Build one big regex with named groups: (?P<NAME>pattern)|...
TOK_REGEX = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_specification)
MASTER = re.compile(TOK_REGEX)

def lex(program_text: str, filename: str, errors: ErrorReporter) -> List[Token]:
    tokens: List[Token] = []
    line_num = 1
    line_start = 0  # index of start of current line

    match_object = MASTER.match(program_text)
    while match_object is not None:
        kind = match_object.lastgroup
        value = match_object.group(kind)

        if kind == "NEWLINE":
            line_start = match_object.end()
            line_num += 1

        elif kind == "SKIP" or kind == "SINGLE_LINE_COMMENT" or kind == "MULTI_LINE_COMMENT":
            # Ignore these completely, but they still advance the cursor.
            pass

        elif kind == "ID":
            
            token_kind = TokenType.KEYWORD if value in KEYWORDS else TokenType.IDENT
            col = (match_object.start() - line_start) + 1
            tokens.append(Token(token_kind, value, line_num, col))

        elif kind == "INT":
            col = (match_object.start() - line_start) + 1
            tokens.append(Token(TokenType.INT_LITERAL, value, line_num, col))

        elif kind == "STRING":
            col = (match_object.start() - line_start) + 1
            tokens.append(Token(TokenType.STRING_LITERAL, value, line_num, col))

        elif kind == "PUNCT":
            col = (match_object.start() - line_start) + 1
            tokens.append(Token(TokenType.PUNCT, value, line_num, col))

        elif kind == "MISMATCH":
            col = (match_object.start() - line_start) + 1
            
            errors.report(filename, line_num, col, f"unexpected character {value!r}")

        # Advance to the next token
        match_object = MASTER.match(program_text, match_object.end())

    # EOF token
    # Column is 1 + index into current line
    final_col = (len(program_text) - line_start) + 1
    tokens.append(Token(TokenType.EOF, "", line_num, final_col))
    return tokens

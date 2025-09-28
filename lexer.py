import re
from enum import Enum, auto
from typing import List, NamedTuple
import sys


def remove_comments(source_code):
        # Remove multi-line comments /* ... */
        multiline_comment = re.compile(r'/\*.*?\*/', re.DOTALL)
        source_code = multiline_comment.sub('', source_code)
        
        # Remove single-line comments // ...
        oneline_comment = re.compile(r'//.*')
        source_code = oneline_comment.sub('', source_code)

        return source_code

# class Token:
#         self.type: str
#         self.value: str
#         # self.line: int
#         # self.column: int

def tokenize(source_code):
        
        KEYWORDS = {"INT", "RETURN", "BREAK", "FOR", "FLOAT", "WHILE", "IF", 
                    "ELSE", "CASE", "SWITCH", "DEFAULT"}
        
# https://austinhenley.com/blog/teenytinycompiler1.html

class Lexer:
    def __init__(self, source):
        self.source = source + "\n"     #Append a new line to simplify lexing/parsing the last token/statement
        self.cur_char = ""      # Current character in the string
        self.cur_pos = -1       # Current position in the string
        self.nextChar()


    # Process the next character.
    def nextChar(self):
        self.cur_pos += 1
        if self.cur_pos >= len(self.source):
             self.cur_char = "\0" # EOF

        else:
             self.cur_char = self.source[self.cur_pos]

    # Return the lookahead character.
    def peek(self):
        if self.cur_pos + 1 >= len(self.source):
             return "\0"
        return self.source[self.cur_pos + 1]

    # Invalid token found, print error message and exit.
    def abort(self, message):
        sys.exit("Lexing error. " + message)
		
    # Skip whitespace except newlines, which we will use to indicate the end of a statement.
    def skipWhitespace(self):
        while self.cur_char == " " or self.cur_char == "\t" or self.cur_char == "\r":
             self.nextChar()
		
    # Skip comments in the code.
    def skipComment(self):
        pass

    # Return the next token.
    def getToken(self):
        # Check the first character of this token to see if we can decide what it is
        # if it is a multiple character operator that is something like !=, number, identifier, or keyword then we will process the rest.
        self.skipWhitespace()
        if self.cur_char == "+":
            token = Token(self.cur_char, TokenType.PLUS)           # Plus Token
        elif self.cur_char == "-":
            token = Token(self.cur_char, TokenType.MINUS)           # Minus Token
        elif self.cur_char == "*":
            token = Token(self.cur_char, TokenType.ASTERISK)            # Asterisk Token
        elif self.cur_char == "/":
            token = Token(self.cur_char, TokenType.SLASH)            # Slash Token
        elif self.cur_char == "\n":
            token = Token(self.cur_char, TokenType.NEWLINE)            # NewLine Token
        elif self.cur_char == "\0":
            token = Token(self.cur_char, TokenType.EOF)            # EOF Token
        else:
            self.abort("Unknown token: " + self.cur_char)            # Unknown Token

        self.nextChar()
        return token

class Token:
     
    def __init__(self, token_text, token_kind):
         self.text = token_text     # The actual text from the token. Used for identifiers, strings, and numbers
         self.kind = token_kind     # The token type that thsi token is classified as
    

class TokenType(enum.Enum):
     EOF = -1
     NEWLINE = 0
     NUMBER = 1
     IDENT = 2
     STRING = 3

     LABEL = 101
     GOTO = 102
     PRINT = 103
     INPUT = 104
     LET = 105
     IF = 106
     THEN = 107
     ENDIF = 108
     WHILE = 109
     REPEAT = 110
     ENDWHILE = 111

     EQ = 201
     PLUS = 202
     MINUS = 203
     ASTERISK = 204
     SLASH = 205
     EQEQ = 206
     NOTEQ = 207
     LT = 208
     LTEQ = 209
     GT = 210
     GTEQ = 211


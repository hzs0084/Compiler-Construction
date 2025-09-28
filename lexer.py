import re

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
        self.cur_Char = ""      # Current character in the string
        self.cur_Pos = -1       # Current position in the string
        self.nextChar()


    # Process the next character.
    def nextChar(self):
        self.cur_Pos += 1
        if self.cur_Pos >= len(self.source):
             self.cur_Char = "\0" # EOF

        else:
             self.cur_Char = self.source[self.cur_Pos]

    # Return the lookahead character.
    def peek(self):
        if self.cur_Pos + 1 >= len(self.source):
             return "\0"
        return self.source[self.cur_Pos + 1]

    # Invalid token found, print error message and exit.
    def abort(self, message):
        pass
		
    # Skip whitespace except newlines, which we will use to indicate the end of a statement.
    def skipWhitespace(self):
        pass
		
    # Skip comments in the code.
    def skipComment(self):
        pass

    # Return the next token.
    def getToken(self):
        pass
        
# def main(source_code):
    
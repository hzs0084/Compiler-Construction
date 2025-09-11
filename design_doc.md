Design Document for my C Compiler


compiler.py - This is going to be my main function and it will accept arguments to spit outputs like the AST, Tokens, etc

lexer.py - This is my tokenizer

errors.py - tracking and throwing errors that were caused and handle errors in the compiler.

tests.py - testing my compiler


Tokens:
    Keywords: int, return, if, else, while, for, char, void
    Identifiers:
    Integer Literals:
    Punctuators: [ ] ( ) { } . & * + - ~ ! / % < > ^ | ? : ; = , #
    Comments: //[^\n]* and /\*.*?\*/


[Regex](https://regexone.com/)


Usage: python3 compiler.py -l testing_simple_c_programs/test3.c



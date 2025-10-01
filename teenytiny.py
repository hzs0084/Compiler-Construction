from lex import *
from parse import *
import sys

def main():
    print("Teeny Tiny Compiler")

    # if len(sys.argv) != 2:
    #         sys.exit("Error: Compiler needs source file as argument.")

    # with open(sys.argv[1], "r") as inputFile:
    # source = """ LABEL loop
    #         PRINT "hello, world!"
    #         GOTO loop""" #inputFile.read()

    if len(sys.argv) != 2:
        sys.exit("Error: Compiler needs source file as argument.")
    
    with open(sys.argv[1], "r") as inputFile:
        source = inputFile.read()

    # Intialize the lexer anad parser
    lexer = Lexer(source)
    parser = Parser(lexer)

    parser.program() # Start the parser

    print("Parsing Completed")

main()
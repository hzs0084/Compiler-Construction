'''
A C Compiler by Hemant Sherawat for COMP 6210
'''

import argparse
import os
import sys
import lexer as lex
from errors import LexerError, ParserError
from parser import Parser
import abstract_syntax_tree as AST


def main():

    print("---A Tiny C Compiler made by Hemant Sherawat---\n")

    # Command-line arguments for running the compiler
    arg_parser = argparse.ArgumentParser(description='A tiny compiler for C language')
    arg_parser.add_argument('input_file', help='Input source code file')
    arg_parser.add_argument('-l', '--lexer', action='store_true', help='Print lexer output tokens')
    arg_parser.add_argument('-p', '--parser', action='store_true', help='Parse and print AST')
    arg_parser.add_argument('--symtab', action='store_true', help='Print function symbol table')
    args = arg_parser.parse_args()

    # See if input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found")
        return

    # Check for .c extension in the input file
    if (args.input_file) [-2:] != ".c":
        print(".c extension not found in the file")
        sys.exit()

    # Read source code
    with open(args.input_file, 'r') as file:
        source = file.read()
        #print(source_code)

    # take that source code and run through the lexer for lexical analysis

    # try the lex

    try:
        tokens = lex.tokenize(source)
    except LexerError as e:
        print(f"{e}")
        sys.exit(1)     # should prevent the unbound local error

    # i will add better error handling here later


    if args.lexer:
        for tok in tokens:
            if tok.kind is lex.TokenKind.EOF:
                continue
            print(f"{tok.line}:{tok.col}\t{tok.kind.name:<7}\t{tok.lexeme!r}") #come back to this later
    
    #parse logic here eventually

    if args.parser:
        try:
            ast = Parser(tokens).parse()
        except ParserError  as e:
            print(f"Parsing error: {e}")
            sys.exit(1)

        print(AST.pretty(ast))

        #print(ast)

    # after parsing succeeds:
    if args.symtab:
        from symfunc import build_function_rows, format_table
        rows = build_function_rows(ast)
        # derive a short display name (like "main.c")
        display_name = os.path.basename(args.input_file)
        print(format_table(display_name, rows))


  

    print("\n--- End ---\n")

if __name__ == "__main__":
    main()

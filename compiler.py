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
    arg_parser.add_argument('-s', '--semantic', action='store_true', help='Run semantic checks')

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

    # Decide if we need to parse (parser/semantic/symtab/tac all need the AST)
    need_parse = args.parser or args.semantic or args.symtab  # add args.tac later if you add TAC
    program_ast = None

    if need_parse:
        try:
            program_ast = Parser(tokens).parse()
        except ParserError as e:
            print(f"Parsing error: {e}")
            sys.exit(1)

    # --parser: pretty print the AST
    if args.parser:
        # if you have a pretty-printer:
        try:
            from abstract_syntax_tree import pretty
            print(pretty(program_ast))
        except Exception:
            # fallback if pretty() not available
            print(program_ast)

    # --symtab: print your symbol tables
    if args.symtab:
        from symfunc import build_function_rows, format_func_table, build_variable_rows, format_var_table
        filename = os.path.basename(args.input_file)
        frows = build_function_rows(program_ast)
        vrows = build_variable_rows(program_ast)
        print(format_func_table(filename, frows))
        print()
        print(format_var_table(filename, vrows))

    # --semantic: run semantic checks
    if args.semantic:
        from semantic import analyze  # and optionally: from errors import SemanticError
        try:
            analyze(program_ast)
        except Exception as e:  # optionally catch SemanticError specifically
            import traceback
            traceback.print_exc()   #remove this later
            print(e)
            sys.exit(1)
        print("Semantic check: OK")

    # if args.parser:
    #     try:
    #         ast = Parser(tokens).parse()
    #     except ParserError  as e:
    #         print(f"Parsing error: {e}")
    #         sys.exit(1)

    #     print(AST.pretty(ast))

    #     if args.semantic:
    #         try:
    #             from semantic import analyze
    #             analyze(ast)
    #         except Exception as e:
    #             # Catch SemanticError specifically if you prefer:
    #             # from errors import SemanticError
    #             # except SemanticError as e:
    #             print(e)
    #             sys.exit(1)
    #         print("Semantic check: OK")
    
    #     if args.symtab:
    #         from symfunc import build_function_rows, format_func_table, build_variable_rows, format_var_table
    #         filename = os.path.basename(args.input_file)
    #         frows = build_function_rows(ast)
    #         vrows = build_variable_rows(ast)
    #         print(format_func_table(filename, frows))
    #         print()
    #         print(format_var_table(filename, vrows))

        #print(ast)

    # after parsing succeeds:
    # if args.symtab:
    #     from symfunc import build_function_rows, format_table
    #     rows = build_function_rows(ast)
    #     # derive a short display name (like "main.c")
    #     display_name = os.path.basename(args.input_file)
    #     print(format_table(display_name, rows))
    
    # after parse succeeds


  

    print("\n--- End ---\n")

if __name__ == "__main__":
    main()

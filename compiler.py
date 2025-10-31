'''
A C Compiler by Hemant Sherawat for COMP 6210
'''

import argparse
import os
import sys
import lexer as lex
from errors import LexerError, ParserError
from parser import Parser
from tac import generate_tac

def main():

    print("---A Tiny C Compiler made by Hemant Sherawat---\n")

    # Command-line arguments for running the compiler
    arg_parser = argparse.ArgumentParser(description='A tiny compiler for C language')
    arg_parser.add_argument('input_file', help='Input source code file')
    arg_parser.add_argument('-l', '--lexer', action='store_true', help='Print lexer output tokens')
    arg_parser.add_argument('-p', '--parser', action='store_true', help='Parse and print AST')
    arg_parser.add_argument('--symtab', action='store_true', help='Print function symbol table')
    arg_parser.add_argument('-s', '--semantic', action='store_true', help='Run semantic checks')
    arg_parser.add_argument('--tac', action='store_true', help='Emit three-address code')
    arg_parser.add_argument('-O', dest='opt_level', type=int, default=0,
                            help='Optimization level (0=off, 1=const folding, 2+=future)')
    arg_parser.add_argument('--constfold', action='store_true',
                            help='Enable constant folding (same as -O1+)')

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
    need_parse = (
                    args.parser or args.semantic or args.symtab or args.tac
                    or args.opt_level > 0 or args.constfold)
    program_ast = None

    if need_parse:
        try:
            program_ast = Parser(tokens).parse()
        except ParserError as e:
            print(f"Parsing error: {e}")
            sys.exit(1)

    # --parser: pretty print the AST
    if args.parser:
        # pretty-printer:
        try:
            from abstract_syntax_tree import pretty
            print(pretty(program_ast))
        except Exception:
            # fallback if pretty() not available
            print(program_ast)

    # --symtab: print symbol tables
    if args.symtab:
        from symfunc import build_function_rows, format_func_table, build_variable_rows, format_var_table
        filename = os.path.basename(args.input_file)
        frows = build_function_rows(program_ast)
        vrows = build_variable_rows(program_ast)
        print(format_func_table(filename, frows))
        print()
        print(format_var_table(filename, vrows))

    # --semantic: run semantic checks
    if args.semantic:       # or args.tac for debugging
        from semantic import analyze
        from errors import SemanticError 
        try:
            analyze(program_ast)
        except SemanticError as e:  # catch SemanticError specifically
            print(f"Semantic error: {e}")
            sys.exit(1)
        print("Semantic check: OK")
        
    # --tac
    if args.tac:
        tac_lines = generate_tac(program_ast)

        # O1: constant folding
        if (args.opt_level >= 1) or args.constfold:
            from opt_constfold import fold_tac
            tac_lines = fold_tac(tac_lines)

        # O3: algebraic simplification, then quick fold again
        if args.opt_level >= 3:
            from opt_algebra import simplify_tac
            tac_lines = simplify_tac(tac_lines)
            from opt_constfold import fold_tac
            tac_lines = fold_tac(tac_lines)

        # O1+: local constant propagation (runs for O1 and higher)
        if args.opt_level >= 1:
            from opt_constprop import const_propagate
            tac_lines = const_propagate(tac_lines)

        # O2: copy propagation
        if args.opt_level >= 2:
            from opt_copyprop import copy_propagate
            tac_lines = copy_propagate(tac_lines)
            # O2+: DCE
            from opt_dce import dce
            tac_lines = dce(tac_lines)

        print("\n".join(tac_lines))

        # # O1: constant folding (IR)
        # do_constfold = (args.opt_level >= 1) or args.constfold
        # if do_constfold:
        #     try:
        #         from opt_constfold import fold_tac
        #         tac_lines = fold_tac(tac_lines)
        #     except Exception as e:
        #         print(f"[constfold error] {e}")

        # # O3: algebraic simplification (IR)
        # if args.opt_level >= 3:
        #     try:
        #         from opt_algebra import simplify_tac
        #         tac_lines = simplify_tac(tac_lines)
        #     except Exception as e:
        #         print(f"[algebra error] {e}")

        # print("\n".join(tac_lines))

    

    # # if args.tac:
    #     tac_lines = generate_tac(program_ast)

    #     print(f"[debug] before passes: {len(tac_lines)}")

    #     # O1: constant folding (IR)
    #     do_constfold = (args.opt_level >= 1) or args.constfold
    #     if do_constfold:
    #         from opt_constfold import fold_tac as _fold_tac
    #         print(f"[debug] constfold from: {_fold_tac.__module__}")
    #         _after_cf = _fold_tac(tac_lines)
    #         print(f"[debug] after constfold: {len(_after_cf)}")
    #     else:
    #         _after_cf = tac_lines

    #     # O3: algebraic simplification (IR)
    #     if args.opt_level >= 3:
    #         from opt_algebra import simplify_tac as _simplify_tac
    #         print(f"[debug] algebra from: {_simplify_tac.__module__}")
    #         _after_alg = _simplify_tac(_after_cf)
    #         print(f"[debug] after algebra: {len(_after_alg)}")
    #     else:
    #         _after_alg = _after_cf

    #     tac_lines = _after_alg
    #     print(f"[debug] before print: {len(tac_lines)}")


    #     print("[debug] raw TAC (first 20 lines):")
    #     for i, ln in enumerate(tac_lines[:20], 1):
    #         print(f"{i:02d}: {ln}")


        # # O1: constant folding (IR)
        # do_constfold = (args.opt_level >= 1) or args.constfold
        # if do_constfold:
        #     try:
        #         from opt_constfold import fold_tac
        #         tac_lines = fold_tac(tac_lines)
        #     except Exception as e:
        #         print(f"[constfold error] {e}")

        # # O3: algebraic simplification (IR)
        # if args.opt_level >= 2:
        #     try:
        #         from opt_algebra import simplify_tac
        #         tac_lines = simplify_tac(tac_lines)
        #     except Exception as e:
        #         print(f"[algebra error] {e}")

        # print(f"[debug] --tac={args.tac}  -O={args.opt_level}  constfold={args.constfold}")
        # print(f"[debug] TAC lines: {len(tac_lines)}")
        # print("\n".join(tac_lines))


    print("\n--- End ---\n")

if __name__ == "__main__":
    main()

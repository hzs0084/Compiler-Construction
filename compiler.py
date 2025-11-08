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
from ir.tac_adapter import tac_to_linear_ir, ir_to_tac
from ir.builder import linear_to_blocks
from ir.pipeline import optimize_function
from ir.pretty import dump_blocks

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
    arg_parser.add_argument(
        '--passes',
        help='Comma-separated list of IR passes to run (overrides -O). '
             'Options: constprop,constfold,drop_unreachable,dse,copyprop,algebra'
    )
    arg_parser.add_argument('--trace-passes', action='store_true',
                            help='After each pass, print IR basic blocks')
    
    arg_parser.add_argument('--dump-blocks', action='store_true',
                        help='Print basic blocks after CFG building (pre-optimization)')
    arg_parser.add_argument('--dump-cfg', action='store_true',
                            help='Include CFG successors in --dump-blocks output')
    arg_parser.add_argument('--dump-blocks-after', action='store_true',
                            help='Print basic blocks after optimization')



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

        # # Convert TAC -> IR, optimize, IR -> TAC
        # from ir.tac_adapter import tac_to_linear_ir, ir_to_tac
        # from ir.builder import linear_to_blocks
        # from ir.pipeline import optimize_function

        # # get function name for header (your TAC header has it)
        # func_name = "main"  # or parse it from the "# function ..." comment if you prefer
        # linear_ir, header = tac_to_linear_ir(func_name, tac_lines)
        # fn = linear_to_blocks(func_name, linear_ir)


        # optimize_function(fn, opt_level=args.opt_level)

        # # if args.opt_level >= 1:
        # #     optimize_function(fn)

        # tac_lines = ir_to_tac(fn, header)
        # print("\n".join(tac_lines))

        linear_ir, header = tac_to_linear_ir("main", tac_lines)
        fn = linear_to_blocks("main", linear_ir)

        if args.dump_blocks:
            print(dump_blocks(fn, show_cfg=args.dump_cfg))

        optimize_function(fn, opt_level=args.opt_level)

        if args.dump_blocks_after:
            print(dump_blocks(fn, show_cfg=args.dump_cfg))

        tac_lines = ir_to_tac(fn, header)
        print("\n".join(tac_lines))

    print("\n--- End ---\n")

if __name__ == "__main__":
    main()

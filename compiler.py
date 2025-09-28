'''
A C Compiler by Hemant Sherawat for COMP 6210
'''

import argparse
import os
import sys
import tokenizer as tok

def main():

    # Command-line arguments for actually running the compiler
    arg_parser = argparse.ArgumentParser(description='A tiny compiler for C language')
    arg_parser.add_argument('input_file', help='Input source code file')
    arg_parser.add_argument('-l', '--lexer', action='store_true', help='Print lexer output tokens')
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
        source_code = file.read()
        #print(source_code)

    # take that source code and run through the lexer for lexical analysis

    source_code = tok.remove_comments(source_code)

    print(source_code)
    



if __name__ == "__main__":
    main()

'''
A C Compiler by Hemant Sherawat for COMP 6210
'''

import argparse

def main():
    parser = argparse.ArgumentParser("Processing a C file")

    parser = parser.add_argument("-L", "--list-tokens", action="store_true", help="Print a list of tokens")


if __name__ == "__main__":
    main()
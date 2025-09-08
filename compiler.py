# Add code for the main arguments and the flags that the code will accept

# Need to add some error checking here to make sure that only correct files will be used in the compiler

# Display a message like "A C Compiler built using Python by Hemant Sherawat"

import argparse

def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("-l", "--lexer", required=True)


if __name__ == "__main()__":
    main()
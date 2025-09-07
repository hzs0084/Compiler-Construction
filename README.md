# Compiler-Construction
COMP 6210 class with Dr. Mulder


[List_of_Awesome_Compilers](https://github.com/aalhour/awesome-compilers?tab=readme-ov-file#educational-and-toy-projects) This repo has tons of compilers and learning resources that might be very helpful.

Design Doc for the class 



References:
    [C Grammar](https://www2.cs.arizona.edu/~debray/Teaching/CSc453/DOCS/cminusminusspec.html)
    [C11 Standard](https://www.open-std.org/jtc1/sc22/WG14/www/docs/n1570.pdf)



## Project Timeline
    Sept 11 - Lexar
    Oct 2 - Parser
    Oct 16 - 3 Addr Code
    Oct 30 - Optimization
    Nov 13 - Low Level IR
    Dec 4 - Register Allocation

### My extra notes


When converting the source code / High Level Code (HLL). It goes through the Preprocessor, Compiler, Assembler, and Linker/Loader to convert into machine code.


The preprocessor embedds the required header files with the source code that omitts all the preprocessor directives, an example would be the stdio.h header file in a basic c program. 



A compiler is made up of
    Lexical Analysis
    Syntax Analysis
    Semantic Analysis
    Intermediate Code Generation
    Code Optimization
    Target Code Generation


The Lexical Analyzer takes lexemes as inputs and generates tokens. The tokens are the meanings of the lexus

An example: x = a + b * c;

List of Lexemes: x, =, a, +, b, *, c
List of tokens: identifier, operator, identifier, operator, identifier

The job of the lexical analyzer is to find out the meaning of the every lexem, to recognize the token, we use RegExs

Lexical Analyzer:
    Scans the pure HLL code line by line.
    Takes lexemes as inputs and produces tokens.
    Removes comments and whitespaces from the pure hll code.

Tokens are made up of:
    Keywords
    Identifier
    Punctuators
    Operators
    Constants
    Literals
    Special characters


An example program and it's tokens

int main()
{
    int x, a = 2, b = 3, c = 5;
    x = a + b * c;
    printf("The value of x is %d", x);
    return 0;
}

Tokens:
    Keywords: int, return
    Identifier: main, x, a, b, c, printf
    Punctuators: {, ",", }, ( , ), ;
    Operators: +, *
    Constants: 2, 3, 5, 0
    Literals: "The value of x is %d"

    Count = 39


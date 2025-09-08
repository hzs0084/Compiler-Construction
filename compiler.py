import argparse
import sys
from errors import ErrorReporter
from lexer import lex
from tokens import TokenType

def quote(s: str) -> str:
    return '"' + s.replace('\\', '\\\\').replace('\n', '\\n').replace('\t', '\\t').replace('"', '\\"') + '"'

def main():
    parser = argparse.ArgumentParser(description="C11 toy compiler (lexer-only, regex MVP)")
    parser.add_argument("-l", "--lex", metavar="FILE", dest="lex_file", help="Lex the given .c file and print tokens")
    args = parser.parse_args()

    if not args.lex_file:
        parser.print_help()
        sys.exit(0)

    path = args.lex_file
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        print(f"{path}: error: {e}", file=sys.stderr)
        sys.exit(1)

    errors = ErrorReporter()
    tokens = lex(source, path, errors)

    for t in tokens:
        if t.type is TokenType.EOF:
            print(f"{t.line}:{t.col}  {t.type.name}")
        else:
            print(f"{t.line}:{t.col}  {t.type.name}  {quote(t.lexeme)}")

    for d in errors.diagnostics:
        print(errors.format(d), file=sys.stderr)

    sys.exit(1 if errors.any_errors() else 0)

if __name__ == "__main__":
    main()

# errors.py
from dataclasses import dataclass
from typing import List

@dataclass
class Diagnostic:
    filename: str
    line: int
    col: int
    message: str
    level: str = "error"

class ErrorReporter:
    def __init__(self) -> None:
        self.diagnostics: List[Diagnostic] = []

    def report(self, filename: str, line: int, col: int, message: str, level: str = "error") -> None:
        self.diagnostics.append(Diagnostic(filename, line, col, message, level))

    def any_errors(self) -> bool:
        return any(d.level == "error" for d in self.diagnostics)

    def format(self, d: Diagnostic) -> str:
        return f"{d.filename}:{d.line}:{d.col}: {d.level}: {d.message}"

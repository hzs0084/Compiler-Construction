import abstract_syntax_tree as AST
from typing import List, Tuple
from dataclasses import dataclass

# Rows = (fname, ftype, begins, ends, varname, vartype)
Row = Tuple[str, str, str, str, str, str]  

@dataclass
class VarRow:
    func: str
    name: str   
    typ: str
    scope: str
    decl_at: str

#
def build_function_rows(program: AST.Program) -> List[Row]:
    rows: List[Row] = []
    for fn in program.functions:
        begins = f"({fn.start_line},{fn.start_col})"
        ends   = f"({fn.end_line},{fn.end_col})"
        
        # Collect top-level vars from the function's body
        top_names: List[str] = []
        top_types: List[str] = []

        for item in getattr(fn.body, "items", []):
            if isinstance(item, AST.VarDecl):
                # all are 'int' in the subset
                top_names += item.names
                top_types += ["int"] * len(item.names)

        vars_cell = ", ".join(top_names) if top_names else "N/A"
        types_cell = ", ".join(top_types) if top_types else "N/A"

        rows.append((
            fn.name,
            "int",       # only int functions for now
            begins,
            ends,
            vars_cell,
            types_cell,
        ))
    return rows

def build_variable_rows(program: AST.Program) -> List[VarRow]:
    rows: List[VarRow] = []
    for fn in program.functions:
        _collect_vars_in_block(fn.name, fn.body, scope_level = 0, out=rows)
    return rows


def format_table(filename: str, rows: List[Row]) -> str:
    # column headers
    headers = [
        "nameOfFunctions",
        "typeOfFunctions",
        "function_begins",
        "function_ends",
        "nameOfVariables",
        "typeOfVariables",
    ]
    # compute column widths
    cols = list(zip(*([headers] + rows))) if rows else [headers]
    widths = [max(len(str(cell)) for cell in col) for col in cols]

    def fmt(row):
        return "  ".join(str(cell).ljust(w) for cell, w in zip(row, widths))

    out: List[str] = []
    out.append(f"{filename}\n")
    out.append(fmt(headers))
    for r in rows:
        out.append(fmt(r))
    return "\n".join(out)

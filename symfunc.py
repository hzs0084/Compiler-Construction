import abstract_syntax_tree as AST
from typing import List, Tuple, Optional
from dataclasses import dataclass
from abstract_syntax_tree import If, While, Block

# Rows = (fname, ftype, begins, ends, varname, vartype)
Row = Tuple[str, str, str, str, str, str]  

@dataclass
class VarRow:
    func: str
    name: str   
    typ: str
    scope: str
    decl_at: str


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


def format_func_table(filename: str, rows: List[Row]) -> str:
    
    # column headers
    headers = [
        "nameOfFunctions",
        "typeOfFunctions",
        "function_begins",
        "function_ends",
        "nameOfVariables",
        "typeOfVariables",
    ]

    return _format_table(headers, rows, title=filename)

def format_var_table(filename: str, rows: List[VarRow]) -> str:
    
    headers = ["function", "name", "type", "scopeLevel", "declared_at"]
    raw: List[Tuple[str, str, str, str, str]] = [
        (r.func, r.name, r.typ, str(r.scope), r.decl_at) for r in rows
    ]
    title = f"{filename} — variables (nested scopes)"
    return _format_table(headers, raw, title=title)

# Adding helpers

def _collect_vars_in_block(func_name: str, block: AST.Block, scope_level: int, out:List[VarRow]) -> None:

    #record any decls in this block

    for item in block.items:
        if isinstance(item, AST.VarDecl):
            for (nm, (ln, col)) in zip(item.names, item.positions):
                out.append(VarRow(func=func_name, name=nm, typ="int",
                                  scope=scope_level, decl_at=f"({ln},{col})"))
        elif isinstance(item, AST.Block):
            # nested block — walk one level deeper
            _collect_vars_in_block(func_name, item, scope_level + 1, out)
        elif isinstance(item, AST.Stmt):
            # statements may *contain* blocks (If/While/Block); descend into them
            _descend_stmt(func_name, item, scope_level, out)

def _descend_stmt(func_name: str, stmt: AST.Stmt, scope_level: int, out: List[VarRow]) -> None:
    
    if isinstance(stmt, If):
        _collect_vars_in_block(func_name, stmt.then_branch, scope_level + 1, out)
        if stmt.else_branch:
            _collect_vars_in_block(func_name, stmt.else_branch, scope_level + 1, out)
    elif isinstance(stmt, While):
        _collect_vars_in_block(func_name, stmt.body, scope_level + 1, out)
    elif isinstance(stmt, Block):
        _collect_vars_in_block(func_name, stmt, scope_level + 1, out)
    else:
        # Return / ExprStmt don’t introduce scopes
        pass


    # do formatting to keep it pretty
def _format_table(headers: List[str], rows: List[Tuple], title: Optional[str] = None) -> str:
    cols = list(zip(*([headers] + rows))) if rows else [headers]
    widths = [max(len(str(cell)) for cell in col) for col in cols]
    def fmt(row): return "  ".join(str(cell).ljust(w) for cell, w in zip(row, widths))
    lines: List[str] = []
    if title: lines.append(title + "\n")
    lines.append(fmt(headers))
    for r in rows:
        lines.append(fmt(r))
    return "\n".join(lines)

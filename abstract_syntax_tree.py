from dataclasses import dataclass
from typing import List

@dataclass
class Program:
    functions: List["Function"]

@dataclass
class Function:
    name: str
    body: "Block"

@dataclass
class Block:
    items: List[object]

# print something here to debuggin purposes

def pretty(node, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(node, Program):
        inner = "\n".join(pretty(f, indent + 1) for f in node.functions)
        return f"{pad}Program\n{inner}"
    if isinstance(node, Function):
        inner = pretty(node.body, indent + 1)
        return f"{pad}Function name={node.name}\n{inner}"
    if isinstance(node, Block):
        if not node.items:
            return f"{pad}Block (empty)"
        inner = "\n".join(pretty(it, indent + 1) for it in node.items)
        return f"{pad}Block\n{inner}"
    # Fallback for now
    return f"{pad}{node.__class__.__name__}({node})"
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ExtractedSymbol:
    name: str
    kind: str # function, class, method, interface
    start_line: int
    end_line: int

@dataclass
class ExtractedEdge:
    from_symbol: str
    to_symbol: str
    kind: str # import, call, reference
    line_number: int

@dataclass
class StructureResult:
    structure_level: str # 'tree_sitter' or 'text_only'
    symbols: List[ExtractedSymbol]
    edges: List[ExtractedEdge]


class StructureExtractor:
    """Extracts symbols, imports, and calls using tree-sitter, falling back to text_only gracefully."""

    def extract(self, file_path: str, language: str, content: str) -> StructureResult:
        symbols: List[ExtractedSymbol] = []
        edges: List[ExtractedEdge] = []

        try:
            from tree_sitter_languages import get_parser
            parser = get_parser(language)
            tree = parser.parse(bytes(content, "utf8"))
            root = tree.root_node
        except Exception:
            # Unsupported language or missing grammar: skip silently and record structure_level = 'text_only'
            return StructureResult(structure_level="text_only", symbols=[], edges=[])

        # Traverse AST
        self._traverse(root, content, symbols, edges, current_scope="global")

        return StructureResult(
            structure_level="tree_sitter",
            symbols=symbols,
            edges=edges
        )

    def _traverse(
        self,
        node,
        content: str,
        symbols: List[ExtractedSymbol],
        edges: List[ExtractedEdge],
        current_scope: str
    ):
        ntype = node.type

        # Function definitions
        if ntype in ("function_definition", "function_declaration"):
            name_node = node.child_by_field_name("name")
            if name_node:
                name = content[name_node.start_byte:name_node.end_byte]
                symbols.append(ExtractedSymbol(
                    name=name,
                    kind="function",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1
                ))
                current_scope = name

        # Class definitions
        elif ntype in ("class_definition", "class_declaration"):
            name_node = node.child_by_field_name("name")
            if name_node:
                name = content[name_node.start_byte:name_node.end_byte]
                symbols.append(ExtractedSymbol(
                    name=name,
                    kind="class",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1
                ))
                current_scope = name

        # Method definitions
        elif ntype in ("method_definition", "method_declaration"):
            name_node = node.child_by_field_name("name")
            if name_node:
                name = content[name_node.start_byte:name_node.end_byte]
                symbols.append(ExtractedSymbol(
                    name=name,
                    kind="method",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1
                ))
                current_scope = name

        # Imports
        elif ntype in ("import_statement", "import_from_statement", "import_declaration"):
            text_slice = content[node.start_byte:node.end_byte].strip()
            edges.append(ExtractedEdge(
                from_symbol=current_scope,
                to_symbol=text_slice[:100],
                kind="import",
                line_number=node.start_point[0] + 1
            ))

        # Calls
        elif ntype in ("call_expression", "call"):
            func_node = node.child_by_field_name("function")
            if func_node:
                callee_name = content[func_node.start_byte:func_node.end_byte]
                # Filter out complex multi-line chained expressions for reliable symbol names
                if len(callee_name) < 60 and "\n" not in callee_name:
                    edges.append(ExtractedEdge(
                        from_symbol=current_scope,
                        to_symbol=callee_name,
                        kind="call",
                        line_number=node.start_point[0] + 1
                    ))

        # Recursively process children
        for child in node.children:
            self._traverse(child, content, symbols, edges, current_scope)

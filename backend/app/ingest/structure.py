import ast
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ExtractedSymbol:
    name: str
    kind: str  # function, class, method, interface
    start_line: int
    end_line: int


@dataclass
class ExtractedEdge:
    from_symbol: str
    to_symbol: str
    kind: str  # import, call, reference
    line_number: int


@dataclass
class StructureResult:
    structure_level: str  # 'tree_sitter', 'ast_native', or 'text_only'
    symbols: List[ExtractedSymbol]
    edges: List[ExtractedEdge]


class StructureExtractor:
    """Extracts symbols, imports, and calls using Tree-sitter or native AST with regex fallback."""

    def extract(self, file_path: str, language: str, content: str) -> StructureResult:
        symbols: List[ExtractedSymbol] = []
        edges: List[ExtractedEdge] = []

        # 1. Try tree-sitter if grammar is installed
        try:
            from tree_sitter_languages import get_parser
            parser = get_parser(language)
            tree = parser.parse(bytes(content, "utf8"))
            self._traverse_treesitter(tree.root_node, content, symbols, edges, current_scope="global")
            if symbols or edges:
                return StructureResult(
                    structure_level="tree_sitter",
                    symbols=symbols,
                    edges=edges
                )
        except Exception:
            pass

        # 2. Python native AST parser
        if language == "python" or file_path.endswith(".py"):
            try:
                tree = ast.parse(content)
                self._traverse_python_ast(tree, symbols, edges)
                return StructureResult(
                    structure_level="ast_native",
                    symbols=symbols,
                    edges=edges
                )
            except Exception:
                pass

        # 3. Regex structural extraction for JS/TS, Go, Java, C++, Rust
        struct_res = self._extract_regex(content, language)
        if struct_res.symbols or struct_res.edges:
            return struct_res

        return StructureResult(structure_level="text_only", symbols=[], edges=[])

    def _traverse_python_ast(self, tree: ast.AST, symbols: List[ExtractedSymbol], edges: List[ExtractedEdge]):
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append(ExtractedSymbol(
                    name=node.name,
                    kind="function",
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno)
                ))
            elif isinstance(node, ast.ClassDef):
                symbols.append(ExtractedSymbol(
                    name=node.name,
                    kind="class",
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno)
                ))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    edges.append(ExtractedEdge(
                        from_symbol="module",
                        to_symbol=alias.name,
                        kind="import",
                        line_number=node.lineno
                    ))
            elif isinstance(node, ast.Call):
                callee = None
                if isinstance(node.func, ast.Name):
                    callee = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    callee = node.func.attr
                if callee and callee not in ("print", "len", "range", "str", "int", "dict", "list"):
                    edges.append(ExtractedEdge(
                        from_symbol="global",
                        to_symbol=callee,
                        kind="call",
                        line_number=node.lineno
                    ))

    def _extract_regex(self, content: str, language: str) -> StructureResult:
        symbols: List[ExtractedSymbol] = []
        edges: List[ExtractedEdge] = []
        lines = content.splitlines()

        for idx, line in enumerate(lines, start=1):
            line_str = line.strip()

            # JS/TS/Go function definitions
            func_m = re.match(r"(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)", line_str)
            if not func_m:
                func_m = re.match(r"func\s+(?:\([^)]+\)\s+)?([a-zA-Z0-9_]+)\s*\(", line_str)
            if not func_m:
                func_m = re.match(r"(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>", line_str)

            if func_m:
                symbols.append(ExtractedSymbol(
                    name=func_m.group(1),
                    kind="function",
                    start_line=idx,
                    end_line=min(idx + 15, len(lines))
                ))

            # Class / Type definitions
            class_m = re.match(r"(?:export\s+)?class\s+([a-zA-Z0-9_$]+)", line_str)
            if not class_m:
                class_m = re.match(r"type\s+([a-zA-Z0-9_]+)\s+struct", line_str)
            if class_m:
                symbols.append(ExtractedSymbol(
                    name=class_m.group(1),
                    kind="class",
                    start_line=idx,
                    end_line=min(idx + 25, len(lines))
                ))

            # Imports
            if line_str.startswith("import ") or line_str.startswith("from "):
                edges.append(ExtractedEdge(
                    from_symbol="module",
                    to_symbol=line_str[:80],
                    kind="import",
                    line_number=idx
                ))

            # Method calls
            call_m = re.findall(r"\b([a-zA-Z0-9_]{3,30})\s*\(", line_str)
            for c in call_m:
                if c not in ("if", "for", "while", "switch", "catch", "function", "return"):
                    edges.append(ExtractedEdge(
                        from_symbol="global",
                        to_symbol=c,
                        kind="call",
                        line_number=idx
                    ))

        return StructureResult(
            structure_level="regex_fallback" if (symbols or edges) else "text_only",
            symbols=symbols,
            edges=edges
        )

    def _traverse_treesitter(self, node, content: str, symbols: List[ExtractedSymbol], edges: List[ExtractedEdge], current_scope: str):
        ntype = node.type
        if ntype in ("function_definition", "function_declaration"):
            name_node = node.child_by_field_name("name")
            if name_node:
                name = content[name_node.start_byte:name_node.end_byte]
                symbols.append(ExtractedSymbol(name=name, kind="function", start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1))
                current_scope = name
        elif ntype in ("class_definition", "class_declaration"):
            name_node = node.child_by_field_name("name")
            if name_node:
                name = content[name_node.start_byte:name_node.end_byte]
                symbols.append(ExtractedSymbol(name=name, kind="class", start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1))
                current_scope = name
        elif ntype in ("import_statement", "import_from_statement", "import_declaration"):
            text_slice = content[node.start_byte:node.end_byte].strip()
            edges.append(ExtractedEdge(from_symbol=current_scope, to_symbol=text_slice[:100], kind="import", line_number=node.start_point[0] + 1))
        elif ntype in ("call_expression", "call"):
            func_node = node.child_by_field_name("function")
            if func_node:
                callee_name = content[func_node.start_byte:func_node.end_byte]
                if len(callee_name) < 60 and "\n" not in callee_name:
                    edges.append(ExtractedEdge(from_symbol=current_scope, to_symbol=callee_name, kind="call", line_number=node.start_point[0] + 1))

        for child in node.children:
            self._traverse_treesitter(child, content, symbols, edges, current_scope)

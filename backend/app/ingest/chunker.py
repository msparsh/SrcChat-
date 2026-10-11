import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class CodeChunk:
    chunk_type: str # code, doc, summary
    symbol: Optional[str]
    start_line: int
    end_line: int
    text: str


class CodeChunker:
    """
    Intelligent chunker.
    Uses tree-sitter when grammar is available, falls back to sliding-window line/indentation chunker.
    """
    def __init__(self, max_chunk_lines: int = 120, min_chunk_lines: int = 10, overlap_lines: int = 15):
        self.max_chunk_lines = max_chunk_lines
        self.min_chunk_lines = min_chunk_lines
        self.overlap_lines = overlap_lines

    def chunk_file(
        self,
        repo_name: str,
        file_path: str,
        language: str,
        content: str
    ) -> List[CodeChunk]:
        if not content.strip():
            return []

        lines = content.splitlines()
        is_doc = language in ("markdown", "text") or file_path.lower().endswith((".md", ".txt", ".rst"))

        if is_doc:
            return self._chunk_markdown(repo_name, file_path, lines)

        # Attempt tree-sitter chunking if available
        chunks = self._chunk_with_treesitter(repo_name, file_path, language, content, lines)
        if chunks:
            return chunks

        # Attempt Python native AST chunking
        if language == "python" or file_path.endswith(".py"):
            py_chunks = self._chunk_with_python_ast(repo_name, file_path, content, lines)
            if py_chunks:
                return py_chunks

        # Fallback to sliding-window indentation-aware chunking
        return self._chunk_sliding_window(repo_name, file_path, language, lines)

    def _format_chunk_header(self, repo_name: str, file_path: str, language: str, symbol: Optional[str]) -> str:
        symbol_part = f" / {symbol}" if symbol else ""
        return f"# [{repo_name} / {file_path} / {language}{symbol_part}]\n"

    def _chunk_markdown(self, repo_name: str, file_path: str, lines: List[str]) -> List[CodeChunk]:
        chunks: List[CodeChunk] = []
        current_chunk_lines: List[str] = []
        current_start = 1
        current_header = None

        for idx, line in enumerate(lines, start=1):
            if re.match(r"^#{1,3}\s+", line) and len(current_chunk_lines) >= self.min_chunk_lines:
                text_body = "\n".join(current_chunk_lines)
                header = self._format_chunk_header(repo_name, file_path, "markdown", current_header)
                chunks.append(CodeChunk(
                    chunk_type="doc",
                    symbol=current_header,
                    start_line=current_start,
                    end_line=idx - 1,
                    text=header + text_body
                ))
                current_chunk_lines = [line]
                current_start = idx
                current_header = line.strip("# ").strip()
            else:
                if re.match(r"^#{1,3}\s+", line):
                    current_header = line.strip("# ").strip()
                current_chunk_lines.append(line)

        if current_chunk_lines:
            text_body = "\n".join(current_chunk_lines)
            header = self._format_chunk_header(repo_name, file_path, "markdown", current_header)
            chunks.append(CodeChunk(
                chunk_type="doc",
                symbol=current_header,
                start_line=current_start,
                end_line=len(lines),
                text=header + text_body
            ))
        return chunks

    def _chunk_with_python_ast(
        self,
        repo_name: str,
        file_path: str,
        content: str,
        lines: List[str]
    ) -> List[CodeChunk]:
        import ast
        try:
            tree = ast.parse(content)
        except Exception:
            return []

        chunks: List[CodeChunk] = []
        top_defs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        if not top_defs:
            return []

        first_start = top_defs[0].lineno
        if first_start > 2:
            preamble = "\n".join(lines[:first_start - 1])
            hdr = self._format_chunk_header(repo_name, file_path, "python", "module_preamble")
            chunks.append(CodeChunk(
                chunk_type="summary",
                symbol="module_preamble",
                start_line=1,
                end_line=first_start - 1,
                text=hdr + preamble
            ))

        for node in top_defs:
            s_line = node.lineno
            e_line = getattr(node, "end_lineno", s_line)
            slice_lines = lines[s_line - 1:e_line]
            sym_name = node.name
            hdr = self._format_chunk_header(repo_name, file_path, "python", sym_name)
            chunks.append(CodeChunk(
                chunk_type="code",
                symbol=sym_name,
                start_line=s_line,
                end_line=e_line,
                text=hdr + "\n".join(slice_lines)
            ))
        return chunks

    def _chunk_with_treesitter(
        self,
        repo_name: str,
        file_path: str,
        language: str,
        content: str,
        lines: List[str]
    ) -> List[CodeChunk]:
        try:
            from tree_sitter_languages import get_parser
            parser = get_parser(language)
            tree = parser.parse(bytes(content, "utf8"))
            root = tree.root_node
        except Exception:
            return []

        chunks: List[CodeChunk] = []
        top_level_definitions = []

        # Target node types for functions/classes/methods across languages
        target_types = {
            "function_definition", "class_definition", "method_definition",
            "function_declaration", "class_declaration", "method_declaration",
            "impl_item", "interface_declaration"
        }

        def find_top_level(node):
            for child in node.children:
                if child.type in target_types:
                    top_level_definitions.append(child)
                elif child.type in ("export_statement", "decorated_definition"):
                    # Inspect inner node
                    for sub in child.children:
                        if sub.type in target_types:
                            top_level_definitions.append(sub)

        find_top_level(root)

        if not top_level_definitions:
            return []

        # Create module summary chunk for top-level imports & module setup
        first_def_start = top_level_definitions[0].start_point[0] + 1
        if first_def_start > 5:
            module_lines = lines[:first_def_start - 1]
            header = self._format_chunk_header(repo_name, file_path, language, "module_preamble")
            chunks.append(CodeChunk(
                chunk_type="summary",
                symbol="module_preamble",
                start_line=1,
                end_line=first_def_start - 1,
                text=header + "\n".join(module_lines)
            ))

        for node in top_level_definitions:
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            
            # Find symbol name if available
            symbol_name = None
            name_node = node.child_by_field_name("name")
            if name_node:
                symbol_name = content[name_node.start_byte:name_node.end_byte]
            
            chunk_slice = lines[start_line - 1:end_line]

            # If unit is oversized, split sensibly
            if len(chunk_slice) > self.max_chunk_lines:
                sub_chunks = self._split_oversized(repo_name, file_path, language, symbol_name, chunk_slice, start_line)
                chunks.extend(sub_chunks)
            else:
                header = self._format_chunk_header(repo_name, file_path, language, symbol_name)
                chunks.append(CodeChunk(
                    chunk_type="code",
                    symbol=symbol_name,
                    start_line=start_line,
                    end_line=end_line,
                    text=header + "\n".join(chunk_slice)
                ))

        return chunks

    def _split_oversized(
        self,
        repo_name: str,
        file_path: str,
        language: str,
        symbol: Optional[str],
        lines: List[str],
        base_start_line: int
    ) -> List[CodeChunk]:
        sub_chunks: List[CodeChunk] = []
        i = 0
        total = len(lines)
        step = self.max_chunk_lines - self.overlap_lines

        while i < total:
            chunk_lines = lines[i:i + self.max_chunk_lines]
            start_l = base_start_line + i
            end_l = base_start_line + min(i + self.max_chunk_lines - 1, total - 1)
            sym_part = f"{symbol} (part {len(sub_chunks) + 1})" if symbol else None
            header = self._format_chunk_header(repo_name, file_path, language, sym_part)
            sub_chunks.append(CodeChunk(
                chunk_type="code",
                symbol=sym_part,
                start_line=start_l,
                end_line=end_l,
                text=header + "\n".join(chunk_lines)
            ))
            i += step
            if i + self.overlap_lines >= total and i < total:
                # Avoid tiny trailing slice
                break
        return sub_chunks

    def _chunk_sliding_window(
        self,
        repo_name: str,
        file_path: str,
        language: str,
        lines: List[str]
    ) -> List[CodeChunk]:
        chunks: List[CodeChunk] = []
        i = 0
        total = len(lines)
        step = max(self.max_chunk_lines - self.overlap_lines, 20)

        while i < total:
            chunk_lines = lines[i:i + self.max_chunk_lines]
            start_l = i + 1
            end_l = min(i + self.max_chunk_lines, total)
            header = self._format_chunk_header(repo_name, file_path, language, None)
            chunks.append(CodeChunk(
                chunk_type="code",
                symbol=None,
                start_line=start_l,
                end_line=end_l,
                text=header + "\n".join(chunk_lines)
            ))
            i += step
            if i + self.overlap_lines >= total and i < total:
                break
        return chunks

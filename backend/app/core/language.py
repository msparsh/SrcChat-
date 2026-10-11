import os
from typing import Optional

EXTENSION_MAP = {
    ".py": "python",
    ".pyw": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".markdown": "markdown",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".sql": "sql",
}

IGNORE_DIRECTORIES = {
    ".git", "node_modules", "vendor", "dist", "build", "target", ".venv", "venv",
    "env", ".next", ".nuxt", "__pycache__", ".pytest_cache", ".turbo", ".idea",
    ".vscode", "coverage", ".bundle", "bin", "obj"
}

IGNORE_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "gemfile.lock", "cargo.lock", "composer.lock", "go.sum"
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".bmp",
    ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar", ".exe", ".dll", ".so",
    ".dylib", ".class", ".jar", ".war", ".bin", ".dat", ".db", ".sqlite",
    ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3", ".wav", ".avi"
}

def detect_language(path: str, first_line: Optional[str] = None) -> str:
    """Detect language by extension and shebang fallback."""
    _, ext = os.path.splitext(path.lower())
    if ext in EXTENSION_MAP:
        return EXTENSION_MAP[ext]
    
    if first_line and first_line.startswith("#!"):
        shebang = first_line.lower()
        if "python" in shebang:
            return "python"
        if "node" in shebang or "js" in shebang:
            return "javascript"
        if "bash" in shebang or "sh" in shebang:
            return "bash"
        if "ruby" in shebang:
            return "ruby"
        if "perl" in shebang:
            return "perl"

    return "text"

def should_skip_file(rel_path: str, file_size_bytes: int, max_file_size_kb: int = 300) -> tuple[bool, str]:
    """
    Checks if a file should be skipped based on path, size, or binary type.
    Returns (should_skip, reason).
    """
    parts = rel_path.replace("\\", "/").split("/")
    for part in parts[:-1]:
        if part in IGNORE_DIRECTORIES:
            return True, f"ignored directory: {part}"
    
    filename = parts[-1]
    if filename.lower() in IGNORE_FILES:
        return True, "lockfile or package manifest lock"

    _, ext = os.path.splitext(filename.lower())
    if ext in BINARY_EXTENSIONS:
        return True, f"binary extension: {ext}"

    if file_size_bytes > (max_file_size_kb * 1024):
        return True, f"exceeds file size limit ({file_size_bytes / 1024:.1f} KB > {max_file_size_kb} KB)"

    return False, ""

"""Tools for reading and searching the CyberVPN codebase."""

from __future__ import annotations

import subprocess
from pathlib import Path

from crewai.tools import tool

PROJECT_ROOT = Path("/home/beep/projects/VPNBussiness")


@tool("read_project_file")
def read_project_file(file_path: str) -> str:
    """Read a file from the CyberVPN project. Provide path relative to project root.

    Example: read_project_file("backend/src/main.py")
    """
    full_path = PROJECT_ROOT / file_path
    if not full_path.exists():
        return f"File not found: {file_path}"
    if not full_path.resolve().is_relative_to(PROJECT_ROOT.resolve()):
        return "Access denied: path outside project root"
    try:
        content = full_path.read_text(encoding="utf-8")
        return content[:10000]  # Cap to manage context
    except Exception as e:
        return f"Error reading file: {e}"


@tool("search_codebase")
def search_codebase(pattern: str, file_glob: str = "**/*.py") -> str:
    """Search the CyberVPN codebase for a regex pattern. Returns matching file paths.

    Args:
        pattern: Regex pattern to search for.
        file_glob: File glob to filter (default: **/*.py).
    """
    try:
        result = subprocess.run(
            ["rg", "--files-with-matches", pattern, "--glob", file_glob],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout[:5000] if result.stdout else "No matches found"
    except FileNotFoundError:
        return "ripgrep (rg) not installed"
    except subprocess.TimeoutExpired:
        return "Search timed out"


@tool("list_project_files")
def list_project_files(directory: str = ".") -> str:
    """List files in a project directory. Provide path relative to project root.

    Example: list_project_files("backend/src/domain")
    """
    full_path = PROJECT_ROOT / directory
    if not full_path.exists():
        return f"Directory not found: {directory}"
    if not full_path.is_dir():
        return f"Not a directory: {directory}"

    entries = sorted(full_path.iterdir())
    lines = []
    for entry in entries[:100]:  # Cap at 100 entries
        prefix = "d " if entry.is_dir() else "f "
        lines.append(prefix + entry.name)
    return "\n".join(lines) if lines else "(empty directory)"

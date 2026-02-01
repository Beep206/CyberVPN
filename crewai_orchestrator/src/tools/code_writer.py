"""Tool for writing code files to disk."""

from __future__ import annotations

from pathlib import Path

from crewai.tools import tool

# Will be set by the flow before agents run
_output_dir: Path | None = None


def set_output_dir(path: Path) -> None:
    """Configure the output directory for code writing."""
    global _output_dir
    _output_dir = path
    _output_dir.mkdir(parents=True, exist_ok=True)


@tool("write_code_file")
def write_code_file(file_path: str, content: str) -> str:
    """Write a code file to the output directory.

    Args:
        file_path: Relative path within the output directory (e.g. "src/main.py").
        content: Full file content to write.

    Returns:
        Success or error message.
    """
    if _output_dir is None:
        return "Error: output directory not configured. Run with --implement --output-dir."

    target = (_output_dir / file_path).resolve()

    # Security: ensure path stays within output dir
    if not str(target).startswith(str(_output_dir.resolve())):
        return f"Access denied: path {file_path} escapes output directory."

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"OK: wrote {len(content)} bytes to {file_path}"
    except OSError as e:
        return f"Error writing {file_path}: {e}"

"""Safe repository file inspection.

Extracts and inspects a repository snapshot archive without executing any code.
All repository content is treated as untrusted input: path traversal and
archive bombs are guarded, binary files rejected, and extracted content is
temporary only.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

BINARY_MAGIC = b"\x00"
MAX_ENTRIES = 200_000
MAX_EXPANDED_BYTES = 1_000_000_000


class UnsafeArchiveError(Exception):
    pass


@dataclass
class InspectedFile:
    path: str
    extension: str | None
    language: str | None
    bytes: int
    lines: int
    category: str | None
    content_hash: str | None
    is_generated: bool
    content_preview: str | None = None


@dataclass
class InspectionResult:
    files: list[InspectedFile] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    languages: dict[str, int] = field(default_factory=dict)


GENERATED_MARKERS = {
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".next",
    ".venv",
    "venv",
    "target",
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    "coverage",
    ".terraform",
}

GENERATED_EXTENSIONS = {".min.js", ".min.css", ".map", ".lock"}

LANGUAGE_BY_EXT = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".rb": "Ruby",
    ".php": "PHP",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cs": "C#",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".sh": "Shell",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown",
    ".mdx": "Markdown",
    ".rst": "Markdown",
    ".vue": "Vue",
    ".dart": "Dart",
    ".tf": "Terraform",
}

CATEGORY_RULES = [
    ("test", re.compile(r"(^|/)(tests?|__tests__|spec|__tests__)/|(_test|\.test|\.spec)\.[^/]+$", re.I)),
    ("docs", re.compile(r"(^|/)docs?/|(readme|changelog|contributing|license|code_of_conduct)\.[^/]*$", re.I)),
    ("infra", re.compile(r"(^|/)(\.github|\.gitlab-ci|docker|deploy|infra|k8s|kube)/|(^|/)(dockerfile|compose\.ya?ml|\.github/workflows)/", re.I)),
    ("migration", re.compile(r"(migrations?|schema|alembic)/|\.sql$", re.I)),
    ("manifest", re.compile(r"(package\.json|pyproject\.toml|requirements\.txt|setup\.py|go\.mod|Cargo\.toml|Gemfile|composer\.json|pom\.xml|build\.gradle)$", re.I)),
    ("config", re.compile(r"(^|/)(\.env|\.env\.[a-z]+|\.github)/|(tsconfig\.json|setup\.cfg|\.eslintrc|\.prettierrc|jest\.config\.[cm]?js|vitest\.config\.[cm]?[jt]s|vite\.config\.[cm]?[jt]s)$", re.I)),
    ("ci", re.compile(r"(^|/)\.github/workflows/|(^|/)\.gitlab-ci\.yml$|(^|/)azure-pipelines", re.I)),
]


def is_generated_path(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    if any(p in GENERATED_MARKERS for p in parts):
        return True
    lower = path.lower()
    if any(lower.endswith(ext) for ext in GENERATED_EXTENSIONS):
        return True
    return False


def categorize(path: str) -> str | None:
    lower = path.lower()
    for category, pattern in CATEGORY_RULES:
        if pattern.search(lower):
            return category
    return None


def safe_join(root: Path, rel_path: str) -> Path:
    if "\x00" in rel_path:
        raise UnsafeArchiveError("NUL byte in archive entry path")
    candidate = (root / rel_path).resolve()
    root_resolved = root.resolve()
    if root_resolved not in candidate.parents and candidate != root_resolved:
        raise UnsafeArchiveError(f"Path traversal blocked: {rel_path}")
    return candidate


def _is_binary(data: bytes) -> bool:
    if not data:
        return False
    return BINARY_MAGIC in data[:4096]


def _count_lines(data: bytes) -> int:
    if _is_binary(data):
        return 0
    return data.count(b"\n") + 1


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _decode(data: bytes, path: str) -> str | None:
    if _is_binary(data):
        return None
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return None


def _infer_language(extension: str | None, path: str) -> str | None:
    if extension and extension.lower() in LANGUAGE_BY_EXT:
        return LANGUAGE_BY_EXT[extension.lower()]
    return None


def inspect_file_bytes(path: str, data: bytes, max_file_bytes: int) -> InspectedFile:
    is_generated = is_generated_path(path)
    if len(data) > max_file_bytes:
        data = data[:max_file_bytes]
    ext = os.path.splitext(path)[1].lower() or None
    text = _decode(data, path) if not is_generated else None
    preview = text[:2000] if text else None
    return InspectedFile(
        path=path,
        extension=ext,
        language=_infer_language(ext, path),
        bytes=len(data),
        lines=_count_lines(data),
        category=categorize(path),
        content_hash=_hash(data),
        is_generated=is_generated,
        content_preview=preview,
    )


def inspect_zip(archive: bytes, max_file_bytes: int) -> InspectionResult:
    result = InspectionResult()
    try:
        zf = zipfile.ZipFile(io.BytesIO(archive))
    except zipfile.BadZipFile:
        result.warnings.append("Archive is not a valid zip.")
        return result

    infolist = zf.infolist()
    if len(infolist) > MAX_ENTRIES:
        result.warnings.append("Archive entry count exceeds safety limit; truncated.")
        infolist = infolist[:MAX_ENTRIES]

    total = 0
    top_levels = set()
    for info in infolist:
        parts = [p for p in info.filename.split("/") if p]
        if parts and not info.is_dir():
            top_levels.add(parts[0])
    strip_top = len(top_levels) == 1

    for info in infolist:
        rel = info.filename
        total += info.file_size
        if total > MAX_EXPANDED_BYTES:
            result.warnings.append("Archive expansion exceeded safety limit; truncated.")
            break
        # strip leading directory segment introduced by GitHub zip naming
        parts = [p for p in rel.split("/") if p]
        if not parts:
            continue
        rel = "/".join(parts[1:] if strip_top else parts)
        if not rel or parts[0] == "__MACOSX" or info.is_dir():
            continue
        if is_generated_path(rel):
            result.files.append(
                InspectedFile(
                    path=rel,
                    extension=os.path.splitext(rel)[1].lower() or None,
                    language=None,
                    bytes=0,
                    lines=0,
                    category=None,
                    content_hash=None,
                    is_generated=True,
                )
            )
            continue
        try:
            data = zf.read(info)
        except Exception:
            result.warnings.append(f"Could not read entry: {rel}")
            continue
        if len(data) > max_file_bytes:
            result.warnings.append(f"File exceeded max size and was truncated: {rel}")
        result.files.append(inspect_file_bytes(rel, data, max_file_bytes))

    for f in result.files:
        if f.language and not f.is_generated:
            result.languages[f.language] = result.languages.get(f.language, 0) + 1
    return result


def inspect_directory(root: Path, max_file_bytes: int) -> InspectionResult:
    """Inspect a fixture directory (no archive)."""
    result = InspectionResult()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in GENERATED_MARKERS]
        for filename in filenames:
            full = Path(dirpath) / filename
            rel = full.relative_to(root).as_posix()
            if is_generated_path(rel):
                result.files.append(
                    InspectedFile(
                        path=rel,
                        extension=os.path.splitext(filename)[1].lower() or None,
                        language=None,
                        bytes=0,
                        lines=0,
                        category=None,
                        content_hash=None,
                        is_generated=True,
                    )
                )
                continue
            try:
                data = full.read_bytes()
            except OSError:
                continue
            if len(data) > max_file_bytes:
                result.warnings.append(f"File exceeded max size and was truncated: {rel}")
            result.files.append(inspect_file_bytes(rel, data, max_file_bytes))
    for f in result.files:
        if f.language and not f.is_generated:
            result.languages[f.language] = result.languages.get(f.language, 0) + 1
    return result
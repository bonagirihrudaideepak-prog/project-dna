"""Unit tests for file inspection and safety."""

import zipfile
from io import BytesIO

import pytest

from app.domain.analysis.inspector import (
    UnsafeArchiveError,
    categorize,
    inspect_file_bytes,
    inspect_zip,
    is_generated_path,
    safe_join,
)


def test_categorize():
    assert categorize("src/tests/test_app.py") == "test"
    assert categorize("docs/README.md") == "docs"
    assert categorize("package.json") == "manifest"
    assert categorize("src/app.py") is None


def test_generated_path():
    assert is_generated_path("node_modules/lodash/index.js")
    assert is_generated_path("src/app.min.js")
    assert not is_generated_path("src/app.py")


def test_binary_rejected():
    data = b"\x00\x01\x02binary\x00"
    f = inspect_file_bytes("blob.bin", data, 1024 * 1024)
    assert f.language is None


def test_safe_join_blocks_traversal():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        with pytest.raises(UnsafeArchiveError):
            safe_join(root, "../escape.txt")


def test_zip_roundtrip():
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("repo/README.md", "# Hello")
        zf.writestr("repo/src/app.py", "print('x')\n")
    result = inspect_zip(buf.getvalue(), 1024 * 1024)
    paths = {f.path for f in result.files}
    assert "README.md" in paths or "src/app.py" in paths
    assert result.languages.get("Python") == 1

"""Seed fixture projects into the database so the demo works offline."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal, init_db  # noqa: E402
from app.models import Project  # noqa: E402


def seed():
    init_db()
    fixture_root = Path(os.environ.get("FIXTURE_ROOT", "./fixtures"))
    db = SessionLocal()
    try:
        if not fixture_root.exists():
            print("fixture root not found", fixture_root)
            return
        for d in sorted(fixture_root.iterdir()):
            manifest = d / "manifest.json"
            if not manifest.exists():
                continue
            data = json.loads(manifest.read_text())
            existing = db.query(Project).filter(Project.full_name == data["full_name"]).first()
            if existing:
                print(f"exists: {data['full_name']}")
                continue
            project = Project(
                full_name=data["full_name"],
                owner=data["owner"],
                name=data["name"],
                default_branch=data.get("default_branch", "main"),
                visibility="public",
                description=data.get("description"),
                is_fixture=True,
            )
            db.add(project)
            print(f"seeded: {data['full_name']}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()

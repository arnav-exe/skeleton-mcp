from __future__ import annotations

import json
from pathlib import Path

from skeleton_mcp.models import IndexSnapshot


def load_snapshot(cache_path: Path) -> IndexSnapshot | None:
    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return IndexSnapshot.from_dict(data)


def save_snapshot(cache_path: Path, snapshot: IndexSnapshot) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(snapshot.to_dict(), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

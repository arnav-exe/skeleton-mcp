from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    cache_dir: Path = Path(".cache") / "skeleton_mcp"
    cache_file: str = "index.json"
    index_ttl_seconds: int = 60 * 60 * 6
    refresh_timeout_seconds: int = 30
    max_chunk_chars: int = 2400
    max_excerpt_chars: int = 4000
    default_top_k: int = 8
    docs_index_url: str = "https://www.skeleton.dev/llms.txt"


settings = Settings()


def get_cache_path() -> Path:
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    return settings.cache_dir / settings.cache_file

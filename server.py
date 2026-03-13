from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from skeleton_mcp.config import settings
from skeleton_mcp.service import SkeletonDocsService


mcp = FastMCP("skeleton-docs-mcp")
service = SkeletonDocsService()


@mcp.tool()
def list_docs(framework: str | None = None) -> dict[str, object]:
    """list available skeleton docs."""
    return service.list_docs(framework=framework)


@mcp.tool()
def search_docs(
    query: str,
    framework: str | None = None,
    section: str | None = None,
    top_k: int = settings.default_top_k,
) -> dict[str, object]:
    """search docs with lexical ranking."""
    return service.search_docs(query=query, framework=framework, section=section, top_k=top_k)


@mcp.tool()
def get_doc(path_or_slug: str) -> dict[str, object]:
    """get full doc by id or title."""
    return service.get_doc(path_or_slug=path_or_slug)


@mcp.tool()
def get_excerpt(query: str, top_k: int = 5, max_chars: int = settings.max_excerpt_chars) -> dict[str, object]:
    """get compact excerpts for a query."""
    return service.get_excerpt(query=query, top_k=top_k, max_chars=max_chars)


@mcp.tool()
def refresh_index(force: bool = False) -> dict[str, object]:
    """refresh local docs index cache."""
    return service.refresh_index(force=force)


if __name__ == "__main__":
    mcp.run(transport="stdio")

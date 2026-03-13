# skeleton-mcp

MCP server for frontend library [Skeleton](https://www.skeleton.dev/). Built using FastMCP

## features

- pulls source from Skeleton LLM endpoints (`/llms.txt`, `/llms-*.txt`)
- creates local cache
- stdio transport for local MCP clients

## install

1. `pip install -r requirements.txt`

## tools

- `list_docs(framework)`
- `search_docs(query, framework, section, top_k)`
- `get_doc(path_or_slug)`
- `get_excerpt(query, top_k, max_chars)`
- `refresh_index(force)`


from __future__ import annotations

import re

import httpx


def fetch_text(url: str, timeout_seconds: int) -> str:
    with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def extract_llm_file_urls(index_text: str) -> list[str]:
    urls = sorted(set(re.findall(r"https://www\.skeleton\.dev/llms[-\w]*\.txt", index_text)))
    if urls:
        return urls

    # fallback if index format changes
    known = [
        "https://www.skeleton.dev/llms-full.txt",
        "https://www.skeleton.dev/llms-svelte.txt",
        "https://www.skeleton.dev/llms-react.txt",
    ]
    return known

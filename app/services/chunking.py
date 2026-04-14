from __future__ import annotations

from typing import Iterable


def normalize_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip()


def chunk_text(text: str, max_chars: int = 800, overlap: int = 120) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)

        if len(paragraph) <= max_chars:
            current = paragraph
            continue

        start = 0
        while start < len(paragraph):
            end = min(start + max_chars, len(paragraph))
            piece = paragraph[start:end].strip()
            if piece:
                chunks.append(piece)
            if end >= len(paragraph):
                break
            start = max(0, end - overlap)
        current = ""

    if current:
        chunks.append(current)
    return chunks


def batched(items: Iterable[str], size: int) -> list[list[str]]:
    batch: list[str] = []
    all_batches: list[list[str]] = []
    for item in items:
        batch.append(item)
        if len(batch) == size:
            all_batches.append(batch)
            batch = []
    if batch:
        all_batches.append(batch)
    return all_batches

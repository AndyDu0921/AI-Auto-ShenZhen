from __future__ import annotations

import math
import re
from typing import Any

from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from app.models import Chunk

TOKEN_RE = re.compile(r"[A-Za-z0-9_./-]+|[\u4e00-\u9fff]+")



def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]



def search_chunks(db: Session, query: str, limit: int = 5) -> list[dict[str, Any]]:
    chunks = db.query(Chunk).all()
    if not chunks:
        return []

    tokenized_corpus = [tokenize(chunk.content) for chunk in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    query_tokens = tokenize(query)
    scores = bm25.get_scores(query_tokens)

    results: list[tuple[float, Chunk]] = []
    for score, chunk in zip(scores, chunks):
        normalized = chunk.content.lower()
        boost = 0.0
        for token in query_tokens:
            if token and token in normalized:
                boost += 0.15
        final_score = float(score) + boost + math.log(len(chunk.content) + 10, 10) * 0.02
        results.append((final_score, chunk))

    results.sort(key=lambda item: item[0], reverse=True)
    top = []
    for score, chunk in results[:limit]:
        top.append(
            {
                "score": round(score, 4),
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "source_label": chunk.source_label,
                "content": chunk.content,
            }
        )
    return top

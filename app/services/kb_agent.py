from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Chunk, Document
from app.services.chunking import chunk_text
from app.services.document_parser import extract_text_from_upload
from app.services.llm import LLMClient
from app.services.retrieval import search_chunks


settings = get_settings()
llm_client = LLMClient(settings)



def ingest_document(db: Session, file_name: str, file_bytes: bytes) -> Document:
    text = extract_text_from_upload(file_name, file_bytes)
    title = Path(file_name).stem
    doc = Document(
        file_name=file_name,
        title=title,
        file_type=Path(file_name).suffix.lower().lstrip("."),
        text_content=text,
    )
    db.add(doc)
    db.flush()

    for idx, content in enumerate(chunk_text(text, settings.max_chunk_chars, settings.chunk_overlap_chars)):
        db.add(
            Chunk(
                document_id=doc.id,
                chunk_index=idx,
                content=content,
                source_label=f"{doc.title}#{idx + 1}",
            )
        )

    db.commit()
    db.refresh(doc)
    return doc



def answer_question(db: Session, question: str) -> dict[str, Any]:
    hits = search_chunks(db, question, limit=settings.top_k_chunks)
    if not hits:
        return {
            "answer": "当前知识库还是空的。先上传产品手册、FAQ、认证文件或报价规则，再来提问。",
            "sources": [],
        }

    if llm_client.enabled:
        context = "\n\n".join(f"[Source: {hit['source_label']}]\n{hit['content']}" for hit in hits)
        answer = llm_client.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a sales enablement knowledge assistant for a Shenzhen factory/exporter. "
                        "Answer only from the provided context. If the answer is incomplete, state what is missing."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nContext:\n{context}",
                },
            ]
        )
        return {"answer": answer.strip(), "sources": hits}

    bullets = []
    for hit in hits[:3]:
        snippet = hit["content"].strip().replace("\n", " ")
        bullets.append(f"- {snippet[:220]}")
    answer = (
        "MVP 当前处于 mock 模式，以下是知识库里最相关的内容，足够给销售或客服先用：\n\n"
        + "\n".join(bullets)
        + "\n\n如果你接入真实模型，系统会自动把这些片段整理成更自然的答案。"
    )
    return {"answer": answer, "sources": hits}

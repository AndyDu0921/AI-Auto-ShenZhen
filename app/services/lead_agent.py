from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Inquiry
from app.services.heuristics import analysis_to_text, analyze_inquiry_with_rules
from app.services.llm import LLMClient
from app.services.retrieval import search_chunks


settings = get_settings()
llm_client = LLMClient(settings)


LEAD_SCHEMA = {
    "lead_grade": "A/B/C/D",
    "lead_score": "0-100",
    "trust_signals": ["short reasons"],
    "specs": {
        "model": "string if present",
        "quantity": "string if present",
        "target_market": "string if present",
        "certification": ["list"]
    },
    "missing_fields": ["list of missing fields"],
    "suggested_action": "string",
    "reply_subject": "string",
    "reply_body_en": "string"
}



def _build_llm_messages(payload: dict[str, Any], kb_context: list[dict[str, Any]]) -> list[dict[str, str]]:
    context_block = "\n\n".join(
        f"[Source: {hit['source_label']}]\n{hit['content']}" for hit in kb_context
    )
    user_block = json.dumps(payload, ensure_ascii=False, indent=2)
    return [
        {
            "role": "system",
            "content": (
                "You are an AI sales operations agent for a Shenzhen exporter. "
                "Classify inbound inquiries, extract specs, detect missing info, write the first English reply, "
                "and return valid JSON only. Keep the reply concise, credible, and commercially useful.\n\n"
                f"Output schema: {json.dumps(LEAD_SCHEMA, ensure_ascii=False)}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Inquiry payload:\n{user_block}\n\n"
                f"Knowledge context:\n{context_block or 'No product knowledge uploaded.'}"
            ),
        },
    ]



def process_inquiry(db: Session, payload: dict[str, Any]) -> Inquiry:
    query_text = "\n".join(filter(None, [payload.get("subject"), payload.get("body"), payload.get("company")]))
    kb_context = search_chunks(db, query_text, limit=settings.top_k_chunks)

    if llm_client.enabled:
        messages = _build_llm_messages(payload, kb_context)
        raw = llm_client.chat_json(messages)
        lead_score = int(raw.get("lead_score", 0) or 0)
        lead_grade = str(raw.get("lead_grade", "C") or "C")
        suggested_action = raw.get("suggested_action") or "Review manually."
        reply_subject = raw.get("reply_subject") or f"Re: {payload.get('subject') or 'your inquiry'}"
        reply_body_en = raw.get("reply_body_en") or "Thank you for your inquiry."
        analysis = raw
        analysis["matched_knowledge"] = [
            {"source": hit["source_label"], "score": hit["score"]} for hit in kb_context
        ]
        analysis_text = json.dumps(analysis, ensure_ascii=False, indent=2)
    else:
        result = analyze_inquiry_with_rules(payload, settings, kb_context)
        lead_score = result.score
        lead_grade = result.grade
        suggested_action = result.action
        reply_subject = result.reply_subject
        reply_body_en = result.reply_body_en
        analysis_text = analysis_to_text(result.analysis)

    inquiry = Inquiry(
        source_channel=payload.get("source_channel") or "form",
        sender_name=payload.get("sender_name"),
        sender_email=payload.get("sender_email"),
        company=payload.get("company"),
        subject=payload.get("subject"),
        body=payload.get("body") or "",
        lead_score=lead_score,
        lead_grade=lead_grade,
        suggested_action=suggested_action,
        reply_subject=reply_subject,
        reply_body_en=reply_body_en,
        analysis_json=analysis_text,
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)
    return inquiry

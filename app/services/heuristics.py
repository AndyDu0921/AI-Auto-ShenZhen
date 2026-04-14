from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from app.config import Settings

FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "outlook.com",
    "hotmail.com",
    "yahoo.com",
    "qq.com",
    "163.com",
    "126.com",
    "foxmail.com",
}

SPEC_PATTERNS = {
    "model": r"(?:model|型号)\s*[:：\-]?\s*([A-Za-z0-9\-_/]+)",
    "quantity": r"(?:(?:qty|quantity|数量)\s*[:：\-]?\s*([0-9,]+)|([0-9,]+)\s*(?:pcs|pieces|sets|units))",
    "target_market": r"(?:(?:market|destination|country|国家|市场)\s*[:：\-]?\s*([A-Za-z ,/]+)|for\s+([A-Za-z ]+)\s+market)",
    "voltage": r"([0-9]{2,3}V(?:/[0-9]{2,3}V)?)",
    "certification": r"(?:CE|FCC|RoHS|UL|ETL|MSDS|UN38\.3)",
}


@dataclass
class LeadResult:
    score: int
    grade: str
    action: str
    analysis: dict[str, Any]
    reply_subject: str
    reply_body_en: str



def _extract_email_domain(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    return email.split("@", 1)[1].lower().strip()



def _parse_specs(text: str) -> tuple[dict[str, Any], list[str]]:
    specs: dict[str, Any] = {}
    missing: list[str] = []
    for field, pattern in SPEC_PATTERNS.items():
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if not matches:
            if field in {"model", "quantity", "target_market"}:
                missing.append(field)
            continue
        if field == "certification":
            specs[field] = sorted({m.upper() for m in matches})
        elif isinstance(matches[0], tuple):
            specs[field] = next((m.strip() for m in matches[0] if m), "")
        else:
            specs[field] = matches[0]
    return specs, missing



def _score_lead(company: str | None, sender_email: str | None, body: str, specs: dict[str, Any]) -> tuple[int, list[str]]:
    reasons: list[str] = []
    score = 35

    domain = _extract_email_domain(sender_email)
    if domain:
        if domain in FREE_EMAIL_DOMAINS:
            reasons.append("Uses a generic mailbox, which lowers trust slightly.")
        else:
            score += 20
            reasons.append("Uses a corporate email domain.")
    else:
        reasons.append("No sender email was provided.")

    if company:
        score += 10
        reasons.append("Company name is available.")

    body_len = len(body.strip())
    if body_len > 200:
        score += 10
        reasons.append("Message has enough detail for qualification.")
    elif body_len < 60:
        reasons.append("Message is short and may need clarification.")

    if "quantity" in specs:
        try:
            qty = int(str(specs["quantity"]).replace(",", ""))
            if qty >= 1000:
                score += 15
                reasons.append("Quantity indicates real buying intent.")
            elif qty >= 100:
                score += 8
                reasons.append("Quantity suggests moderate buying intent.")
        except ValueError:
            pass

    if "model" in specs:
        score += 8
        reasons.append("Specific model information is present.")

    if "certification" in specs:
        score += 5
        reasons.append("Certification requirements are mentioned.")

    score = max(5, min(100, score))
    return score, reasons



def _grade(score: int) -> str:
    if score >= 80:
        return "A"
    if score >= 65:
        return "B"
    if score >= 45:
        return "C"
    return "D"



def _next_action(grade: str, missing: list[str]) -> str:
    if grade in {"A", "B"} and not missing:
        return "Push to sales within 15 minutes, send quote prep checklist, and arrange human follow-up."
    if grade in {"A", "B"}:
        return f"Reply immediately and ask for missing info: {', '.join(missing)}. Human follow-up within 30 minutes."
    if grade == "C":
        return f"Auto-reply with clarification questions, then queue for same-day review. Missing info: {', '.join(missing) or 'n/a'}."
    return "Send a polite clarification template. Review only if the customer responds with product, quantity, or company details."



def _build_reply(subject: str | None, sender_name: str | None, company_name: str, specs: dict[str, Any], missing: list[str], settings: Settings, kb_context: list[dict[str, Any]]) -> tuple[str, str]:
    greet_name = sender_name or "there"
    product_ref = specs.get("model") or "the requested product"
    qty_ref = specs.get("quantity") or "your target quantity"
    cert_ref = ", ".join(specs.get("certification", [])) if isinstance(specs.get("certification"), list) else specs.get("certification")
    cert_line = f" We can also review certification needs such as {cert_ref}." if cert_ref else ""

    knowledge_hint = ""
    if kb_context:
        first = kb_context[0]["content"].split("\n", 1)[0][:180]
        knowledge_hint = f" Based on our current product notes: {first}."

    ask_block = ""
    if missing:
        ask_block = "To move to quotation quickly, please share: " + ", ".join(missing) + "."

    reply_subject = f"Re: {subject}" if subject else "Re: your inquiry"
    reply_body = (
        f"Dear {greet_name},\n\n"
        f"Thank you for your inquiry to {company_name}. We have received your request for {product_ref}"
        f" and the current target quantity is {qty_ref}.{cert_line}{knowledge_hint}\n\n"
        f"{ask_block}\n\n"
        "Once we receive the remaining details, we can prepare the first quotation and lead time suggestion promptly.\n\n"
        f"{settings.reply_signature}"
    ).strip()
    return reply_subject, reply_body



def analyze_inquiry_with_rules(
    payload: dict[str, Any],
    settings: Settings,
    kb_context: list[dict[str, Any]],
) -> LeadResult:
    subject = payload.get("subject") or ""
    body = payload.get("body") or ""
    merged = f"{subject}\n{body}"
    specs, missing = _parse_specs(merged)
    score, reasons = _score_lead(payload.get("company"), payload.get("sender_email"), body, specs)
    grade = _grade(score)
    action = _next_action(grade, missing)
    reply_subject, reply_body = _build_reply(
        subject=payload.get("subject"),
        sender_name=payload.get("sender_name"),
        company_name=settings.company_name,
        specs=specs,
        missing=missing,
        settings=settings,
        kb_context=kb_context,
    )

    analysis = {
        "lead_grade": grade,
        "lead_score": score,
        "trust_signals": reasons,
        "specs": specs,
        "missing_fields": missing,
        "suggested_action": action,
        "matched_knowledge": [
            {
                "source": hit["source_label"],
                "score": hit["score"],
            }
            for hit in kb_context
        ],
    }
    return LeadResult(
        score=score,
        grade=grade,
        action=action,
        analysis=analysis,
        reply_subject=reply_subject,
        reply_body_en=reply_body,
    )



def analysis_to_text(analysis: dict[str, Any]) -> str:
    return json.dumps(analysis, ensure_ascii=False, indent=2)

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Base, engine, get_db
from app.models import Document, Inquiry
from app.schemas import AskRequest, DocumentRead, InquiryCreate, InquiryRead
from app.services.kb_agent import answer_question, ingest_document
from app.services.lead_agent import process_inquiry


settings = get_settings()
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/api/health")
def health() -> dict[str, str | bool]:
    return {
        "app": settings.app_name,
        "mock_mode": settings.use_mock_llm or not bool(settings.llm_api_key),
        "model": settings.llm_model,
        "base_url": settings.llm_base_url,
    }


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    inquiries = db.query(Inquiry).order_by(Inquiry.created_at.desc()).limit(10).all()
    documents = db.query(Document).order_by(Document.created_at.desc()).limit(10).all()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "settings": settings,
            "inquiries": inquiries,
            "documents": documents,
        },
    )


@app.post("/api/inquiries", response_model=InquiryRead)
def create_inquiry(payload: InquiryCreate, db: Session = Depends(get_db)):
    inquiry = process_inquiry(db, payload.model_dump())
    return inquiry


@app.post("/api/inquiries/form", response_model=InquiryRead)
def create_inquiry_form(
    source_channel: str = Form("form"),
    sender_name: str | None = Form(None),
    sender_email: str | None = Form(None),
    company: str | None = Form(None),
    subject: str | None = Form(None),
    body: str = Form(...),
    db: Session = Depends(get_db),
):
    inquiry = process_inquiry(
        db,
        {
            "source_channel": source_channel,
            "sender_name": sender_name,
            "sender_email": sender_email,
            "company": company,
            "subject": subject,
            "body": body,
        },
    )
    return inquiry


@app.get("/api/inquiries", response_model=list[InquiryRead])
def list_inquiries(db: Session = Depends(get_db)):
    return db.query(Inquiry).order_by(Inquiry.created_at.desc()).all()


@app.get("/api/inquiries/{inquiry_id}", response_model=InquiryRead)
def get_inquiry(inquiry_id: int, db: Session = Depends(get_db)):
    inquiry = db.get(Inquiry, inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    return inquiry


@app.post("/api/docs/upload", response_model=DocumentRead)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_bytes = await file.read()
    try:
        doc = ingest_document(db, file.filename or "upload.txt", file_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return doc


@app.get("/api/docs", response_model=list[DocumentRead])
def list_documents(db: Session = Depends(get_db)):
    return db.query(Document).order_by(Document.created_at.desc()).all()


@app.post("/api/ask")
def ask_question(payload: AskRequest, db: Session = Depends(get_db)):
    return answer_question(db, payload.question)


@app.post("/api/demo/seed")
def seed_demo(db: Session = Depends(get_db)):
    sample_dir = Path(__file__).resolve().parents[1] / "sample_data"
    loaded = []
    for path in sample_dir.glob("*"):
        if path.is_file():
            existing = db.query(Document).filter(Document.file_name == path.name).first()
            if existing:
                continue
            ingest_document(db, path.name, path.read_bytes())
            loaded.append(path.name)
    return {"loaded": loaded, "count": len(loaded)}

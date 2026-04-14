from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
from docx import Document as DocxDocument
from pypdf import PdfReader


SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf", ".docx", ".csv", ".xlsx"}


class UnsupportedFileTypeError(ValueError):
    pass



def extract_text_from_upload(file_name: str, file_bytes: bytes) -> str:
    suffix = Path(file_name).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise UnsupportedFileTypeError(f"Unsupported file type: {suffix}")

    if suffix in {".txt", ".md"}:
        return file_bytes.decode("utf-8", errors="ignore")

    if suffix == ".pdf":
        reader = PdfReader(BytesIO(file_bytes))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)

    if suffix == ".docx":
        doc = DocxDocument(BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    if suffix == ".csv":
        df = pd.read_csv(BytesIO(file_bytes))
        return df.to_csv(index=False)

    if suffix == ".xlsx":
        excel = pd.ExcelFile(BytesIO(file_bytes))
        sheets: list[str] = []
        for sheet_name in excel.sheet_names:
            df = excel.parse(sheet_name)
            sheets.append(f"# Sheet: {sheet_name}\n{df.to_csv(index=False)}")
        return "\n\n".join(sheets)

    raise UnsupportedFileTypeError(f"Unsupported file type: {suffix}")

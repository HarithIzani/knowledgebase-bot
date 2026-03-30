from pathlib import Path
from docx import Document
from pypdf import PdfReader

def extract_text_from_txt(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8", errors="ignore")

def extract_text_from_pdf(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)

    return "\n".join(pages)

def extract_text_from_docx(file_path: Path) -> str:
    doc = Document(str(file_path))
    paragraphs = [paragraph.text for paragraph in doc.paragraphs]

    return "\n".join(paragraphs)

def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    if suffix == ".txt":
        return extract_text_from_txt(file_path)
    
    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    
    if suffix == ".docx":
        return extract_text_from_docx(file_path)
    
    raise ValueError(f"Unsupported file type: {suffix}")

def normalize_text(text: str) -> str:
    lines = text.splitlines()
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    return "\n".join(cleaned_lines)

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    if not text:
        return []
    
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks
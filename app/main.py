from pathlib import Path
import uuid
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db import (
    init_db,
    insert_document,
    list_documents,
    insert_chunks,
    get_chunks_for_document,
    search_chunks
)
from app.ingestion import extract_text, normalize_text, chunk_text
from app.db import search_chunk_texts
from app.llm import ask_ollama

# --------------------------------------------------
# Paths
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "app" / "templates"
STATIC_DIR = BASE_DIR / "app" / "static"
UPLOADS_DIR = BASE_DIR / "data" / "uploads"

# Make sure the uploads folder exists
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# App setup
# --------------------------------------------------
app = FastAPI(title="Knowledgebase Bot", version="1.0")

# Serve static files like CSS from /static
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Tell FastAPI where our HTML templates live
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Initialize the database when the app starts
@app.on_event("startup")
def startup():
    init_db()

# --------------------------------------------------
# Helper function
# --------------------------------------------------
def list_uploaded_files() -> list[str]:
    files = []
    for item in UPLOADS_DIR.iterdir():
        if item.is_file():
            files.append(item.name)
    return sorted(files)


# --------------------------------------------------
# Routes
# --------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    documents = list_documents()
    return templates.TemplateResponse(
        request,
        "index.html",
        {"request": request, "documents": documents},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    for uploaded_file in files:
        if not uploaded_file.filename:
            continue

        # Generate a unique ID for the document
        doc_id = str(uuid.uuid4())

        # Create safe filename
        extension = Path(uploaded_file.filename).suffix.lower()
        filename = f"{doc_id}{extension}"

        destination = UPLOADS_DIR / filename

        file_bytes = await uploaded_file.read()
        destination.write_bytes(file_bytes)

        # Save metadata to the database
        insert_document(
            doc_id=doc_id,
            filename=filename,
            original_name=uploaded_file.filename
        )

        try:
            raw_text = extract_text(destination)
            clean_text = normalize_text(raw_text)
            chunks = chunk_text(clean_text)

            if chunks:
                insert_chunks(doc_id, chunks)

        except ValueError:
            pass  # Unsupported file type, skip chunking

    return RedirectResponse(url="/", status_code=303)


@app.get("/documents/{document_id}/chunks")
async def show_document_chunks(document_id: str):
    chunks = get_chunks_for_document(document_id)

    return {
        "document_id": document_id,
        "chunk_count": len(chunks),
        "chunks": [
            {
                "chunk_index": row["chunk_index"],
                "content": row["content"],
            }
            for row in chunks
        ],
    }

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    return templates.TemplateResponse(
        request,
        "search.html",
        {
            "request": request,
            "results": [],
            "query": "",
        },
    )

@app.post("/search", response_class=HTMLResponse)
async def run_search(request: Request):
    form = await request.form()
    query = str(form.get("query", "")).strip()

    results = []
    if query:
        try:
            results = search_chunks(query)
        except Exception:
            results = []

    return templates.TemplateResponse(
        request,
        "search.html",
        {
            "request": request,
            "results": results,
            "query": query,
        },
    )

@app.get("/ask", response_class=HTMLResponse)
async def ask_page(request: Request):
    return templates.TemplateResponse(
        request,
        "ask.html",
        {
            "request": request,
            "question": "",
            "answer": "",
            "results": [],
        },
    )


@app.post("/ask", response_class=HTMLResponse)
async def run_ask(request: Request):
    form = await request.form()
    question = str(form.get("question", "")).strip()

    answer = ""
    results = []

    if question:
        try:
            results = search_chunks(question, limit=5)
            context_chunks = [row["content"] for row in results]

            if context_chunks:
                answer = await ask_ollama(question, context_chunks)
            else:
                answer = "I couldn't find that in the uploaded documents."

        except Exception as exc:
            answer = f"Error: {str(exc)}"

    return templates.TemplateResponse(
        request,
        "ask.html",
        {
            "request": request,
            "question": question,
            "answer": answer,
            "results": results,
        },
    )

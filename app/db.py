import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "app.db"

# --------------------------------------------------
# Intializing the database and helper functions
# --------------------------------------------------
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        doc_id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        original_name TEXT NOT NULL,
        uploaded_at TEXT NOT NULL
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES documents(doc_id)
    )
    """)

    conn.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts
    USING fts5(
        content,
        document_id UNINDEXED,
        chunk_index UNINDEXED
    )
    """)

    conn.commit()
    conn.close()

# --------------------------------------------------
# Insert functions
# --------------------------------------------------
def insert_document(doc_id: str, filename: str, original_name: str):
    conn = get_connection()

    conn.execute(
        """
        INSERT INTO documents (doc_id, filename, original_name, uploaded_at)
        VALUES (?, ?, ?, ?)
        """,
        (doc_id, filename, original_name, datetime.utcnow().isoformat())
    )

    conn.commit()
    conn.close()

def insert_chunks(document_id: str, chunks: list[str]):
    conn = get_connection()

    chunk_rows = [
        (document_id, index, chunk)
        for index, chunk in enumerate(chunks)
    ]

    conn.executemany(
        """
        INSERT INTO chunks (document_id, chunk_index, content)
        VALUES (?, ?, ?)
        """,
        chunk_rows
    )

    conn.executemany(
        """
        INSERT INTO chunk_fts (content, document_id, chunk_index)
        VALUES (?, ?, ?)
        """,
        [
            (chunk, document_id, index)
            for index, chunk in enumerate(chunks)
        ]
    )

    conn.commit()
    conn.close()

# --------------------------------------------------
# Query functions
# --------------------------------------------------
def list_documents():
    conn = get_connection()

    rows = conn.execute(
        "SELECT * FROM documents ORDER BY uploaded_at DESC"
    ).fetchall()

    conn.close()

    return rows

def sanitize_fts_query(query: str) -> str:
    return " ".join(query.replace('"', " ").split())

def get_chunks_for_document(doc_id):
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT * FROM chunks
        WHERE document_id = ?
        ORDER BY chunk_index ASC
        """,
        (doc_id,)
    ).fetchall()

    conn.close()
    return rows

def search_chunks(query: str, limit: int = 5):
    conn = get_connection()

    query = sanitize_fts_query(query)

    rows = conn.execute(
        """
        SELECT
            chunk_fts.rowid,
            chunk_fts.content,
            chunk_fts.document_id,
            chunk_fts.chunk_index,
            documents.original_name
        FROM chunk_fts
        JOIN documents
          ON documents.doc_id = chunk_fts.document_id
        WHERE chunk_fts MATCH ?
        LIMIT ?
        """,
        (query, limit)
    ).fetchall()

    conn.close()
    return rows

def search_chunk_texts(query: str, limit: int = 5) -> list[str]:
    rows = search_chunks(query, limit=limit)
    return [row["content"] for row in rows]
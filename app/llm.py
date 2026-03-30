import httpx


import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = "llama3.2"


def build_prompt(question: str, context_chunks: list[str]) -> str:
    context_text = "\n\n---\n\n".join(context_chunks)

    return f"""
You are a helpful assistant answering questions about uploaded documents.

Use only the provided context to answer the question.
If the answer is not in the context, say:
"I couldn't find that in the uploaded documents."

Context:
{context_text}

Question:
{question}
""".strip()


async def ask_ollama(question: str, context_chunks: list[str]) -> str:
    prompt = build_prompt(question, context_chunks)

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "stream": False,
        "keep_alive": "10m",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    return data["message"]["content"].strip()
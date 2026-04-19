import os
import logging
from typing import List, Tuple

import anthropic

from app.core.config import get_settings
from app.services.retrieval_service import RetrievedChunk
from app.schemas.query import CitationSource

settings = get_settings()
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are LexQuery, an AI legal research assistant.

Your job is to answer questions about legal documents accurately and concisely.

STRICT RULES:
1. Answer ONLY using information from the provided document passages.
2. Every factual claim must be followed by a citation number [1], [2], etc.
3. If the passages do not contain enough information to answer, say so clearly.
4. Never speculate, infer, or add information not present in the passages.
5. Keep your answer focused and professional.
6. Always end with: "Note: This is not legal advice."

FORMAT:
- Write in clear, plain English
- Use citation numbers inline: "The contract requires 30 days notice [1]."
- If multiple passages support a claim, cite all of them: [1][2]
"""


def build_context(chunks: List[RetrievedChunk]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        parts.append(
            f"[{i}] Source: {chunk.filename}, Page {chunk.page_number}\n"
            f"{chunk.text}"
        )
    return "\n\n---\n\n".join(parts)


def compute_confidence(chunks: List[RetrievedChunk]) -> Tuple[float, str]:
    if not chunks:
        return 0.0, "Insufficient"
    avg_score = sum(c.score for c in chunks) / len(chunks)
    normalized = min(1.0, avg_score * 30)
    if normalized >= 0.7:
        label = "High"
    elif normalized >= 0.4:
        label = "Medium"
    elif normalized >= 0.2:
        label = "Low"
    else:
        label = "Insufficient"
    return round(normalized, 3), label


def generate_answer(
    query: str,
    chunks: List[RetrievedChunk],
) -> Tuple[str, List[CitationSource], float, str]:
    if not chunks:
        return (
            "I could not find any relevant passages in the indexed documents "
            "to answer your question. Please ensure relevant documents have "
            "been uploaded and indexed.",
            [],
            0.0,
            "Insufficient",
        )

    context = build_context(chunks)
    user_message = (
        f"Document passages:\n\n{context}\n\n"
        f"Question: {query}\n\n"
        f"Answer the question using only the passages above. "
        f"Include citation numbers [1], [2], etc. after each claim."
    )

    groq_key = settings.groq_api_key
    anthropic_key = settings.anthropic_api_key

    if groq_key and "placeholder" not in groq_key:
        from groq import Groq
        groq_client = Groq(api_key=groq_key)
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=1024,
        )
        answer = completion.choices[0].message.content
    elif anthropic_key and "placeholder" not in anthropic_key:
        client = anthropic.Anthropic(api_key=anthropic_key)
        message = client.messages.create(
            model=settings.llm_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        answer = message.content[0].text
    else:
        answer = _mock_answer(query, chunks)

    citations = [
        CitationSource(
            citation_number=i,
            document_id=str(chunk.document_id),
            filename=chunk.filename,
            page_number=chunk.page_number,
            excerpt=chunk.text[:500],
            relevance_score=round(chunk.score, 4),
            matter_number=chunk.matter_number,
        )
        for i, chunk in enumerate(chunks, start=1)
    ]
    confidence_score, confidence_label = compute_confidence(chunks)
    return answer, citations, confidence_score, confidence_label


def _mock_answer(query: str, chunks: List[RetrievedChunk]) -> str:
    excerpts = "\n".join(
        f"[{i}] {c.filename} (p.{c.page_number}): {c.text[:150]}..."
        for i, c in enumerate(chunks, start=1)
    )
    return (
        f"[Development mode — no LLM key configured]\n\n"
        f"Found {len(chunks)} relevant passage(s):\n\n"
        f"{excerpts}\n\n"
        f"Note: This is not legal advice."
    )
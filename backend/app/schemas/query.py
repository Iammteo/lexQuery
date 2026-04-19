from typing import List, Optional
from pydantic import BaseModel


class QueryRequest(BaseModel):
    """
    A natural language query submitted by a legal professional.
    """
    query: str
    workspace_id: Optional[str] = None   # scope to one workspace, or search all
    top_k: Optional[int] = None          # override default retrieval count
    top_n: Optional[int] = None          # override default rerank count


class CitationSource(BaseModel):
    """
    A single source citation — links a claim in the answer
    back to the exact chunk it came from.
    """
    citation_number: int
    document_id: str
    filename: str
    page_number: int
    excerpt: str                         # the verbatim chunk text
    relevance_score: float
    matter_number: Optional[str] = None


class QueryResponse(BaseModel):
    """
    The full response to a query — answer + citations + confidence.
    """
    query: str
    answer: str
    citations: List[CitationSource]
    confidence_score: float              # 0.0 - 1.0
    confidence_label: str               # High / Medium / Low / Insufficient
    chunks_retrieved: int
    chunks_used: int
    workspace_id: Optional[str] = None

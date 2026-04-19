from typing import List, Optional
from app.core.config import get_settings

settings = get_settings()


class EmbeddingService:
    """
    Local embedding service using sentence-transformers.
    Free, runs on your machine — no API key needed.
    Swap for OpenAI in production by changing this class.
    """

    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def embed_single(self, text: str) -> List[float]:
        """Embed a single text — used for query embeddings."""
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Embed many texts in batches."""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=True,
        )
        return embeddings.tolist()


_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
import uuid
import logging
from dataclasses import dataclass
from typing import List, Optional

from app.core.config import get_settings
from app.services.embedding_service import get_embedding_service
from app.services.weaviate_service import get_weaviate_service

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """
    A single retrieved chunk with all metadata needed for
    citation generation and answer assembly.
    """
    chunk_index: int
    text: str
    document_id: str
    filename: str
    page_number: int
    workspace_id: str
    matter_number: Optional[str]
    score: float            # final score after re-ranking
    vector_score: float     # raw vector similarity score
    bm25_score: float       # raw BM25 keyword score


class RetrievalService:
    """
    Hybrid retrieval pipeline:

    1. Embed the user query using the same model used during ingestion
    2. Run vector similarity search against Weaviate (semantic)
    3. Run BM25 keyword search against Weaviate (exact match)
    4. Merge results using Reciprocal Rank Fusion (RRF)
    5. Re-rank top-k using Cohere (or a fallback scorer)
    6. Return top-n passages with full citation metadata

    Why hybrid?
    - Vector search finds semantically similar text even when
      the user doesn't use the exact same words as the document.
    - BM25 catches exact legal terms (case numbers, defined terms,
      section references) that vector search can miss.
    - RRF combines both rankings without needing to tune weights.
    """

    def __init__(self):
        self.embed_svc = get_embedding_service()
        self.weaviate_svc = get_weaviate_service()

    def retrieve(
        self,
        tenant_id: uuid.UUID,
        query: str,
        workspace_id: Optional[uuid.UUID] = None,
        top_k: int = None,
        top_n: int = None,
    ) -> List[RetrievedChunk]:
        """
        Run the full retrieval pipeline for a user query.

        Args:
            tenant_id: The tenant making the query (enforces isolation)
            query: The natural language question
            workspace_id: Optional — scope search to one workspace
            top_k: Number of candidates before re-ranking (default 20)
            top_n: Number of results after re-ranking (default 5)

        Returns:
            List of RetrievedChunk ordered by relevance (best first)
        """
        top_k = top_k or settings.retrieval_top_k
        top_n = top_n or settings.rerank_top_n

        logger.info(
            f"[retrieve] tenant={tenant_id} query='{query[:60]}...' "
            f"workspace={workspace_id} top_k={top_k} top_n={top_n}"
        )

        # Step 1 — embed the query
        query_vector = self.embed_svc.embed_single(query)

        # Step 2 & 3 — vector + BM25 search
        vector_results = self._vector_search(
            tenant_id=tenant_id,
            query_vector=query_vector,
            workspace_id=workspace_id,
            limit=top_k,
        )
        bm25_results = self._bm25_search(
            tenant_id=tenant_id,
            query=query,
            workspace_id=workspace_id,
            limit=top_k,
        )

        logger.info(
            f"[retrieve] vector={len(vector_results)} bm25={len(bm25_results)} candidates"
        )

        # Step 4 — RRF merge
        merged = self._reciprocal_rank_fusion(vector_results, bm25_results)

        # Take top_k after merging
        candidates = merged[:top_k]

        if not candidates:
            logger.warning("[retrieve] No candidates found")
            return []

        # Step 5 — re-rank
        reranked = self._rerank(query=query, candidates=candidates, top_n=top_n)

        logger.info(f"[retrieve] returning {len(reranked)} chunks after reranking")
        return reranked

    def _vector_search(
        self,
        tenant_id: uuid.UUID,
        query_vector: List[float],
        workspace_id: Optional[uuid.UUID],
        limit: int,
    ) -> List[RetrievedChunk]:
        """Vector similarity search against Weaviate."""
        try:
            import weaviate.classes.query as wq

            collection = self.weaviate_svc.client.collections.get(
                self.weaviate_svc.COLLECTION
            )
            collection_with_tenant = collection.with_tenant(str(tenant_id))

            filters = None
            if workspace_id:
                filters = wq.Filter.by_property("workspace_id").equal(
                    str(workspace_id)
                )

            response = collection_with_tenant.query.near_vector(
                near_vector=query_vector,
                limit=limit,
                filters=filters,
                return_metadata=wq.MetadataQuery(distance=True),
            )

            results = []
            for obj in response.objects:
                props = obj.properties
                distance = obj.metadata.distance if obj.metadata else 1.0
                # Convert distance to similarity score (0-1)
                score = max(0.0, 1.0 - (distance or 1.0))
                results.append(
                    RetrievedChunk(
                        chunk_index=props.get("chunk_index", 0),
                        text=props.get("text", ""),
                        document_id=props.get("document_id", ""),
                        filename=props.get("filename", ""),
                        page_number=props.get("page_number", 1),
                        workspace_id=props.get("workspace_id", ""),
                        matter_number=props.get("matter_number"),
                        score=score,
                        vector_score=score,
                        bm25_score=0.0,
                    )
                )
            return results
        except Exception as e:
            logger.warning(f"[retrieve] Vector search failed: {e}")
            return []

    def _bm25_search(
        self,
        tenant_id: uuid.UUID,
        query: str,
        workspace_id: Optional[uuid.UUID],
        limit: int,
    ) -> List[RetrievedChunk]:
        """BM25 keyword search against Weaviate."""
        try:
            import weaviate.classes.query as wq

            collection = self.weaviate_svc.client.collections.get(
                self.weaviate_svc.COLLECTION
            )
            collection_with_tenant = collection.with_tenant(str(tenant_id))

            filters = None
            if workspace_id:
                filters = wq.Filter.by_property("workspace_id").equal(
                    str(workspace_id)
                )

            response = collection_with_tenant.query.bm25(
                query=query,
                limit=limit,
                filters=filters,
                return_metadata=wq.MetadataQuery(score=True),
            )

            results = []
            for obj in response.objects:
                props = obj.properties
                bm25_score = obj.metadata.score if obj.metadata else 0.0
                results.append(
                    RetrievedChunk(
                        chunk_index=props.get("chunk_index", 0),
                        text=props.get("text", ""),
                        document_id=props.get("document_id", ""),
                        filename=props.get("filename", ""),
                        page_number=props.get("page_number", 1),
                        workspace_id=props.get("workspace_id", ""),
                        matter_number=props.get("matter_number"),
                        score=bm25_score or 0.0,
                        vector_score=0.0,
                        bm25_score=bm25_score or 0.0,
                    )
                )
            return results
        except Exception as e:
            logger.warning(f"[retrieve] BM25 search failed: {e}")
            return []

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[RetrievedChunk],
        bm25_results: List[RetrievedChunk],
        k: int = 60,
    ) -> List[RetrievedChunk]:
        """
        Reciprocal Rank Fusion — combines two ranked lists.

        RRF score = sum(1 / (k + rank)) for each list.
        k=60 is the standard constant that balances top vs tail results.

        Uses (document_id, chunk_index) as the unique key per chunk.
        """
        scores: dict = {}
        chunks_by_key: dict = {}

        for rank, chunk in enumerate(vector_results, start=1):
            key = (chunk.document_id, chunk.chunk_index)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            chunk.vector_score = chunk.score
            chunks_by_key[key] = chunk

        for rank, chunk in enumerate(bm25_results, start=1):
            key = (chunk.document_id, chunk.chunk_index)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            chunk.bm25_score = chunk.score
            if key not in chunks_by_key:
                chunks_by_key[key] = chunk

        # Sort by RRF score descending
        sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
        result = []
        for key in sorted_keys:
            chunk = chunks_by_key[key]
            chunk.score = scores[key]
            result.append(chunk)

        return result

    def _rerank(
        self,
        query: str,
        candidates: List[RetrievedChunk],
        top_n: int,
    ) -> List[RetrievedChunk]:
        """
        Re-rank candidates using Cohere Rerank.
        Falls back to RRF score ordering if Cohere is unavailable.
        """
        if not settings.cohere_api_key or settings.cohere_api_key.startswith("placeholder"):
            logger.info("[retrieve] Cohere not configured — using RRF scores")
            return candidates[:top_n]

        try:
            import cohere
            co = cohere.Client(settings.cohere_api_key)

            documents = [c.text for c in candidates]
            response = co.rerank(
                model="rerank-english-v3.0",
                query=query,
                documents=documents,
                top_n=top_n,
            )

            reranked = []
            for result in response.results:
                chunk = candidates[result.index]
                chunk.score = result.relevance_score
                reranked.append(chunk)

            return reranked

        except Exception as e:
            logger.warning(f"[retrieve] Cohere rerank failed: {e} — using RRF scores")
            return candidates[:top_n]


_retrieval_service: Optional[RetrievalService] = None


def get_retrieval_service() -> RetrievalService:
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service

import uuid
from typing import List, Optional, Dict, Any

import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.data import DataObject
from weaviate.classes.query import Filter, MetadataQuery

from app.core.config import get_settings
from app.services.chunker import Chunk

settings = get_settings()


class WeaviateService:
    """
    Wrapper around Weaviate for chunk storage and retrieval.

    Multi-tenancy: each tenant gets a dedicated Weaviate tenant namespace
    within a single shared collection called 'LegalChunk'. This gives strong
    isolation (Weaviate enforces it at the query level) while keeping the
    schema management simple.

    A chunk stores:
      - text (the content, also BM25-indexed)
      - tenant_id, workspace_id, document_id (for filtering)
      - page_number, chunk_index (for citations)
      - filename, matter_number (human-readable metadata)
    """

    COLLECTION = "LegalChunk"

    def __init__(self):
        # Parse host/port from WEAVIATE_URL
        from urllib.parse import urlparse
        parsed = urlparse(settings.weaviate_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 8080

        self.client = weaviate.connect_to_local(host=host, port=port)
        self._ensure_collection()

    def close(self):
        """Close the Weaviate client connection."""
        try:
            self.client.close()
        except Exception:
            pass

    def _ensure_collection(self) -> None:
        """Create the LegalChunk collection if it doesn't exist."""
        if self.client.collections.exists(self.COLLECTION):
            return

        self.client.collections.create(
            name=self.COLLECTION,
            # Vectors are supplied by us (OpenAI), not computed by Weaviate
            vectorizer_config=Configure.Vectorizer.none(),
            # Enable multi-tenancy
            multi_tenancy_config=Configure.multi_tenancy(enabled=True),
            properties=[
                Property(name="text", data_type=DataType.TEXT),
                Property(name="tenant_id", data_type=DataType.UUID),
                Property(name="workspace_id", data_type=DataType.UUID),
                Property(name="document_id", data_type=DataType.UUID),
                Property(name="chunk_index", data_type=DataType.INT),
                Property(name="page_number", data_type=DataType.INT),
                Property(name="filename", data_type=DataType.TEXT),
                Property(name="matter_number", data_type=DataType.TEXT),
            ],
        )

    def _ensure_tenant(self, tenant_id: uuid.UUID) -> None:
        """Ensure a Weaviate tenant exists for this LexQuery tenant."""
        collection = self.client.collections.get(self.COLLECTION)
        tenant_name = str(tenant_id)
        existing = collection.tenants.get()
        if tenant_name not in existing:
            from weaviate.classes.tenants import Tenant as WTenant
            collection.tenants.create([WTenant(name=tenant_name)])

    def index_chunks(
        self,
        tenant_id: uuid.UUID,
        workspace_id: uuid.UUID,
        document_id: uuid.UUID,
        filename: str,
        chunks: List[Chunk],
        embeddings: List[List[float]],
        matter_number: Optional[str] = None,
    ) -> int:
        """
        Bulk-index a set of chunks with their embeddings.
        Returns the number of chunks indexed.
        """
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")

        self._ensure_tenant(tenant_id)

        collection = self.client.collections.get(self.COLLECTION)
        collection_with_tenant = collection.with_tenant(str(tenant_id))

        objects = [
            DataObject(
                properties={
                    "text": chunk.text,
                    "tenant_id": str(tenant_id),
                    "workspace_id": str(workspace_id),
                    "document_id": str(document_id),
                    "chunk_index": chunk.index,
                    "page_number": chunk.page_number,
                    "filename": filename,
                    "matter_number": matter_number or "",
                },
                vector=embedding,
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]

        collection_with_tenant.data.insert_many(objects)
        return len(objects)

    def delete_document_chunks(
        self,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> None:
        """
        Delete all chunks for a given document.
        Used when a document is deleted or re-indexed.
        """
        collection = self.client.collections.get(self.COLLECTION)
        collection_with_tenant = collection.with_tenant(str(tenant_id))
        collection_with_tenant.data.delete_many(
            where=Filter.by_property("document_id").equal(str(document_id))
        )


_weaviate_service: Optional[WeaviateService] = None


def get_weaviate_service() -> WeaviateService:
    global _weaviate_service
    if _weaviate_service is None:
        _weaviate_service = WeaviateService()
    return _weaviate_service

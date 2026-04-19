import re
from dataclasses import dataclass
from typing import List, Optional

import tiktoken

from app.core.config import get_settings
from app.services.document_parser import ParsedDocument

settings = get_settings()


@dataclass
class Chunk:
    """A single chunk ready to be embedded and indexed."""
    index: int              # position in the document (0-based)
    text: str               # the chunk content
    page_number: int        # source page for citations
    char_start: int         # byte offset in original document
    char_end: int
    token_count: int


class Chunker:
    """
    Split parsed documents into semantically coherent chunks.

    Key design choices:
    - 512 tokens per chunk (default) — fits most embedding model context windows.
    - 128 tokens of overlap between chunks — ensures important context at chunk
      boundaries isn't lost during retrieval.
    - Clause-boundary-aware splitting — prefers to break on paragraph breaks
      and sentence endings, not mid-sentence. Legal text has clear clause
      structure that we try to respect.
    """

    # Legal clause boundary patterns, in priority order
    # We prefer to split at higher-quality boundaries
    CLAUSE_BOUNDARIES = [
        r"\n\n+",                    # paragraph breaks (best)
        r"\.\s+(?=[A-Z])",           # sentence ends followed by capital
        r";\s+",                     # semicolons (clause separators)
        r",\s+",                     # commas (last resort)
    ]

    _encoder_cache: Optional[object] = None

    def __init__(
        self,
        chunk_size: int = None,
        overlap: int = None,
    ):
        self.chunk_size = chunk_size or settings.chunk_size_tokens
        self.overlap = overlap or settings.chunk_overlap_tokens

    @property
    def encoder(self):
        """Lazy-load the tokeniser — avoids network calls at import time."""
        if Chunker._encoder_cache is None:
            Chunker._encoder_cache = tiktoken.get_encoding("cl100k_base")
        return Chunker._encoder_cache

    def chunk_document(self, parsed: ParsedDocument) -> List[Chunk]:
        """
        Split a parsed document into chunks.
        Each chunk is tagged with its source page for citations.
        """
        chunks: List[Chunk] = []
        chunk_index = 0

        # Process each page separately so page_number is accurate
        for page in parsed.pages:
            page_chunks = self._chunk_text(
                text=page.text,
                page_number=page.page_number,
                starting_index=chunk_index,
            )
            chunks.extend(page_chunks)
            chunk_index += len(page_chunks)

        return chunks

    def _chunk_text(
        self,
        text: str,
        page_number: int,
        starting_index: int,
    ) -> List[Chunk]:
        """
        Chunk a single page of text.
        Uses token-aware windowing with clause-boundary preference.
        """
        tokens = self.encoder.encode(text)

        if len(tokens) <= self.chunk_size:
            # Short enough to be one chunk
            return [
                Chunk(
                    index=starting_index,
                    text=text,
                    page_number=page_number,
                    char_start=0,
                    char_end=len(text),
                    token_count=len(tokens),
                )
            ]

        chunks: List[Chunk] = []
        step = self.chunk_size - self.overlap
        idx = starting_index
        pos = 0

        while pos < len(tokens):
            end = min(pos + self.chunk_size, len(tokens))
            chunk_tokens = tokens[pos:end]
            chunk_text = self.encoder.decode(chunk_tokens)

            # Try to trim to a clean clause boundary at the end
            if end < len(tokens):
                chunk_text = self._trim_to_boundary(chunk_text)

            chunks.append(
                Chunk(
                    index=idx,
                    text=chunk_text.strip(),
                    page_number=page_number,
                    char_start=0,   # precise offset calc would require more work
                    char_end=len(chunk_text),
                    token_count=len(self.encoder.encode(chunk_text)),
                )
            )
            idx += 1

            # Advance by step (chunk_size - overlap)
            pos += step
            if end >= len(tokens):
                break

        return chunks

    def _trim_to_boundary(self, text: str) -> str:
        """
        Try to trim the trailing fragment at a natural boundary.
        Reduces splits in the middle of a sentence or clause.
        """
        for pattern in self.CLAUSE_BOUNDARIES:
            matches = list(re.finditer(pattern, text))
            if matches:
                last = matches[-1]
                # Only trim if we're not losing more than 25% of the chunk
                if last.end() >= len(text) * 0.75:
                    return text[:last.end()]
        return text

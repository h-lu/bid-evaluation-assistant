"""
Real document parsing module.

Provides PDF and DOCX parsing with text extraction, chunking, and metadata.
Falls back gracefully when optional dependencies are unavailable.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.errors import ApiError
from app.parse_utils import normalize_bbox


@dataclass
class PageBlock:
    page: int
    text: str
    bbox: list[float] = field(default_factory=lambda: [0.0, 0.0, 1.0, 1.0])
    block_type: str = "text"


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    page: int
    bbox: list[float]
    heading_path: list[str]
    chunk_type: str = "text"
    start_char: int = 0
    end_char: int = 0


CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
MIN_CHUNK_SIZE = 50


def _generate_chunk_id() -> str:
    return f"ck_{uuid.uuid4().hex[:16]}"


def _chunk_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _extract_heading_path(text: str) -> list[str]:
    """Extract heading hierarchy from leading markdown-style headings."""
    lines = text.strip().split("\n")
    headings: list[str] = []
    for line in lines[:5]:
        stripped = line.strip()
        match = re.match(r"^(#{1,6})\s+(.+)", stripped)
        if match:
            headings.append(match.group(2).strip())
        elif stripped and not headings:
            headings.append(stripped[:60])
            break
    return headings if headings else ["content"]


def chunk_text_blocks(
    blocks: list[PageBlock],
    *,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[DocumentChunk]:
    """Split page blocks into overlapping chunks preserving page/bbox metadata."""
    if not blocks:
        return []

    chunks: list[DocumentChunk] = []
    current_text = ""
    current_page = blocks[0].page if blocks else 1
    current_bbox = blocks[0].bbox if blocks else [0.0, 0.0, 1.0, 1.0]
    char_offset = 0

    for block in blocks:
        text = block.text.strip()
        if not text:
            continue

        if len(current_text) + len(text) + 1 > chunk_size and len(current_text) >= MIN_CHUNK_SIZE:
            heading_path = _extract_heading_path(current_text)
            chunks.append(
                DocumentChunk(
                    chunk_id=_generate_chunk_id(),
                    text=current_text.strip(),
                    page=current_page,
                    bbox=current_bbox,
                    heading_path=heading_path,
                    start_char=char_offset,
                    end_char=char_offset + len(current_text),
                )
            )
            char_offset += len(current_text) - chunk_overlap
            overlap_text = current_text[-chunk_overlap:] if len(current_text) > chunk_overlap else ""
            current_text = overlap_text
            current_page = block.page
            current_bbox = block.bbox

        if current_text:
            current_text += "\n" + text
        else:
            current_text = text
            current_page = block.page
            current_bbox = block.bbox

    if current_text.strip():
        is_last_remainder = len(current_text.strip()) < MIN_CHUNK_SIZE
        if not is_last_remainder or not chunks:
            heading_path = _extract_heading_path(current_text)
            chunks.append(
                DocumentChunk(
                    chunk_id=_generate_chunk_id(),
                    text=current_text.strip(),
                    page=current_page,
                    bbox=current_bbox,
                    heading_path=heading_path,
                    start_char=char_offset,
                    end_char=char_offset + len(current_text),
                )
            )
        elif chunks:
            chunks[-1].text += "\n" + current_text.strip()
            chunks[-1].end_char = char_offset + len(current_text)

    return chunks


def parse_pdf_bytes(file_bytes: bytes) -> list[DocumentChunk]:
    """Parse PDF bytes into chunks using PyMuPDF."""
    try:
        import pymupdf
    except ImportError:
        raise ApiError(
            code="PARSER_DEPENDENCY_MISSING",
            message="pymupdf is required for PDF parsing",
            error_class="permanent",
            retryable=False,
            http_status=500,
        )

    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise ApiError(
            code="DOC_PARSE_PDF_CORRUPT",
            message=f"Failed to open PDF: {exc}",
            error_class="permanent",
            retryable=False,
            http_status=422,
        )

    blocks: list[PageBlock] = []
    try:
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_num = page_idx + 1
            page_rect = page.rect
            pw = max(page_rect.width, 1.0)
            ph = max(page_rect.height, 1.0)

            text_dict = page.get_text("dict", flags=pymupdf.TEXT_PRESERVE_WHITESPACE)
            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                lines_text = []
                for line in block.get("lines", []):
                    spans_text = []
                    for span in line.get("spans", []):
                        t = span.get("text", "")
                        if t.strip():
                            spans_text.append(t)
                    if spans_text:
                        lines_text.append(" ".join(spans_text))
                text = "\n".join(lines_text).strip()
                if not text:
                    continue

                raw_bbox = block.get("bbox", [0, 0, pw, ph])
                normalized = [
                    round(raw_bbox[0] / pw, 4),
                    round(raw_bbox[1] / ph, 4),
                    round(raw_bbox[2] / pw, 4),
                    round(raw_bbox[3] / ph, 4),
                ]
                blocks.append(PageBlock(page=page_num, text=text, bbox=normalized))

            if not any(b.page == page_num for b in blocks):
                plain = page.get_text("text").strip()
                if plain:
                    blocks.append(
                        PageBlock(
                            page=page_num,
                            text=plain,
                            bbox=[0.0, 0.0, 1.0, 1.0],
                        )
                    )
    finally:
        doc.close()

    if not blocks:
        return []

    return chunk_text_blocks(blocks)


def parse_docx_bytes(file_bytes: bytes) -> list[DocumentChunk]:
    """Parse DOCX bytes into chunks using python-docx."""
    try:
        import docx
    except ImportError:
        raise ApiError(
            code="PARSER_DEPENDENCY_MISSING",
            message="python-docx is required for DOCX parsing",
            error_class="permanent",
            retryable=False,
            http_status=500,
        )

    import io

    try:
        doc = docx.Document(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ApiError(
            code="DOC_PARSE_DOCX_CORRUPT",
            message=f"Failed to open DOCX: {exc}",
            error_class="permanent",
            retryable=False,
            http_status=422,
        )

    blocks: list[PageBlock] = []
    page_num = 1
    page_char_count = 0
    chars_per_page = 3000

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        blocks.append(
            PageBlock(
                page=page_num,
                text=text,
                bbox=[0.0, 0.0, 1.0, 1.0],
                block_type="heading" if para.style and para.style.name.startswith("Heading") else "text",
            )
        )
        page_char_count += len(text)
        if page_char_count >= chars_per_page:
            page_num += 1
            page_char_count = 0

    if not blocks:
        return []

    return chunk_text_blocks(blocks)


def parse_plain_text_bytes(file_bytes: bytes) -> list[DocumentChunk]:
    """Parse plain text file bytes into chunks."""
    from app.parse_utils import decode_text_with_fallback

    text = decode_text_with_fallback(file_bytes)
    if not text.strip():
        return []

    paragraphs = re.split(r"\n{2,}", text)
    blocks: list[PageBlock] = []
    page_num = 1
    page_char_count = 0
    chars_per_page = 3000

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        blocks.append(PageBlock(page=page_num, text=para, bbox=[0.0, 0.0, 1.0, 1.0]))
        page_char_count += len(para)
        if page_char_count >= chars_per_page:
            page_num += 1
            page_char_count = 0

    return chunk_text_blocks(blocks)


def parse_file_bytes(
    file_bytes: bytes,
    *,
    filename: str,
    document_id: str,
    parser_name: str = "local",
    parser_version: str = "v1",
) -> list[dict[str, Any]]:
    """
    Parse file bytes into a list of chunk dicts matching the existing chunk schema.

    Returns list of dicts with keys:
      document_id, pages, positions, section, heading_path, chunk_type,
      parser, parser_version, content_source, text, chunk_id, chunk_hash
    """
    lower = filename.lower()

    if lower.endswith(".pdf"):
        doc_chunks = parse_pdf_bytes(file_bytes)
        content_source = "pdf_local"
    elif lower.endswith((".docx", ".doc")):
        doc_chunks = parse_docx_bytes(file_bytes)
        content_source = "docx_local"
    elif lower.endswith((".txt", ".md", ".csv")):
        doc_chunks = parse_plain_text_bytes(file_bytes)
        content_source = "text_local"
    else:
        doc_chunks = parse_plain_text_bytes(file_bytes)
        content_source = "fallback_local"

    result: list[dict[str, Any]] = []
    for chunk in doc_chunks:
        result.append(
            {
                "chunk_id": chunk.chunk_id,
                "document_id": document_id,
                "pages": [chunk.page],
                "positions": [
                    {
                        "page": chunk.page,
                        "bbox": chunk.bbox,
                        "start": chunk.start_char,
                        "end": chunk.end_char,
                    }
                ],
                "section": chunk.heading_path[0] if chunk.heading_path else "content",
                "heading_path": chunk.heading_path,
                "chunk_type": chunk.chunk_type,
                "parser": parser_name,
                "parser_version": parser_version,
                "content_source": content_source,
                "text": chunk.text,
                "chunk_hash": _chunk_hash(chunk.text),
            }
        )

    return result

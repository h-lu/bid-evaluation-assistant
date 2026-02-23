from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from typing import Any

import chromadb
from chromadb.api import ClientAPI
from fastapi import FastAPI
from pydantic import BaseModel, Field

try:
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
except ImportError:  # pragma: no cover - optional dependency
    SentenceTransformerEmbeddingFunction = None


class IndexRequest(BaseModel):
    index_name: str
    tenant_id: str
    project_id: str
    document_id: str
    doc_type: str
    supplier_id: str | None = None
    chunks: list[dict[str, Any]] = Field(default_factory=list)


class QueryFilters(BaseModel):
    tenant_id: str
    project_id: str
    supplier_id: str
    doc_scope: list[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    index_name: str
    query: str
    mode: str = "hybrid"
    top_k: int = 10
    filters: QueryFilters


class SimpleEmbeddingFunction:
    def __init__(self, dim: int = 128) -> None:
        self._dim = max(8, dim)

    def __call__(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            raw = list(digest)
            needed = self._dim
            data = (raw * ((needed // len(raw)) + 1))[:needed]
            vectors.append([x / 255.0 for x in data])
        return vectors


@lru_cache(maxsize=1)
def _embedding_fn():
    backend = os.environ.get("EMBEDDING_BACKEND", "sentence-transformers").strip().lower()
    if backend == "simple":
        dim = int(os.environ.get("EMBEDDING_DIM", "128"))
        return SimpleEmbeddingFunction(dim=dim)
    if SentenceTransformerEmbeddingFunction is None:
        raise RuntimeError("sentence-transformers is required when EMBEDDING_BACKEND is not 'simple'")
    model_name = os.environ.get("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
    return SentenceTransformerEmbeddingFunction(model_name=model_name)


@lru_cache(maxsize=1)
def _chroma_client() -> ClientAPI:
    persist_dir = os.environ.get("CHROMA_PERSIST_DIR", "").strip()
    if persist_dir:
        return chromadb.PersistentClient(path=persist_dir)
    host = os.environ.get("CHROMA_HOST", "").strip()
    if host:
        port = int(os.environ.get("CHROMA_PORT", "8000"))
        return chromadb.HttpClient(host=host, port=port)
    return chromadb.Client()


def _collection(index_name: str):
    client = _chroma_client()
    return client.get_or_create_collection(name=index_name, embedding_function=_embedding_fn())


def _chunk_text(chunk: dict[str, Any]) -> str:
    text = str(chunk.get("text") or "")
    return text if text else str(chunk.get("section") or "")


def _chunk_metadata(
    *,
    chunk: dict[str, Any],
    tenant_id: str,
    project_id: str,
    supplier_id: str,
    document_id: str,
    doc_type: str,
) -> dict[str, Any]:
    positions = chunk.get("positions", [])
    page = 1
    bbox = [0.0, 0.0, 1.0, 1.0]
    if isinstance(positions, list) and positions:
        first = positions[0] if isinstance(positions[0], dict) else {}
        page = int(first.get("page") or 1)
        bbox_raw = first.get("bbox")
        if isinstance(bbox_raw, list) and len(bbox_raw) == 4:
            try:
                bbox = [float(x) for x in bbox_raw]
            except (TypeError, ValueError):
                pass
    return {
        "tenant_id": tenant_id,
        "project_id": project_id,
        "supplier_id": supplier_id,
        "document_id": document_id,
        "doc_type": doc_type,
        "page": page,
        "bbox": bbox,
        "chunk_type": str(chunk.get("chunk_type") or "text"),
        "heading_path": chunk.get("heading_path", []),
    }


app = FastAPI(title="LightRAG Lite Service", version="0.1.0")


@app.post("/index")
def index_chunks(payload: IndexRequest):
    collection = _collection(payload.index_name)
    ids: list[str] = []
    docs: list[str] = []
    metas: list[dict[str, Any]] = []
    for chunk in payload.chunks:
        if not isinstance(chunk, dict):
            continue
        chunk_id = str(chunk.get("chunk_id") or "")
        if not chunk_id:
            continue
        ids.append(chunk_id)
        docs.append(_chunk_text(chunk))
        metas.append(
            _chunk_metadata(
                chunk=chunk,
                tenant_id=payload.tenant_id,
                project_id=payload.project_id,
                supplier_id=payload.supplier_id or "",
                document_id=payload.document_id,
                doc_type=payload.doc_type,
            )
        )
    if ids:
        collection.upsert(ids=ids, documents=docs, metadatas=metas)
    return {"success": True, "indexed": len(ids)}


@app.post("/query")
def query_index(payload: QueryRequest):
    collection = _collection(payload.index_name)
    where: dict[str, Any] = {
        "tenant_id": payload.filters.tenant_id,
        "project_id": payload.filters.project_id,
        "supplier_id": payload.filters.supplier_id,
    }
    if payload.filters.doc_scope:
        where["doc_type"] = {"$in": payload.filters.doc_scope}
    result = collection.query(query_texts=[payload.query], n_results=payload.top_k, where=where)
    ids = (result.get("ids") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    out: list[dict[str, Any]] = []
    for idx, chunk_id in enumerate(ids):
        metadata = metadatas[idx] if idx < len(metadatas) else {}
        distance = float(distances[idx]) if idx < len(distances) else 1.0
        score_raw = 1.0 / (1.0 + distance)
        out.append(
            {
                "chunk_id": chunk_id,
                "score_raw": score_raw,
                "reason": "vector_similarity",
                "metadata": metadata or {},
            }
        )
    return {"items": out}

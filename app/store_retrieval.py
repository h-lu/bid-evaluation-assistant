from __future__ import annotations

import json
import logging
import os
import re
from typing import Any
from urllib import request
from urllib.error import URLError

from app.errors import ApiError
from app.sql_whitelist import query_structured, validate_structured_filters

logger = logging.getLogger(__name__)

_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")


class StoreRetrievalMixin:
    @staticmethod
    def _lightrag_index_prefix() -> str:
        return os.environ.get("LIGHTRAG_INDEX_PREFIX", "lightrag").strip() or "lightrag"

    @staticmethod
    def _validate_index_segment(value: str, field_name: str) -> str:
        if not value or not _SAFE_ID_RE.match(value):
            raise ApiError(
                code="REQ_VALIDATION_FAILED",
                message=f"Invalid {field_name} for index name: must match [a-zA-Z0-9_-]+",
                error_class="client",
                retryable=False,
                http_status=400,
            )
        return value

    def _retrieval_index_name(self, *, tenant_id: str, project_id: str) -> str:
        prefix = self._lightrag_index_prefix()
        self._validate_index_segment(tenant_id, "tenant_id")
        self._validate_index_segment(project_id, "project_id")
        return f"{prefix}:{tenant_id}:{project_id}"

    @staticmethod
    def _post_json(
        *,
        endpoint: str,
        payload: dict[str, Any],
        timeout_s: float,
    ) -> object:
        body = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
        req = request.Request(
            endpoint,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
        return json.loads(raw)

    def _maybe_index_chunks_to_lightrag(
        self,
        *,
        tenant_id: str,
        project_id: str,
        supplier_id: str,
        document_id: str,
        doc_type: str,
        chunks: list[dict[str, Any]],
    ) -> None:
        if not chunks:
            return
        index_name = self._retrieval_index_name(tenant_id=tenant_id, project_id=project_id)
        dsn = os.environ.get("LIGHTRAG_DSN", "").strip()
        if dsn:
            endpoint = dsn.rstrip("/") + "/index"
            payload = {
                "index_name": index_name,
                "tenant_id": tenant_id,
                "project_id": project_id,
                "supplier_id": supplier_id,
                "document_id": document_id,
                "doc_type": doc_type,
                "chunks": chunks,
            }
            timeout_s = float(os.environ.get("RERANK_TIMEOUT_MS", "2000")) / 1000.0 + 3.0
            self.parser_retrieval_metrics["parse_index_write_total"] += 1
            try:
                self._post_json(endpoint=endpoint, payload=payload, timeout_s=timeout_s)
                return
            except (TimeoutError, URLError, ValueError, OSError):
                self.parser_retrieval_metrics["parse_index_fail_total"] += 1
                return

        self.parser_retrieval_metrics["parse_index_write_total"] += 1
        try:
            from app.lightrag_service import index_chunks_to_collection

            indexed = index_chunks_to_collection(
                index_name=index_name,
                tenant_id=tenant_id,
                project_id=project_id,
                supplier_id=supplier_id,
                document_id=document_id,
                doc_type=doc_type,
                chunks=chunks,
            )
            if indexed == 0:
                self.parser_retrieval_metrics["parse_index_fail_total"] += 1
        except Exception:
            self.parser_retrieval_metrics["parse_index_fail_total"] += 1

    def _query_lightrag(
        self,
        *,
        tenant_id: str,
        project_id: str,
        supplier_id: str,
        query: str,
        selected_mode: str,
        top_k: int,
        doc_scope: list[str],
    ) -> list[dict[str, Any]] | None:
        index_name = self._retrieval_index_name(tenant_id=tenant_id, project_id=project_id)
        dsn = os.environ.get("LIGHTRAG_DSN", "").strip()

        result: dict[str, Any] | None = None
        if dsn:
            endpoint = dsn.rstrip("/") + "/query"
            payload = {
                "index_name": index_name,
                "query": query,
                "mode": selected_mode,
                "top_k": top_k,
                "filters": {
                    "tenant_id": tenant_id,
                    "project_id": project_id,
                    "supplier_id": supplier_id,
                    "doc_scope": list(doc_scope),
                },
            }
            timeout_s = float(os.environ.get("RERANK_TIMEOUT_MS", "2000")) / 1000.0 + 3.0
            self.parser_retrieval_metrics["retrieval_lightrag_calls_total"] += 1
            try:
                result = self._post_json(endpoint=endpoint, payload=payload, timeout_s=timeout_s)
                if not isinstance(result, dict):
                    logger.warning("external_lightrag_invalid_response type=%s", type(result).__name__)
                    result = None
                elif "items" in result and not isinstance(result["items"], list):
                    logger.warning("external_lightrag_invalid_items type=%s", type(result["items"]).__name__)
                    result = None
            except (TimeoutError, URLError, ValueError, OSError):
                self.parser_retrieval_metrics["retrieval_lightrag_fail_total"] += 1
                result = None
        else:
            self.parser_retrieval_metrics["retrieval_lightrag_calls_total"] += 1
            try:
                from app.lightrag_service import query_collection

                result = query_collection(
                    index_name=index_name,
                    query=query,
                    top_k=top_k,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    supplier_id=supplier_id,
                    doc_scope=doc_scope or None,
                )
            except Exception:
                self.parser_retrieval_metrics["retrieval_lightrag_fail_total"] += 1
                result = None

        if result is None:
            return None
        rows = result.get("items")
        if not isinstance(rows, list):
            return []
        out: list[dict[str, Any]] = []
        dropped_cross_tenant = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            metadata = row.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
            if metadata.get("tenant_id") != tenant_id:
                dropped_cross_tenant += 1
                continue
            if metadata.get("project_id") != project_id:
                dropped_cross_tenant += 1
                continue
            if metadata.get("supplier_id") != supplier_id:
                dropped_cross_tenant += 1
                continue
            row_doc_type = metadata.get("doc_type")
            if doc_scope and row_doc_type not in set(doc_scope):
                continue
            entry: dict[str, Any] = {
                "chunk_id": row.get("chunk_id"),
                "score_raw": float(row.get("score_raw", 0.5)),
                "reason": str(row.get("reason", "matched retrieval intent")),
                "metadata": {
                    "tenant_id": metadata.get("tenant_id"),
                    "project_id": metadata.get("project_id"),
                    "supplier_id": metadata.get("supplier_id"),
                    "document_id": metadata.get("document_id"),
                    "doc_type": metadata.get("doc_type"),
                    "page": int(metadata.get("page", 1)),
                    "bbox": metadata.get("bbox", [0, 0, 1, 1]),
                },
            }
            if row.get("text"):
                entry["text"] = row["text"]
            out.append(entry)
        if dropped_cross_tenant > 0:
            logger.warning(
                "retrieval_post_filter_drop tenant_id=%s project_id=%s dropped=%d",
                tenant_id, project_id, dropped_cross_tenant,
            )
            self.parser_retrieval_metrics["retrieval_cross_tenant_drops_total"] = (
                self.parser_retrieval_metrics.get("retrieval_cross_tenant_drops_total", 0)
                + dropped_cross_tenant
            )
        return out

    @staticmethod
    def _rerank_items(items: list[dict[str, Any]], query: str = "") -> list[dict[str, Any]]:
        if os.environ.get("BEA_FORCE_RERANK_ERROR", "").strip().lower() in {"1", "true", "yes", "on"}:
            raise RuntimeError("forced rerank error")
        from app.reranker import rerank_items
        return rerank_items(query=query, items=items)

    def register_citation_source(self, *, chunk_id: str, source: dict[str, Any]) -> None:
        self.citation_sources[chunk_id] = source

    def get_citation_source(self, *, chunk_id: str, tenant_id: str) -> dict[str, Any] | None:
        source = self.citation_sources.get(chunk_id)
        if source is None:
            return None
        source_tenant = source.get("tenant_id", tenant_id)
        self._assert_tenant_scope(source_tenant, tenant_id)
        return source

    def _resolve_citation(self, chunk_id: str, *, include_quote: bool = True) -> dict[str, Any]:
        """
        将 chunk_id 解析为完整 citation 对象。

        Args:
            chunk_id: chunk 唯一标识
            include_quote: 是否包含 quote 字段（报告级需要，criteria 级不需要）

        Returns:
            {"chunk_id": str, "page": int | None, "bbox": list | None, "quote": str | None}
        """
        source = self.citation_sources.get(chunk_id)
        if source is None:
            result = {
                "chunk_id": chunk_id,
                "page": None,
                "bbox": None,
            }
            if include_quote:
                result["quote"] = None
            return result
        result = {
            "chunk_id": chunk_id,
            "page": source.get("page"),
            "bbox": source.get("bbox"),
        }
        if include_quote:
            result["quote"] = source.get("text")
        return result

    def _resolve_citations_batch(self, chunk_ids: list[str], *, include_quote: bool = True) -> list[dict[str, Any]]:
        """
        批量解析 chunk_id 列表为 citation 对象列表。
        """
        return [self._resolve_citation(cid, include_quote=include_quote) for cid in chunk_ids]

    def _calculate_retrieval_agreement(self, chunk_ids: list[str]) -> float:
        """
        计算检索一致性 (retrieval_agreement)。

        基于引用来源的 score_raw 分布计算：
        - 如果所有 citation 的 score_raw 都较高且接近，认为一致性好
        - 如果 score_raw 分散，认为一致性差

        Returns:
            float: 0.0 ~ 1.0
        """
        if not chunk_ids:
            return 0.0

        scores = []
        for cid in chunk_ids:
            source = self.citation_sources.get(cid)
            if source and "score_raw" in source:
                try:
                    scores.append(float(source.get("score_raw", 0)))
                except (TypeError, ValueError):
                    pass

        if not scores:
            return 0.5  # 无分数数据时返回中等值

        if len(scores) == 1:
            return 1.0  # 单个结果，完全一致

        # 计算分数的变异系数 (CV = std / mean)
        mean_score = sum(scores) / len(scores)
        if mean_score == 0:
            return 0.5

        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        std_dev = variance**0.5
        cv = std_dev / mean_score

        # CV 越小，一致性越高
        # CV=0 → agreement=1.0, CV>=1 → agreement=0.0
        agreement = max(0.0, min(1.0, 1.0 - cv))
        return agreement

    @staticmethod
    def _select_retrieval_mode(*, query_type: str, high_risk: bool) -> str:
        if high_risk:
            return "mix"
        mapping = {
            "fact": "local",
            "relation": "global",
            "comparison": "hybrid",
            "summary": "hybrid",
            "risk": "mix",
        }
        return mapping.get(query_type, "hybrid")

    def retrieval_query(
        self,
        *,
        tenant_id: str,
        project_id: str,
        supplier_id: str,
        query: str,
        query_type: str,
        high_risk: bool,
        top_k: int,
        doc_scope: list[str],
        enable_rerank: bool = True,
        must_include_terms: list[str] | None = None,
        must_exclude_terms: list[str] | None = None,
        structured_filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.parser_retrieval_metrics["retrieval_queries_total"] += 1
        selected_mode = self._select_retrieval_mode(query_type=query_type, high_risk=high_risk)
        index_name = self._retrieval_index_name(tenant_id=tenant_id, project_id=project_id)
        candidates = self._query_lightrag(
            tenant_id=tenant_id,
            project_id=project_id,
            supplier_id=supplier_id,
            query=query,
            selected_mode=selected_mode,
            top_k=top_k,
            doc_scope=doc_scope,
        )
        if candidates is None:
            local_candidates = [x for x in self.citation_sources.values() if x.get("tenant_id") == tenant_id]
            local_candidates = [x for x in local_candidates if x.get("project_id") == project_id]
            local_candidates = [x for x in local_candidates if x.get("supplier_id") == supplier_id]
            if doc_scope:
                scope = set(doc_scope)
                local_candidates = [x for x in local_candidates if x.get("doc_type") in scope]
            candidates = []
            for source in local_candidates:
                candidates.append(
                    {
                        "chunk_id": source.get("chunk_id"),
                        "score_raw": float(source.get("score_raw", 0.5)),
                        "reason": f"matched {query_type} intent",
                        "metadata": {
                            "tenant_id": source.get("tenant_id"),
                            "project_id": source.get("project_id"),
                            "supplier_id": source.get("supplier_id"),
                            "document_id": source.get("document_id"),
                            "doc_type": source.get("doc_type"),
                            "page": int(source.get("page", 1)),
                            "bbox": source.get("bbox", [0, 0, 1, 1]),
                        },
                    }
                )
        if structured_filters:
            validated = validate_structured_filters(structured_filters)
            if validated:
                struct_hits = query_structured(
                    store=self,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    supplier_id=supplier_id,
                    structured_filters=validated,
                )
                existing_ids = {c.get("chunk_id") for c in candidates}
                for hit in struct_hits:
                    hid = hit.get("chunk_id")
                    if hid in existing_ids:
                        for i, c in enumerate(candidates):
                            if c.get("chunk_id") == hid and float(hit.get("score_raw", 0)) > float(
                                c.get("score_raw", 0)
                            ):
                                candidates[i] = hit
                    else:
                        candidates.append(hit)
                        existing_ids.add(hid)

        include_terms = [x.lower() for x in (must_include_terms or []) if x.strip()]
        exclude_terms = [x.lower() for x in (must_exclude_terms or []) if x.strip()]
        rewrite = self._normalize_and_rewrite_query(
            query=query,
            include_terms=include_terms,
            exclude_terms=exclude_terms,
        )
        if include_terms:
            candidates = [
                x
                for x in candidates
                if all(
                    term in str(self.citation_sources.get(str(x.get("chunk_id", "")), {}).get("text", "")).lower()
                    for term in include_terms
                )
            ]
        if exclude_terms:
            candidates = [
                x
                for x in candidates
                if all(
                    term not in str(self.citation_sources.get(str(x.get("chunk_id", "")), {}).get("text", "")).lower()
                    for term in exclude_terms
                )
            ]

        items = [dict(x) for x in candidates]
        degraded = False
        degrade_reason = ""
        if enable_rerank:
            try:
                items = self._rerank_items(items, query=query)
            except Exception:
                degraded = True
                degrade_reason = "rerank_failed"
                self.parser_retrieval_metrics["rerank_degraded_total"] += 1
                for item in items:
                    item["score_rerank"] = None
                items = sorted(items, key=lambda x: float(x.get("score_raw", 0.0)), reverse=True)
        else:
            degraded = True
            degrade_reason = "rerank_disabled"
            self.parser_retrieval_metrics["rerank_degraded_total"] += 1
            for item in items:
                item["score_rerank"] = None
            items = sorted(items, key=lambda x: float(x.get("score_raw", 0.0)), reverse=True)
        items = items[:top_k]
        return {
            "query": query,
            "rewritten_query": rewrite["rewritten_query"],
            "rewrite_reason": rewrite["rewrite_reason"],
            "constraints_preserved": rewrite["constraints_preserved"],
            "constraint_diff": rewrite["constraint_diff"],
            "entity_constraints": rewrite.get("entity_constraints", []),
            "numeric_constraints": rewrite.get("numeric_constraints", []),
            "time_constraints": rewrite.get("time_constraints", []),
            "query_type": query_type,
            "selected_mode": selected_mode,
            "index_name": index_name,
            "degraded": degraded,
            "degrade_reason": degrade_reason or None,
            "items": items,
            "total": len(items),
        }

    def retrieval_preview(
        self,
        *,
        tenant_id: str,
        project_id: str,
        supplier_id: str,
        query: str,
        query_type: str,
        high_risk: bool,
        top_k: int,
        doc_scope: list[str],
        enable_rerank: bool = True,
        must_include_terms: list[str] | None = None,
        must_exclude_terms: list[str] | None = None,
        structured_filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        base = self.retrieval_query(
            tenant_id=tenant_id,
            project_id=project_id,
            supplier_id=supplier_id,
            query=query,
            query_type=query_type,
            high_risk=high_risk,
            top_k=top_k,
            doc_scope=doc_scope,
            enable_rerank=enable_rerank,
            must_include_terms=must_include_terms,
            must_exclude_terms=must_exclude_terms,
            structured_filters=structured_filters,
        )
        preview_items = []
        for item in base["items"]:
            source = self.citation_sources.get(item["chunk_id"], {})
            preview_items.append(
                {
                    "chunk_id": item["chunk_id"],
                    "document_id": source.get("document_id"),
                    "page": item["metadata"]["page"],
                    "bbox": item["metadata"]["bbox"],
                    "text": source.get("text", ""),
                }
            )
        return {
            "query": query,
            "selected_mode": base["selected_mode"],
            "index_name": base["index_name"],
            "degraded": base["degraded"],
            "items": preview_items,
            "total": len(preview_items),
        }

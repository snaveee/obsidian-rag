"""FastAPI service for obsidian-rag.

Exposes REST endpoints for vault indexing, hybrid search, grounded question
answering with source citations, related note graph discovery, and search history.
Protected by X-API-Key header authentication.
"""

import logging
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from infra.auth import verify_api_key
from infra.config import load_settings
from infra.embeddings import get_embedding_client
from infra.generation import generate_answer
from infra.history_store import HistoryStore
from infra.hybrid_search import HybridSearchEngine
from infra.indexing import IndexConflictError, VaultIndexer
from infra.keyword_index import KeywordStore
from infra.note_registry import NoteRegistry
from infra.vector_store import VectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = load_settings()

# Initialize core stores and engines
registry = NoteRegistry(settings.registry_db)
keyword_store = KeywordStore(settings.keyword_db)
vector_store = VectorStore(settings.chroma_dir, collection_name=settings.collection_name)
embedding_client = get_embedding_client(settings.ollama_url, model=settings.embed_model)
history_store = HistoryStore(settings.history_db)

search_engine = HybridSearchEngine(
    registry=registry,
    keyword_store=keyword_store,
    vector_store=vector_store,
    embedding_client=embedding_client,
    rerank_enabled=settings.rerank_enabled,
    reranker_model=settings.reranker_model,
)

indexer = VaultIndexer(
    vault_path=settings.vault_path,
    registry=registry,
    keyword_store=keyword_store,
    vector_store=vector_store,
    embedding_client=embedding_client,
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap,
)

app = FastAPI(
    title="obsidian-rag",
    description="Intelligent Hybrid Search and Grounded RAG over Obsidian Vaults",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request & Response Models ---


class IndexRequest(BaseModel):
    full_reindex: bool = Field(False, description="Whether to reset and rebuild all stores.")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query string.")
    top_k: int = Field(5, ge=1, le=20, description="Max results to return.")
    candidate_k: int = Field(20, ge=1, le=50, description="Candidates before re-ranking.")
    tags: list[str] | None = Field(None, description="Optional tag filter.")
    folder: str | None = Field(None, description="Optional folder filter.")
    enable_rerank: bool | None = Field(None, description="Toggle cross-encoder rerank.")


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Question to answer.")
    top_k: int = Field(5, ge=1, le=15, description="Number of context passages.")
    tags: list[str] | None = Field(None, description="Optional tag filter.")
    folder: str | None = Field(None, description="Optional folder filter.")
    enable_rerank: bool | None = Field(None, description="Toggle cross-encoder rerank.")


class AskResponse(BaseModel):
    query: str
    answer: str
    citations: list[int]
    sources: list[dict[str, Any]]
    related_notes: list[dict[str, Any]]
    retrieval_mode: str
    rerank_applied: bool
    search_id: int


# --- API Routes ---


@app.get("/", tags=["Health"])
def health_and_stats():
    """Public health check and vault indexing statistics."""
    stats = registry.stats()
    return {
        "status": "online",
        "service": "obsidian-rag",
        "vault_path": str(settings.vault_path),
        "total_notes": stats["notes"],
        "total_chunks": stats["chunks"],
        "last_indexed_at": stats["last_indexed_at"],
        "tags_count": len(stats["tags"]),
        "folders_count": len(stats["folders"]),
        "models": {
            "embed": settings.embed_model,
            "gen": settings.gen_model,
            "rerank": settings.reranker_model,
        },
    }


@app.post("/index", tags=["Indexing"], dependencies=[Depends(verify_api_key)])
def run_indexing(req: IndexRequest = IndexRequest()):
    """Trigger vault synchronization into vector and keyword indexes."""
    try:
        report = indexer.sync(full_reindex=req.full_reindex)
        return {"status": "success", "report": report.to_dict()}
    except IndexConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Indexing failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing failed: {exc}",
        ) from exc


@app.post("/search", tags=["Search"], dependencies=[Depends(verify_api_key)])
def search_notes(req: SearchRequest):
    """Retrieve ranked candidate passages without generating an LLM answer."""
    results, mode, rerank_applied = search_engine.search(
        query=req.query,
        top_k=req.top_k,
        candidate_k=req.candidate_k,
        tags=req.tags,
        folder=req.folder,
        enable_rerank=req.enable_rerank,
    )
    return {
        "query": req.query,
        "mode": mode,
        "rerank_applied": rerank_applied,
        "count": len(results),
        "results": results,
    }


@app.post("/ask", response_model=AskResponse, tags=["RAG"], dependencies=[Depends(verify_api_key)])
def ask_vault(req: AskRequest):
    """Ask a question; returns grounded answer with citations and related notes."""
    results, mode, rerank_applied = search_engine.search(
        query=req.query,
        top_k=req.top_k,
        candidate_k=max(20, req.top_k * 3),
        tags=req.tags,
        folder=req.folder,
        enable_rerank=req.enable_rerank,
    )

    try:
        grounded = generate_answer(
            query=req.query,
            results=results,
            ollama_url=settings.ollama_url,
            model=settings.gen_model,
            num_predict=settings.gen_num_predict,
            num_ctx=settings.gen_num_ctx,
        )
    except Exception as exc:
        logger.error("Generation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Local LLM generation failed: {exc}",
        ) from exc

    # Gather related 1-hop notes from top cited notes
    related_notes: list[dict[str, Any]] = []
    seen_related_ids = set()
    top_note_ids = {s.get("note_id") for s in grounded.sources if s.get("note_id")}
    for nid in top_note_ids:
        for rel in registry.related(nid):
            rel_key = rel.note_id or rel.title
            if rel_key not in seen_related_ids and rel.note_id not in top_note_ids:
                seen_related_ids.add(rel_key)
                related_notes.append(rel.to_dict())

    # Log to history
    search_id = history_store.log_search(
        query=req.query,
        results_count=len(grounded.sources),
        answer_preview=grounded.answer,
        retrieval_mode=mode,
    )

    return AskResponse(
        query=req.query,
        answer=grounded.answer,
        citations=grounded.citations,
        sources=grounded.sources,
        related_notes=related_notes[:8],
        retrieval_mode=mode,
        rerank_applied=rerank_applied,
        search_id=search_id,
    )


@app.get("/notes/{note_id}/related", tags=["Graph"], dependencies=[Depends(verify_api_key)])
def get_note_related(note_id: str):
    """Fetch 1-hop outgoing wikilinks and backlinks for a given note."""
    note = registry.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")
    related = registry.related(note_id)
    return {
        "note_id": note_id,
        "title": note.title,
        "rel_path": note.rel_path,
        "related": [r.to_dict() for r in related],
    }


@app.get("/history", tags=["History"], dependencies=[Depends(verify_api_key)])
def get_history(
    limit: int = Query(20, ge=1, le=100),
    distinct: bool = Query(True),
):
    """Retrieve search query history with distinct deduplication."""
    entries = history_store.list_history(limit=limit, distinct=distinct)
    return {"count": len(entries), "history": [e.to_dict() for e in entries]}


"""Generación y búsqueda de embeddings vía proveedor conmutable (WP0)."""
import hashlib
import uuid
from typing import List, Tuple

from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.ai.providers import get_provider
from app.models import EvidenceTextChunk
from app.utils.chunker import chunk_text


def generate_embedding(text: str) -> List[float]:
    """Genera un embedding usando el proveedor activo."""
    return get_provider().embed(text)


def create_chunks_and_embeddings(
    evidence_file_id: uuid.UUID,
    extraction_id: uuid.UUID,
    text: str,
    tenant_id: uuid.UUID,
    db: Session,
    chunk_size: int = 500,
) -> List[EvidenceTextChunk]:
    """
    Divide el texto en chunks y genera embeddings para cada uno.
    """
    chunks_text = chunk_text(text, chunk_size=chunk_size)
    if not chunks_text:
        return []
    
    provider = get_provider()
    chunks = []
    
    for seq, chunk_str in enumerate(chunks_text):
        # Crear el chunk
        chunk = EvidenceTextChunk(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            evidence_file_id=evidence_file_id,
            extraction_id=extraction_id,
            seq=seq,
            text=chunk_str,
            sha256=hashlib.sha256(chunk_str.encode()).hexdigest(),
            character_count=len(chunk_str)
        )
        db.add(chunk)
        db.flush()
        
        # Generar embedding
        embedding = provider.embed(chunk_str)
        vector_str = "[" + ",".join(map(str, embedding)) + "]"
        
        # Insertar vector usando la sintaxis estándar CAST(...)
        db.execute(
            sql_text(
                "INSERT INTO evidence_vectors "
                "(id, chunk_id, tenant_id, model, dim, embedding) "
                "VALUES (:id, :chunk_id, :tenant_id, :model, :dim, CAST(:emb AS vector))"
            ),
            {
                "id": uuid.uuid4(),
                "chunk_id": chunk.id,
                "tenant_id": tenant_id,
                "model": provider.embedding_model,
                "dim": len(embedding),
                "emb": vector_str,
            },
        )
        chunks.append(chunk)
    
    db.commit()
    return chunks


def search_similar_chunks(
    query_text: str,
    audit_id: uuid.UUID,
    db: Session,
    top_k: int = 5,
    threshold: float = 0.6,
) -> List[Tuple[EvidenceTextChunk, float]]:
    """Busca chunks relevantes por similitud coseno dentro de la auditoría."""
    provider = get_provider()
    query_vec = provider.embed(query_text)
    query_str = "[" + ",".join(str(x) for x in query_vec) + "]"
    max_distance = 1.0 - threshold

    rows = db.execute(
        sql_text(
            """
            SELECT c.id,
                   1 - (v.embedding <=> CAST(:q AS vector)) AS similarity
            FROM evidence_text_chunks c
            JOIN evidence_vectors v ON v.chunk_id = c.id
            JOIN evidence_files ef ON ef.id = c.evidence_file_id
            WHERE ef.audit_id = :audit_id
              AND (v.embedding <=> CAST(:q AS vector)) <= :max_distance
            ORDER BY similarity DESC
            LIMIT :top_k
            """
        ),
        {
            "q": query_str,
            "audit_id": audit_id,
            "max_distance": max_distance,
            "top_k": top_k,
        },
    ).fetchall()

    result: List[Tuple[EvidenceTextChunk, float]] = []
    for row in rows:
        chunk = (
            db.query(EvidenceTextChunk)
            .filter(EvidenceTextChunk.id == row.id)
            .first()
        )
        if chunk:
            result.append((chunk, float(row.similarity)))
    return result
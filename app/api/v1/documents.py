"""Document ingestion API endpoints."""

from __future__ import annotations

import io
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.api.dependencies import get_state, get_default_user
from app.ingestion.schema_registry import validate_entity_categories
from app.security.audit_log import DOCUMENT_INGESTED, ENTITY_DETECTED, TOKEN_CREATED

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """Ingest a Markdown document with OKF frontmatter.

    Pipeline: Parse → Detect PII → Tokenize → Build Graph → Store.
    """
    state = get_state()

    # Read uploaded file
    content = await file.read()
    text = content.decode("utf-8")

    # Stage 1: Parse OKF
    try:
        doc = state.parser.parse_text(text, source_path=file.filename or "<upload>")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    doc_id = doc.header.document.id

    # Stage 2: Detect PII entities
    detector = state.get_detector()
    entity_categories = validate_entity_categories(
        doc.header.privacy.entity_categories
    )
    all_entities = []
    tokenized_sentences = []

    for sentence in doc.sentences:
        entities = detector.detect(
            text=sentence,
            entity_categories=entity_categories,
            min_confidence=doc.header.privacy.min_confidence,
        )
        all_entities.extend(entities)

        # Tokenize the sentence
        tokenized_text, tok_entities = state.tokenizer.tokenize_text(
            sentence, entities
        )
        tokenized_sentences.append(tokenized_text)

        # Store each token in the vault
        for tok in tok_entities:
            await state.vault.store(
                token=tok.token,
                entity_type=tok.entity_type,
                original_value=tok.original_value,
                hmac_digest=tok.hmac_digest,
                doc_id=doc_id,
            )

    # Stage 3: Extract triples and build graph
    all_triples = []
    prev_subject = None
    for sentence in tokenized_sentences:
        triples = state.triple_extractor.extract(
            sentence, doc_id=doc_id, prev_subject=prev_subject
        )
        all_triples.extend(triples)
        if triples:
            prev_subject = triples[0].subject

    state.graph_builder.add_triples(all_triples, doc.header)

    # Store document metadata
    state.documents[doc_id] = {
        "id": doc_id,
        "title": doc.header.document.title,
        "classification": doc.header.document.classification.value,
        "department": doc.header.document.department,
        "author": doc.header.document.author,
        "created": str(doc.header.document.created),
        "entity_count": len(all_entities),
        "triple_count": len(all_triples),
    }

    # Audit logging
    state.audit.log(
        DOCUMENT_INGESTED,
        {
            "doc_id": doc_id,
            "title": doc.header.document.title,
            "entities_detected": len(all_entities),
            "triples_extracted": len(all_triples),
        },
    )

    return {
        "status": "ingested",
        "doc_id": doc_id,
        "entities_detected": len(all_entities),
        "triples_extracted": len(all_triples),
        "tokens_stored": state.vault.count(),
    }


@router.get("")
async def list_documents():
    """List all ingested documents (metadata only)."""
    state = get_state()
    return {"documents": list(state.documents.values())}


@router.get("/{doc_id}")
async def get_document(doc_id: str):
    """Get metadata for a specific document."""
    state = get_state()
    doc = state.documents.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    return doc

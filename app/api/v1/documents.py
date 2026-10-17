"""Document ingestion API endpoints."""

from __future__ import annotations

import io
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.api.dependencies import get_state, get_default_user
from app.detection.hint_merge import merge_hints
from app.ingestion.schema_registry import validate_entity_categories
from app.security.audit_log import DOCUMENT_INGESTED, DOCUMENT_DELETED, ENTITY_DETECTED, TOKEN_CREATED

router = APIRouter(prefix="/documents", tags=["documents"])


async def process_document_pipeline(
    content: bytes,
    filename: str,
    title: str | None = None,
    classification: str | None = None,
    department: str | None = None,
    author: str | None = None,
    job_id: str | None = None,
) -> dict:
    """Execute the end-to-end ingestion pipeline with progressive job updates."""
    state = get_state()
    ext = Path(filename).suffix.lower()

    if job_id:
        state.update_job(job_id, status="processing", stage="parsing", progress_pct=15)

    # Stage 1: Parse or Convert into OKFDocument
    if ext == ".pdf" or "pdf" in ext:
        doc = state.pdf_converter.convert(
            content=content,
            filename=filename,
            title=title,
            classification=classification,
            department=department,
            author=author,
        )
    elif ext in (".csv", ".xlsx", ".xls") or "csv" in ext:
        doc = state.csv_converter.convert(
            content=content,
            filename=filename,
            title=title,
            classification=classification,
            department=department,
            author=author,
        )
    elif ext in (".md", ".markdown", ".txt") or "text" in ext:
        text = content.decode("utf-8")
        doc = state.parser.parse_text(text, source_path=filename)
    else:
        raise ValueError(
            f"Unsupported file format '{filename}'. Please upload a .md (OKF Markdown), .pdf, .csv, or .xlsx document."
        )

    doc_id = doc.header.document.id

    # Stage 2: Detect PII entities & Tokenize
    if job_id:
        state.update_job(job_id, status="processing", stage="detecting_pii", progress_pct=35)

    detector = state.get_detector()
    entity_categories = validate_entity_categories(doc.header.privacy.entity_categories)
    all_entities = []
    tokenized_sentences = []
    hints_per_sentence = doc.sentence_hints
    total_sentences = len(doc.sentences)

    for i, sentence in enumerate(doc.sentences):
        entities = detector.detect(
            text=sentence,
            entity_categories=entity_categories,
            min_confidence=doc.header.privacy.min_confidence,
        )
        if i < len(hints_per_sentence):
            entities = merge_hints(
                sentence, entities, hints_per_sentence[i], allowed_types=entity_categories
            )
        all_entities.extend(entities)

        # Tokenize sentence
        tokenized_text, tok_entities = state.tokenizer.tokenize_text(sentence, entities)
        tokenized_sentences.append(tokenized_text)

        # Store each token in the encrypted vault
        for tok in tok_entities:
            await state.vault.store(
                token=tok.token,
                entity_type=tok.entity_type,
                original_value=tok.original_value,
                hmac_digest=tok.hmac_digest,
                doc_id=doc_id,
            )

        if job_id and total_sentences > 0 and (i % max(1, total_sentences // 5) == 0):
            current_pct = 35 + int((i / total_sentences) * 35)
            state.update_job(job_id, status="processing", stage="tokenizing", progress_pct=current_pct)

    # Stage 3: Extract triples and build graph
    if job_id:
        state.update_job(job_id, status="processing", stage="building_graph", progress_pct=80)

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
    state.save_documents()

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

    result = {
        "status": "ingested",
        "doc_id": doc_id,
        "entities_detected": len(all_entities),
        "triples_extracted": len(all_triples),
        "tokens_stored": state.vault.count(),
    }

    if job_id:
        state.update_job(job_id, status="completed", stage="completed", progress_pct=100, result=result)

    return result


async def _run_pipeline_worker(
    content: bytes,
    filename: str,
    title: str | None,
    classification: str | None,
    department: str | None,
    author: str | None,
    job_id: str,
) -> None:
    """Background worker task wrapping document pipeline execution."""
    state = get_state()
    try:
        await process_document_pipeline(
            content=content,
            filename=filename,
            title=title,
            classification=classification,
            department=department,
            author=author,
            job_id=job_id,
        )
    except Exception as exc:
        state.update_job(
            job_id,
            status="failed",
            stage="failed",
            progress_pct=100,
            error=str(exc),
        )


@router.post("/ingest")
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    classification: str | None = Form(None),
    department: str | None = Form(None),
    author: str | None = Form(None),
    background: bool = Form(False),
):
    """Ingest a Markdown, PDF, CSV, or XLSX document synchronously or asynchronously.

    Pipeline: Parse/Convert to OKF → Detect PII → Tokenize → Build Graph → Store.
    """
    state = get_state()
    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()

    # Quick pre-validation on file extension & content type
    supported_exts = {".pdf", ".csv", ".xlsx", ".xls", ".md", ".markdown", ".txt"}
    is_pdf_type = file.content_type and "pdf" in file.content_type
    is_csv_type = file.content_type and "csv" in file.content_type
    is_txt_type = file.content_type and "text" in file.content_type

    if ext not in supported_exts and not (is_pdf_type or is_csv_type or is_txt_type):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{filename}'. Please upload a .md (OKF Markdown), .pdf, .csv, or .xlsx document.",
        )

    # Sanitize optional form parameters
    opt_title = title if isinstance(title, str) and title.strip() else None
    opt_class = classification if isinstance(classification, str) and classification.strip() else None
    opt_dept = department if isinstance(department, str) and department.strip() else None
    opt_author = author if isinstance(author, str) and author.strip() else None

    # Read uploaded file content immediately before request ends
    content = await file.read()

    if background:
        job_id = state.create_job(filename)
        background_tasks.add_task(
            _run_pipeline_worker,
            content=content,
            filename=filename,
            title=opt_title,
            classification=opt_class,
            department=opt_dept,
            author=opt_author,
            job_id=job_id,
        )
        return JSONResponse(
            status_code=202,
            content={
                "status": "processing",
                "job_id": job_id,
                "filename": filename,
                "stage": "queued",
                "progress_pct": 0,
                "check_status_url": f"/api/v1/documents/jobs/{job_id}",
            },
        )

    try:
        return await process_document_pipeline(
            content=content,
            filename=filename,
            title=opt_title,
            classification=opt_class,
            department=opt_dept,
            author=opt_author,
        )
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Failed to decode text file: {e}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/jobs")
async def list_jobs():
    """List all tracked ingestion jobs and their current execution status."""
    state = get_state()
    return {"jobs": state.list_jobs()}


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Retrieve execution status and progress for an asynchronous ingestion job."""
    state = get_state()
    job = state.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job


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


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document from the system, pruning its triples, nodes, and vault tokens."""
    state = get_state()
    doc = state.documents.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")

    del state.documents[doc_id]
    state.save_documents()
    graph_stats = state.graph_builder.remove_document(doc_id)
    tokens_purged = state.vault.delete_by_doc_id(doc_id)

    state.audit.log(
        DOCUMENT_DELETED,
        {
            "doc_id": doc_id,
            "title": doc.get("title", ""),
            "edges_removed": graph_stats.get("edges_removed", 0),
            "nodes_removed": graph_stats.get("nodes_removed", 0),
            "tokens_purged": tokens_purged,
        },
    )

    return {
        "status": "deleted",
        "doc_id": doc_id,
        "edges_removed": graph_stats.get("edges_removed", 0),
        "nodes_removed": graph_stats.get("nodes_removed", 0),
        "tokens_purged": tokens_purged,
    }


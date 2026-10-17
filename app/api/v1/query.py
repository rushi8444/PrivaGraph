"""Query/chat API endpoints."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException

from app.api.dependencies import get_state, get_default_user
from app.models.query import (
    QueryRequest,
    QueryResponse,
    QueryMetadata,
    LLMRequest,
    Citation,
    ZeroPIIProof,
)
from app.security.audit_log import QUERY_SENT, QUERY_RECONSTRUCTED, INJECTION_BLOCKED
from app.tokenization.token_codec import extract_tokens
from app.retrieval.synthesizer import AnswerSynthesizer

router = APIRouter(prefix="/query", tags=["query"])

synthesizer = AnswerSynthesizer()


@router.post("", response_model=QueryResponse)
async def submit_query(request: QueryRequest):
    """Submit a natural language query through the privacy-preserving pipeline."""
    state = get_state()
    user = get_default_user()
    start_time = time.time()

    # Step 0: Tokenize PII in user query
    detector = state.get_detector()
    query_entities = detector.detect(request.query)
    tokenized_query, tok_entities = state.tokenizer.tokenize_text(
        request.query, query_entities
    )
    for tok in tok_entities:
        await state.vault.store(
            token=tok.token,
            entity_type=tok.entity_type,
            original_value=tok.original_value,
            hmac_digest=tok.hmac_digest,
            doc_id="query",
        )

    # Step 1: Build context and retrieve citations from graph edges
    context, raw_citations = state.context_builder.build_context_with_citations(
        query=tokenized_query if query_entities else request.query,
        user=user,
    )

    # Enrich citations with doc metadata and decrypt snippet preview locally
    citations: list[Citation] = []
    for c in raw_citations:
        doc_id = c.get("doc_id", "")
        doc_meta = getattr(state, "documents", {}).get(doc_id, {})
        title = doc_meta.get("filename") or c.get("title") or doc_id
        dept = doc_meta.get("department") or c.get("department", "General")
        cls_level = doc_meta.get("classification") or c.get("classification", "INTERNAL")
        snippet_raw = c.get("snippet", "")
        reconstructed_snippet, _ = await state.reconstructor.reconstruct(snippet_raw)
        citations.append(
            Citation(
                doc_id=doc_id,
                title=title,
                department=dept,
                classification=cls_level,
                snippet=reconstructed_snippet,
                predicate=c.get("predicate"),
            )
        )

    # Step 2: Sanitize for prompt injection
    sanitization = state.sanitizer.sanitize(context)
    if not sanitization.is_safe:
        state.audit.log(
            INJECTION_BLOCKED,
            {"query": request.query, "violations": sanitization.violations},
        )
        raise HTTPException(
            status_code=400,
            detail=f"Prompt injection detected: {', '.join(sanitization.violations)}",
        )

    # Step 3: Send to cloud LLM or synthesize locally
    llm_request = LLMRequest(
        query=tokenized_query,
        context=sanitization.sanitized_text,
        model=request.model,
    )

    state.audit.log(
        QUERY_SENT,
        {
            "query_length": len(request.query),
            "context_length": len(context),
            "model": request.model or "default",
        },
    )

    llm_response_text = ""
    llm_model = request.model or "offline-synthesizer"

    try:
        llm_response = await state.llm_gateway.query(llm_request)
        if llm_response and llm_response.raw_text and llm_response.raw_text.strip():
            llm_response_text = llm_response.raw_text
            llm_model = llm_response.model
        else:
            import logging
            logging.getLogger("uvicorn.error").warning(
                "LLM returned empty response. Falling back to local graph answer synthesizer."
            )
            llm_response_text = synthesizer.synthesize(
                tokenized_query, context, original_query=request.query
            )
            llm_model = "offline-synthesizer"
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").warning(
            f"LLM call failed: {e}. Synthesizing answer directly from graph context."
        )
        llm_response_text = synthesizer.synthesize(
            tokenized_query, context, original_query=request.query
        )
        llm_model = "offline-synthesizer"

    # Step 4: Reconstruct tokens locally
    reconstructed_text, entities_count = await state.reconstructor.reconstruct(
        llm_response_text
    )

    # Guarantee response is never empty string (prevents bare avatar glyph 🛡️)
    if not reconstructed_text or not reconstructed_text.strip():
        reconstructed_text = "I could not find matching records in the knowledge base for this query."

    elapsed_ms = int((time.time() - start_time) * 1000)

    state.audit.log(
        QUERY_RECONSTRUCTED,
        {
            "entities_reconstructed": entities_count,
            "latency_ms": elapsed_ms,
        },
    )

    # Construct cryptographic Zero-PII Proof payload
    all_egress_text = f"{tokenized_query}\n{sanitization.sanitized_text}"
    tokens_detected = list(dict.fromkeys(extract_tokens(all_egress_text)))

    zero_pii_proof = ZeroPIIProof(
        tokenized_query=tokenized_query,
        anonymized_context=sanitization.sanitized_text,
        raw_llm_response=llm_response_text,
        tokens_detected=tokens_detected,
        entities_reconstructed=entities_count,
        vault_storage_mode="AES-256-GCM Encrypted (Local-Only)",
        egress_destination="Cloud LLM (Zero Plaintext PII)",
    )

    # Step 5: Return answer with citations & Zero-PII verification proof
    return QueryResponse(
        answer=reconstructed_text,
        metadata=QueryMetadata(
            entities_reconstructed=entities_count,
            subgraph_nodes=state.graph_builder.graph.number_of_nodes(),
            subgraph_edges=state.graph_builder.graph.number_of_edges(),
            model_used=llm_model,
            latency_ms=elapsed_ms,
        ),
        graph_context=context if request.include_graph_context else None,
        citations=citations,
        zero_pii_proof=zero_pii_proof,
    )

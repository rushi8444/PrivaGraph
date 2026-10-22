"""Query/chat API endpoints."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Depends

from app.api.dependencies import get_state, get_current_user_or_default
from app.models.auth import UserContext
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
from app.security.chat_store import chat_store

router = APIRouter(prefix="/query", tags=["query"])

synthesizer = AnswerSynthesizer()


@router.post("", response_model=QueryResponse)
async def submit_query(
    request: QueryRequest,
    user: UserContext = Depends(get_current_user_or_default),
):
    """Submit a natural language query through the privacy-preserving pipeline."""
    state = get_state()
    start_time = time.perf_counter()
    timings_ms: dict[str, int] = {}

    def elapsed_ms(since: float) -> int:
        return max(0, round((time.perf_counter() - since) * 1000))

    # Manage conversation session & persist user message
    phase_start = time.perf_counter()
    conv_id = request.conversation_id
    if not conv_id and user and user.user_id:
        words = request.query.strip().split()
        title = " ".join(words[:6])
        if len(words) > 6:
            title += "..."
        try:
            conv = await chat_store.create_conversation(user_id=user.user_id, title=title or "New Chat")
            conv_id = conv.id
        except Exception:
            conv_id = None

    if conv_id:
        try:
            await chat_store.add_message(
                conversation_id=conv_id,
                role="user",
                content=request.query,
            )
        except Exception:
            pass
    timings_ms["session_setup_ms"] = elapsed_ms(phase_start)

    # Step 0: Tokenize PII in user query
    phase_start = time.perf_counter()
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
    timings_ms["question_protection_ms"] = elapsed_ms(phase_start)

    # Resolve document scoping for this conversation
    phase_start = time.perf_counter()
    allowed_doc_ids = request.doc_ids
    if allowed_doc_ids is None and conv_id:
        allowed_doc_ids = await chat_store.get_conversation_documents(conv_id)

    # Step 1: Build context and retrieve citations from graph edges
    context, raw_citations = state.context_builder.build_context_with_citations(
        query=tokenized_query if query_entities else request.query,
        user=user,
        allowed_doc_ids=allowed_doc_ids,
    )
    timings_ms["graph_retrieval_ms"] = elapsed_ms(phase_start)

    # Enrich citations with doc metadata and decrypt snippet preview locally
    phase_start = time.perf_counter()
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
    timings_ms["citation_restore_ms"] = elapsed_ms(phase_start)

    # Step 2: Sanitize for prompt injection
    phase_start = time.perf_counter()
    sanitization = state.sanitizer.sanitize(context)
    timings_ms["safety_check_ms"] = elapsed_ms(phase_start)
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
    phase_start = time.perf_counter()

    try:
        llm_response = await state.llm_gateway.query(llm_request)
        if llm_response and llm_response.raw_text and llm_response.raw_text.strip():
            llm_response_text = llm_response.raw_text
            llm_model = llm_response.model
        else:
            import logging
            logging.getLogger("uvicorn.error").warning(
                "LLM returned empty response. Falling back to local evidence synthesis."
            )
            llm_response_text = synthesizer.synthesize(
                tokenized_query, sanitization.sanitized_text, original_query=request.query
            )
            llm_model = "offline-synthesizer"
    except Exception as e:
        import logging
        response = getattr(e, "response", None)
        status_code = getattr(response, "status_code", None)
        provider = getattr(state.llm_gateway, "provider", "unknown")
        error_detail = f"status={status_code}" if status_code else f"type={type(e).__name__}"
        logging.getLogger("uvicorn.error").warning(
            "LLM call failed (provider=%s, %s); using local evidence fallback.",
            provider,
            error_detail,
        )
        llm_response_text = synthesizer.synthesize(
            tokenized_query, sanitization.sanitized_text, original_query=request.query
        )
        llm_model = "offline-synthesizer"
    timings_ms["ai_and_fallback_ms"] = elapsed_ms(phase_start)

    # Step 4: Reconstruct tokens locally
    phase_start = time.perf_counter()
    reconstructed_text, entities_count = await state.reconstructor.reconstruct(
        llm_response_text
    )
    timings_ms["answer_restore_ms"] = elapsed_ms(phase_start)

    # Guarantee response is never empty string (prevents bare avatar glyph 🛡️)
    if not reconstructed_text or not reconstructed_text.strip():
        reconstructed_text = "I could not find matching records in the knowledge base for this query."

    total_elapsed_ms = elapsed_ms(start_time)
    timings_ms["total_ms"] = total_elapsed_ms

    state.audit.log(
        QUERY_RECONSTRUCTED,
        {
            "entities_reconstructed": entities_count,
            "latency_ms": total_elapsed_ms,
            "timings_ms": timings_ms,
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

    # Step 5: Persist assistant message
    if conv_id:
        try:
            await chat_store.add_message(
                conversation_id=conv_id,
                role="assistant",
                content=reconstructed_text,
                citations=[c.model_dump() for c in citations],
                zero_pii_proof=zero_pii_proof.model_dump() if zero_pii_proof else None,
                metadata={
                    "entities_reconstructed": entities_count,
                    "subgraph_nodes": state.graph_builder.graph.number_of_nodes(),
                    "subgraph_edges": state.graph_builder.graph.number_of_edges(),
                    "model_used": llm_model,
                    "latency_ms": total_elapsed_ms,
                    "timings_ms": timings_ms,
                },
            )
        except Exception:
            pass

    # Step 6: Return answer with citations & Zero-PII verification proof
    return QueryResponse(
        answer=reconstructed_text,
        conversation_id=conv_id,
        metadata=QueryMetadata(
            entities_reconstructed=entities_count,
            subgraph_nodes=state.graph_builder.graph.number_of_nodes(),
            subgraph_edges=state.graph_builder.graph.number_of_edges(),
            model_used=llm_model,
            latency_ms=total_elapsed_ms,
            timings_ms=timings_ms,
        ),
        graph_context=context if request.include_graph_context else None,
        citations=citations,
        zero_pii_proof=zero_pii_proof,
    )

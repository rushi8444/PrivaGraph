"""Query/chat API endpoints."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException

from app.api.dependencies import get_state, get_default_user
from app.models.query import QueryRequest, QueryResponse, QueryMetadata, LLMRequest
from app.security.audit_log import QUERY_SENT, QUERY_RECONSTRUCTED, INJECTION_BLOCKED

router = APIRouter(prefix="/query", tags=["query"])


def format_natural_fallback(context_text: str) -> str:
    """Format knowledge graph context into natural, fluent English sentences."""
    import re
    rel_pattern = re.compile(r"-\s*(.+?)\s*--\[([A-Z_]+)\]-->\s*(.+)")
    rels = rel_pattern.findall(context_text)

    if not rels:
        return "I could not find matching records in the knowledge base for this query."

    pred_map = {
        "EARNS": "earns",
        "REPORTS_TO": "reports to",
        "MANAGES": "manages a budget of",
        "WORKS_FOR": "works for",
        "LEADS": "leads",
        "OVERSEES": "oversees",
        "HAS_CONTACT": "can be reached at",
        "IS_A": "is a",
        "RELATED_TO": "is associated with",
    }

    by_subject: dict[str, list[str]] = {}
    seen = set()
    for subj, pred, obj in rels:
        subj, pred, obj = subj.strip(), pred.strip(), obj.strip()
        if (subj, pred, obj) in seen:
            continue
        seen.add((subj, pred, obj))
        if subj not in by_subject:
            by_subject[subj] = []
        verb = pred_map.get(pred, pred.lower().replace("_", " "))
        by_subject[subj].append(f"{verb} {obj}")

    sentences = []
    for subj, facts in by_subject.items():
        if len(facts) == 1:
            sentences.append(f"{subj} {facts[0]}.")
        elif len(facts) == 2:
            sentences.append(f"{subj} {facts[0]} and {facts[1]}.")
        else:
            joined = ", ".join(facts[:-1]) + f", and {facts[-1]}"
            sentences.append(f"{subj} {joined}.")

    return " ".join(sentences)


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

    # Step 1: Build context
    context = state.context_builder.build_context(
        query=tokenized_query if query_entities else request.query,
        user=user,
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

    # Step 3: Send to cloud LLM
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

    try:
        llm_response = await state.llm_gateway.query(llm_request)
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").warning(f"LLM call failed: {e}")
        # Natural conversational fallback generated directly from graph context
        llm_response_text = format_natural_fallback(context)
        llm_model = "offline-graph"
        llm_response = None
    else:
        llm_response_text = llm_response.raw_text
        llm_model = llm_response.model

    # Step 4: Reconstruct tokens locally
    reconstructed_text, entities_count = await state.reconstructor.reconstruct(
        llm_response_text
    )

    elapsed_ms = int((time.time() - start_time) * 1000)

    state.audit.log(
        QUERY_RECONSTRUCTED,
        {
            "entities_reconstructed": entities_count,
            "latency_ms": elapsed_ms,
        },
    )

    # Step 5: Return answer
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
    )

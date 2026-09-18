"""Unit and regression tests for retrieval, normalization, hierarchy traversal, and answer synthesis."""

from __future__ import annotations

from pathlib import Path
import pytest

from app.api.dependencies import get_state
from app.models.auth import UserContext
from app.retrieval.synthesizer import AnswerSynthesizer


@pytest.fixture
def test_state():
    """Create an AppState instance with doc1_hr_compensation.pdf ingested."""
    import asyncio
    state = get_state()
    # Reset in-memory structures for a clean test
    state.graph_builder.graph.clear()
    state.vault._store.clear()
    state.documents.clear()

    pdf_path = Path("tests/fixtures/doc1_hr_compensation.pdf")
    pdf_bytes = pdf_path.read_bytes()
    doc = state.pdf_converter.convert(pdf_bytes, filename=pdf_path.name)
    doc_id = doc.header.document.id

    detector = state.get_detector()
    tokenized_sentences = []
    for sentence in doc.sentences:
        entities = detector.detect(sentence)
        tokenized_text, tok_entities = state.tokenizer.tokenize_text(sentence, entities)
        tokenized_sentences.append(tokenized_text)
        for tok in tok_entities:
            asyncio.run(
                state.vault.store(
                    token=tok.token,
                    entity_type=tok.entity_type,
                    original_value=tok.original_value,
                    hmac_digest=tok.hmac_digest,
                    doc_id=doc_id,
                )
            )

    all_triples = []
    prev_subject = None
    for sentence in tokenized_sentences:
        triples = state.triple_extractor.extract(sentence, doc_id=doc_id, prev_subject=prev_subject)
        all_triples.extend(triples)
        if triples:
            prev_subject = triples[0].subject

    state.graph_builder.add_triples(all_triples, doc.header)
    return state


@pytest.mark.asyncio
async def test_case_1_single_fact_ssn_concise(test_state):
    """1. What is Priya Nandakumar's SSN? -> Concise answer with SSN, no property dump."""
    user = UserContext(user_id="1", username="admin", department="Engineering")
    query = "What is Priya Nandakumar's SSN?"

    detector = test_state.get_detector()
    query_entities = detector.detect(query)
    tokenized_query, _ = test_state.tokenizer.tokenize_text(query, query_entities)

    context = test_state.context_builder.build_context(tokenized_query if query_entities else query, user)
    synthesizer = AnswerSynthesizer()
    answer = synthesizer.synthesize(tokenized_query, context)
    reconstructed, _ = await test_state.reconstructor.reconstruct(answer)

    assert "912-04-7731" in reconstructed
    assert "Priya" in reconstructed
    # Strict rule: no salary or address dump
    assert "$" not in reconstructed
    assert "salary" not in reconstructed.lower()
    assert "Sewickley" not in reconstructed


@pytest.mark.asyncio
async def test_case_2_department_boundary_filtering(test_state):
    """2. List every employee in the Engineering department along with their SSN.
    -> EXACTLY 5 employees (Priya, David, Marcus, Yuki, Ibrahim). Zero from Sales, Finance, Operations.
    """
    user = UserContext(user_id="1", username="admin", department="Engineering")
    query = "List every employee in the Engineering department along with their SSN."

    detector = test_state.get_detector()
    query_entities = detector.detect(query)
    tokenized_query, _ = test_state.tokenizer.tokenize_text(query, query_entities)

    context = test_state.context_builder.build_context(tokenized_query if query_entities else query, user)
    synthesizer = AnswerSynthesizer()
    answer = synthesizer.synthesize(tokenized_query, context)
    reconstructed, _ = await test_state.reconstructor.reconstruct(answer)

    # Must contain the 5 Engineering team members
    assert "Priya Nandakumar" in reconstructed
    assert "David Okonkwo" in reconstructed
    assert "Marcus Feldstein" in reconstructed
    assert "Yuki Tanaka" in reconstructed
    assert "Ibrahim Al" in reconstructed

    # Must NOT leak employees from other departments
    assert "Renata Costa" not in reconstructed
    assert "Owen Fitzgerald" not in reconstructed
    assert "Sofia Beaumont" not in reconstructed
    assert "Desmond Ackerley" not in reconstructed
    assert "Camila Reinholt" not in reconstructed
    assert "Helena Brand" not in reconstructed


@pytest.mark.asyncio
async def test_case_3_alias_and_address_resolution(test_state):
    """3. What is Harold Mbeki-Sorensen's home address? -> 2 Overlook Pointe, Sewickley, PA 15143."""
    user = UserContext(user_id="1", username="admin", department="Executive")
    query = "What is Harold Mbeki-Sorensen's home address?"

    detector = test_state.get_detector()
    query_entities = detector.detect(query)
    tokenized_query, _ = test_state.tokenizer.tokenize_text(query, query_entities)

    context = test_state.context_builder.build_context(tokenized_query if query_entities else query, user)
    synthesizer = AnswerSynthesizer()
    answer = synthesizer.synthesize(tokenized_query, context)
    reconstructed, _ = await test_state.reconstructor.reconstruct(answer)

    assert "2 Overlook Pointe, Sewickley, PA 15143" in reconstructed


@pytest.mark.asyncio
async def test_case_4_multi_hop_hierarchy_chain(test_state):
    """4. Who does Ibrahim Al-Sayed report to, and who does that person report to?
    -> Ibrahim reports to Priya Nandakumar, who reports to Marcus Feldstein.
    """
    user = UserContext(user_id="1", username="admin", department="Engineering")
    query = "Who does Ibrahim Al-Sayed report to, and who does that person report to?"

    detector = test_state.get_detector()
    query_entities = detector.detect(query)
    tokenized_query, _ = test_state.tokenizer.tokenize_text(query, query_entities)

    context = test_state.context_builder.build_context(tokenized_query if query_entities else query, user)
    synthesizer = AnswerSynthesizer()
    answer = synthesizer.synthesize(tokenized_query, context)
    reconstructed, _ = await test_state.reconstructor.reconstruct(answer)

    assert "Ibrahim" in reconstructed
    assert "Priya Nandakumar" in reconstructed
    assert "Marcus Feldstein" in reconstructed
    assert "reports to" in reconstructed


@pytest.mark.asyncio
async def test_case_5_predicate_promotion_filter(test_state):
    """5. Which employees got a salary increase specifically because of a promotion?
    -> Only employees with promotion reasons (David Okonkwo-Reyes, Julian Osei-Kastrati). Excludes merit increases.
    """
    user = UserContext(user_id="1", username="admin", department="HR")
    query = "Which employees got a salary increase specifically because of a promotion?"

    detector = test_state.get_detector()
    query_entities = detector.detect(query)
    tokenized_query, _ = test_state.tokenizer.tokenize_text(query, query_entities)

    context = test_state.context_builder.build_context(tokenized_query if query_entities else query, user)
    synthesizer = AnswerSynthesizer()
    answer = synthesizer.synthesize(tokenized_query, context)
    reconstructed, _ = await test_state.reconstructor.reconstruct(answer)

    # Must contain promotion recipients
    assert "David Okonkwo" in reconstructed
    assert "Julian Osei" in reconstructed

    # Must exclude merit / quota / retention employees
    assert "Nikolai Petrov" not in reconstructed
    assert "Grace Holloway" not in reconstructed
    assert "Baxter Ihenacho" not in reconstructed


@pytest.mark.asyncio
async def test_case_6_narrative_retention_terms(test_state):
    """6. What retention bonus terms were offered to the CEO and CFO?
    -> Retention bonus equal to 100% of base salary upon deal close.
    """
    user = UserContext(user_id="1", username="admin", department="Executive")
    query = "What retention bonus terms were offered to the CEO and CFO?"

    detector = test_state.get_detector()
    query_entities = detector.detect(query)
    tokenized_query, _ = test_state.tokenizer.tokenize_text(query, query_entities)

    context = test_state.context_builder.build_context(tokenized_query if query_entities else query, user)
    synthesizer = AnswerSynthesizer()
    answer = synthesizer.synthesize(tokenized_query, context)
    reconstructed, _ = await test_state.reconstructor.reconstruct(answer)

    assert "100% of base salary" in reconstructed
    assert "deal close" in reconstructed

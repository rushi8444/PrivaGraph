"""Unit and integration tests for Chat-Scoped Document Isolation."""

import pytest
import networkx as nx
from app.graph.graph_builder import KnowledgeGraphBuilder
from app.retrieval.context_builder import ContextBuilder
from app.security.chat_store import chat_store
from app.security.user_store import user_store
from app.graph.triple_extractor import Triple
from datetime import date
from app.graph.graph_builder import KnowledgeGraphBuilder
from app.retrieval.context_builder import ContextBuilder
from app.security.chat_store import chat_store
from app.security.user_store import user_store
from app.graph.triple_extractor import Triple
from app.models.document import OKFHeader, DocumentMeta, GraphConfig, PrivacyConfig, Classification


@pytest.mark.asyncio
async def test_chat_scoped_document_isolation():
    await user_store.init_db()
    await chat_store.init_db()

    # 1. Setup in-memory knowledge graph with 2 isolated documents: doc_a and doc_b
    graph_builder = KnowledgeGraphBuilder()
    
    header_a = OKFHeader(
        document=DocumentMeta(
            id="doc_a",
            title="Doc A",
            classification=Classification.INTERNAL,
            department="Engineering",
            author="Test",
            created=date.today(),
        ),
        privacy=PrivacyConfig(entity_categories=["PERSON"]),
        graph=GraphConfig(namespace="corp"),
    )
    triples_a = [
        Triple(subject="Alice", predicate="REPORTS_TO", object="Bob", doc_id="doc_a", source_sentence="Alice reports to Bob."),
        Triple(subject="Alice", predicate="IN_DEPARTMENT", object="Engineering", doc_id="doc_a", source_sentence="Alice is in Engineering."),
    ]
    graph_builder.add_triples(triples_a, header_a)

    header_b = OKFHeader(
        document=DocumentMeta(
            id="doc_b",
            title="Doc B",
            classification=Classification.INTERNAL,
            department="Sales",
            author="Test",
            created=date.today(),
        ),
        privacy=PrivacyConfig(entity_categories=["PERSON"]),
        graph=GraphConfig(namespace="corp"),
    )
    triples_b = [
        Triple(subject="Charlie", predicate="REPORTS_TO", object="David", doc_id="doc_b", source_sentence="Charlie reports to David."),
        Triple(subject="Charlie", predicate="IN_DEPARTMENT", object="Sales", doc_id="doc_b", source_sentence="Charlie is in Sales."),
    ]
    graph_builder.add_triples(triples_b, header_b)

    # Verify both documents exist in the global graph
    assert graph_builder.graph.has_node("Alice")
    assert graph_builder.graph.has_node("Charlie")

    context_builder = ContextBuilder(graph_builder=graph_builder)

    # 2. Test graph traversal with doc_a scope
    sub_a = graph_builder.get_neighbors("Alice", allowed_doc_ids={"doc_a"})
    assert sub_a.has_node("Alice")
    assert sub_a.has_node("Bob")
    assert not sub_a.has_node("Charlie")
    assert not sub_a.has_node("David")

    # 3. Test graph traversal with doc_b scope when queried for Alice
    sub_b_alice = graph_builder.get_neighbors("Alice", allowed_doc_ids={"doc_b"})
    assert sub_b_alice.number_of_nodes() == 0  # Alice does not exist in doc_b!

    # 4. Test context builder scoping with doc_a
    context_a, citations_a = context_builder.build_context_with_citations(
        query="Who does Alice report to?",
        allowed_doc_ids=["doc_a"],
    )
    assert "Bob" in context_a
    assert all(c["doc_id"] == "doc_a" for c in citations_a)

    # 5. Query for Charlie with doc_a scope -> must NOT find Charlie (ZERO leakage!)
    context_leak_check, citations_leak_check = context_builder.build_context_with_citations(
        query="Who does Charlie report to?",
        allowed_doc_ids=["doc_a"],
    )
    assert "David" not in context_leak_check
    assert len(citations_leak_check) == 0

    # 6. Query for Charlie with doc_b scope -> finds David
    context_b, citations_b = context_builder.build_context_with_citations(
        query="Who does Charlie report to?",
        allowed_doc_ids=["doc_b"],
    )
    assert "David" in context_b
    assert all(c["doc_id"] == "doc_b" for c in citations_b)

    # 7. Test conversation document attachment persistence in PostgreSQL
    import uuid
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    user = await user_store.get_or_create_google_user(email=f"{user_id}@privagraph.internal", username=user_id)

    conv_1 = await chat_store.create_conversation(user_id=user.id, title="Chat 1 (Doc A)")
    conv_2 = await chat_store.create_conversation(user_id=user.id, title="Chat 2 (Doc B)")

    await chat_store.attach_document(conv_1.id, "doc_a")
    await chat_store.attach_document(conv_2.id, "doc_b")

    docs_1 = await chat_store.get_conversation_documents(conv_1.id)
    docs_2 = await chat_store.get_conversation_documents(conv_2.id)

    assert docs_1 == ["doc_a"]
    assert docs_2 == ["doc_b"]

    # Detach test
    await chat_store.detach_document(conv_1.id, "doc_a")
    assert await chat_store.get_conversation_documents(conv_1.id) == []

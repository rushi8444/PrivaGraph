"""Context builder — orchestrates the retrieval pipeline.

Combines query analysis, subgraph extraction,
and serialization into a single context string for the LLM.
"""

from __future__ import annotations

from pathlib import Path
import networkx as nx

from app.graph.graph_builder import KnowledgeGraphBuilder
from app.retrieval.query_analyzer import QueryAnalyzer
from app.models.auth import UserContext


class ContextBuilder:
    """Orchestrates: query → subgraph → LLM context string."""

    def __init__(
        self,
        graph_builder: KnowledgeGraphBuilder,
        query_analyzer: QueryAnalyzer | None = None,
        max_traversal_depth: int = 3,
    ):
        self.graph_builder = graph_builder
        self.query_analyzer = query_analyzer or QueryAnalyzer()
        self.max_depth = max_traversal_depth

    def build_context(
        self,
        query: str,
        user: UserContext | None = None,
        allowed_doc_ids: list[str] | set[str] | None = None,
    ) -> str:
        """Build anonymized LLM context from a user query with optional document scoping."""
        context_str, _ = self.build_context_with_citations(
            query=query,
            user=user,
            allowed_doc_ids=allowed_doc_ids,
        )
        return context_str

    def build_context_with_citations(
        self,
        query: str,
        user: UserContext | None = None,
        allowed_doc_ids: list[str] | set[str] | None = None,
    ) -> tuple[str, list[dict]]:
        """Build anonymized graph context and collect source citations scoped to allowed documents."""
        allowed_set = set(allowed_doc_ids) if allowed_doc_ids is not None else None

        # If scoped to an empty document set, return clean empty state without searching
        if allowed_set is not None and len(allowed_set) == 0:
            return "# Knowledge Graph Context\n\nNo documents are attached to this chat session.", []

        mentioned_tokens = self.query_analyzer.extract_tokens(query)

        query_lower = query.lower()
        target_dept = None
        for dept in [
            "engineering",
            "sales",
            "operations",
            "marketing",
            "customer success",
            "legal",
            "finance",
            "executive",
        ]:
            if dept in query_lower:
                target_dept = dept
                break

        if target_dept:
            dept_nodes = [
                u
                for u, v, data in self.graph_builder.graph.edges(data=True)
                if data.get("predicate") == "IN_DEPARTMENT"
                and target_dept in str(v).lower()
                and (allowed_set is None or data.get("doc_id") in allowed_set)
            ]
            if dept_nodes:
                if mentioned_tokens:
                    filtered = [t for t in mentioned_tokens if t in dept_nodes]
                    mentioned_tokens = filtered
                else:
                    mentioned_tokens = dept_nodes

        if not mentioned_tokens:
            if allowed_set is not None:
                candidate_nodes = [
                    n
                    for n in self.graph_builder.graph.nodes
                    if any(doc in allowed_set for doc in self.graph_builder.graph.nodes[n].get("doc_ids", []))
                    or any(
                        d.get("doc_id") in allowed_set
                        for _, _, d in self.graph_builder.graph.edges(n, data=True)
                    )
                ]
            else:
                candidate_nodes = list(self.graph_builder.graph.nodes)
            mentioned_tokens = self.query_analyzer.match_nodes(query, candidate_nodes)

        if not mentioned_tokens:
            return "# Knowledge Graph Context\n\nNo matching entities found in the graph.", []

        traversal_depth = 1
        if any(w in query_lower for w in ("report", "hierarchy", "manager", "supervisor", "chain", "who does", "leads", "oversees")):
            traversal_depth = max(self.max_depth, 3)

        combined_subgraph = nx.MultiDiGraph()
        for token in mentioned_tokens:
            sub = self.graph_builder.get_neighbors(
                token,
                depth=traversal_depth,
                allowed_doc_ids=allowed_set,
            )
            combined_subgraph = nx.compose(combined_subgraph, sub)

        # If filtering left subgraph empty
        if combined_subgraph.number_of_nodes() == 0 or combined_subgraph.number_of_edges() == 0:
            return "# Knowledge Graph Context\n\nNo matching entities found in the attached documents.", []

        context_str = self.graph_builder.serialize_subgraph(combined_subgraph)

        # Extract source citations strictly from allowed subgraph edge metadata
        citations: list[dict] = []
        seen = set()
        for u, v, data in combined_subgraph.edges(data=True):
            doc_id = data.get("doc_id")
            if not doc_id:
                continue
            if allowed_set is not None and doc_id not in allowed_set:
                continue
            pred = data.get("predicate", "RELATED_TO")
            source_sentence = data.get("source_sentence")
            key = (doc_id, pred, str(u), str(v))
            if key in seen:
                continue
            seen.add(key)
            citations.append({
                "doc_id": doc_id,
                "title": Path(doc_id).stem.replace("_", " ").title(),
                "department": "General",
                "classification": "INTERNAL",
                "predicate": pred,
                "snippet": source_sentence or f"{u} --[{pred}]--> {v}",
            })

        return context_str, citations


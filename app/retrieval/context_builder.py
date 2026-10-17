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

    def build_context(self, query: str, user: UserContext | None = None) -> str:
        """Build anonymized LLM context from a user query.

        Pipeline:
            1. Extract tokens/keywords from the query.
            2. Find matching graph nodes.
            3. Extract subgraphs around matched nodes.
            4. Serialize the subgraph to text.

        Args:
            query: User's natural language question.
            user: Optional authenticated user context.

        Returns:
            Markdown-formatted anonymized context for the LLM.
        """
        # Step 1: Find explicit tokens in query
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
                if data.get("predicate") == "IN_DEPARTMENT" and target_dept in str(v).lower()
            ]
            if dept_nodes:
                if mentioned_tokens:
                    # Enforce department boundary: only retain entities that belong to target_dept
                    filtered = [t for t in mentioned_tokens if t in dept_nodes]
                    mentioned_tokens = filtered
                else:
                    # Roster/aggregate query for the entire department
                    mentioned_tokens = dept_nodes

        # Step 2: If no explicit tokens or department filter, keyword-match against graph nodes
        if not mentioned_tokens:
            all_nodes = list(self.graph_builder.graph.nodes)
            mentioned_tokens = self.query_analyzer.match_nodes(query, all_nodes)

        if not mentioned_tokens:
            return "# Knowledge Graph Context\n\nNo matching entities found in the graph."

        # Step 3: Extract subgraphs around each matched entity (using multi-hop for hierarchies)
        traversal_depth = 1
        if any(w in query_lower for w in ("report", "hierarchy", "manager", "supervisor", "chain", "who does", "leads", "oversees")):
            traversal_depth = max(self.max_depth, 3)

        combined_subgraph = nx.MultiDiGraph()
        for token in mentioned_tokens:
            sub = self.graph_builder.get_neighbors(token, depth=traversal_depth)
            combined_subgraph = nx.compose(combined_subgraph, sub)

        # Step 4: Serialize to LLM-friendly text
        return self.graph_builder.serialize_subgraph(combined_subgraph)

    def build_context_with_citations(
        self,
        query: str,
        user: UserContext | None = None,
    ) -> tuple[str, list[dict]]:
        """Build anonymized graph context and collect source citations."""
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
                if data.get("predicate") == "IN_DEPARTMENT" and target_dept in str(v).lower()
            ]
            if dept_nodes:
                if mentioned_tokens:
                    filtered = [t for t in mentioned_tokens if t in dept_nodes]
                    mentioned_tokens = filtered
                else:
                    mentioned_tokens = dept_nodes

        if not mentioned_tokens:
            all_nodes = list(self.graph_builder.graph.nodes)
            mentioned_tokens = self.query_analyzer.match_nodes(query, all_nodes)

        if not mentioned_tokens:
            return "# Knowledge Graph Context\n\nNo matching entities found in the graph.", []

        traversal_depth = 1
        if any(w in query_lower for w in ("report", "hierarchy", "manager", "supervisor", "chain", "who does", "leads", "oversees")):
            traversal_depth = max(self.max_depth, 3)

        combined_subgraph = nx.MultiDiGraph()
        for token in mentioned_tokens:
            sub = self.graph_builder.get_neighbors(token, depth=traversal_depth)
            combined_subgraph = nx.compose(combined_subgraph, sub)

        context_str = self.graph_builder.serialize_subgraph(combined_subgraph)

        # Extract source citations from subgraph edge metadata
        citations: list[dict] = []
        seen = set()
        for u, v, data in combined_subgraph.edges(data=True):
            doc_id = data.get("doc_id")
            if not doc_id:
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


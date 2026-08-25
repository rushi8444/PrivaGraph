"""Context builder — orchestrates the retrieval pipeline.

Combines query analysis, subgraph extraction, RBAC filtering,
and serialization into a single context string for the LLM.
"""

from __future__ import annotations

import networkx as nx

from app.graph.graph_builder import KnowledgeGraphBuilder
from app.retrieval.rbac_filter import RBACFilter
from app.retrieval.query_analyzer import QueryAnalyzer
from app.models.auth import UserContext


class ContextBuilder:
    """Orchestrates: query → subgraph → RBAC filter → LLM context string."""

    def __init__(
        self,
        graph_builder: KnowledgeGraphBuilder,
        rbac_filter: RBACFilter | None = None,
        query_analyzer: QueryAnalyzer | None = None,
        max_traversal_depth: int = 3,
    ):
        self.graph_builder = graph_builder
        self.rbac_filter = rbac_filter or RBACFilter()
        self.query_analyzer = query_analyzer or QueryAnalyzer()
        self.max_depth = max_traversal_depth

    def build_context(self, query: str, user: UserContext) -> str:
        """Build anonymized LLM context from a user query.

        Pipeline:
            1. Extract tokens/keywords from the query.
            2. Find matching graph nodes.
            3. Extract subgraphs around matched nodes.
            4. Apply RBAC filtering based on user roles.
            5. Serialize the filtered subgraph to text.

        Args:
            query: User's natural language question.
            user: Authenticated user context with roles.

        Returns:
            Markdown-formatted anonymized context for the LLM.
        """
        # Step 1: Find explicit tokens in query
        mentioned_tokens = self.query_analyzer.extract_tokens(query)

        # Step 2: If no explicit tokens, keyword-match against graph nodes
        if not mentioned_tokens:
            all_nodes = list(self.graph_builder.graph.nodes)
            mentioned_tokens = self.query_analyzer.match_nodes(query, all_nodes)

        if not mentioned_tokens:
            return "# Knowledge Graph Context\n\nNo matching entities found in the graph."

        # Step 3: Extract subgraphs around each matched entity
        combined_subgraph = nx.MultiDiGraph()
        for token in mentioned_tokens:
            sub = self.graph_builder.get_neighbors(token, depth=self.max_depth)
            combined_subgraph = nx.compose(combined_subgraph, sub)

        # Step 4: Apply RBAC filtering
        filtered = self.rbac_filter.filter_subgraph(combined_subgraph, user)

        # Step 5: Serialize to LLM-friendly text
        return self.graph_builder.serialize_subgraph(filtered)

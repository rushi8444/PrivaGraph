"""Query analyzer — extracts entity tokens and intent from user queries."""

from __future__ import annotations

from app.tokenization.token_codec import TOKEN_PATTERN


class QueryAnalyzer:
    """Analyzes user queries to identify referenced graph entities.

    For MVP, uses simple token pattern matching.
    Future versions can add semantic similarity matching.
    """

    def extract_tokens(self, query: str) -> list[str]:
        """Extract any PrivaGraph tokens explicitly mentioned in the query.

        Args:
            query: User's natural language query.

        Returns:
            List of token strings found in the query.
        """
        return TOKEN_PATTERN.findall(query)

    def extract_keywords(self, query: str) -> list[str]:
        """Extract meaningful keywords from a query for graph search.

        Args:
            query: User's natural language query.

        Returns:
            List of lowercase keywords (stopwords removed).
        """
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "what", "who",
            "which", "how", "where", "when", "do", "does", "did", "can",
            "could", "would", "should", "will", "has", "have", "had",
            "this", "that", "these", "those", "of", "in", "on", "at",
            "to", "for", "with", "by", "from", "and", "or", "but", "not",
            "about", "me", "my", "tell", "show", "find", "get",
        }
        words = query.lower().split()
        return [w.strip("?.!,;:") for w in words if w.strip("?.!,;:") not in stopwords and len(w) > 2]

    def match_nodes(self, query: str, node_ids: list[str]) -> list[str]:
        """Find graph nodes that match keywords in the query.

        Args:
            query: User's natural language query.
            node_ids: List of all node IDs in the graph.

        Returns:
            Node IDs that contain query keywords.
        """
        keywords = self.extract_keywords(query)
        if not keywords:
            return node_ids[:10]  # Return first 10 nodes as fallback

        matched: list[str] = []
        for node_id in node_ids:
            node_lower = node_id.lower()
            if any(kw in node_lower for kw in keywords):
                matched.append(node_id)

        return matched if matched else node_ids[:10]

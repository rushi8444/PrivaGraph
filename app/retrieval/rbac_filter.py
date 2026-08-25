"""RBAC-based knowledge graph filter.

Filters subgraphs based on the requesting user's roles, enforcing
the access control metadata declared in OKF document headers.
"""

from __future__ import annotations

import networkx as nx

from app.models.auth import UserContext


class RBACFilter:
    """Filters knowledge graph subgraphs based on user roles.

    Rules:
        1. If node has `allowed_roles` → user must have at least one matching role.
        2. If node has `denied_roles` → user must NOT have any matching role.
        3. If no access control metadata → node is accessible (PUBLIC default).
        4. An edge is accessible only if BOTH its source and target nodes pass.
    """

    def filter_subgraph(
        self, subgraph: nx.MultiDiGraph, user: UserContext
    ) -> nx.MultiDiGraph:
        """Return a new subgraph containing only nodes/edges the user may access.

        Args:
            subgraph: The unfiltered subgraph.
            user: The authenticated user context with roles.

        Returns:
            A copy of the subgraph with inaccessible nodes removed.
        """
        accessible_nodes: set[str] = set()

        for node, data in subgraph.nodes(data=True):
            if self._is_node_accessible(data, user):
                accessible_nodes.add(node)

        return subgraph.subgraph(accessible_nodes).copy()

    def _is_node_accessible(self, node_data: dict, user: UserContext) -> bool:
        """Check if a user's roles grant access to a node."""
        denied_roles = set(node_data.get("denied_roles", []))
        if denied_roles & set(user.roles):
            return False  # User has a denied role

        allowed_roles = set(node_data.get("allowed_roles", []))
        if not allowed_roles:
            return True  # No restrictions → accessible

        return bool(allowed_roles & set(user.roles))

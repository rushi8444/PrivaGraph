"""Pytest configuration and test isolation fixtures."""

import pytest
from app.api.dependencies import get_state


@pytest.fixture(autouse=True)
def isolate_test_state():
    """Ensure every test runs with an isolated, clean state and clean database."""
    state = get_state()
    state.graph_builder.graph.clear()
    state.vault.clear()
    state.documents.clear()
    yield
    state.graph_builder.graph.clear()
    state.vault.clear()
    state.documents.clear()

"""PrivaGraph — FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import documents, query, graph, admin
from app.config import settings

app = FastAPI(
    title="PrivaGraph",
    description="Privacy-Preserving Graph RAG Middleware for Enterprise LLMs",
    version="0.1.0",
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(documents.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    from app.api.dependencies import get_state

    state = get_state()
    return {
        "status": "healthy",
        "documents_ingested": len(state.documents),
        "graph_nodes": state.graph_builder.graph.number_of_nodes(),
        "graph_edges": state.graph_builder.graph.number_of_edges(),
        "vault_tokens": state.vault.count(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_ENV == "development",
    )

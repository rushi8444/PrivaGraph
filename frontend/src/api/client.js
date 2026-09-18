const API_BASE = '/api/v1';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  };
  const response = await fetch(url, config);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }
  return response.json();
}

export const api = {
  ingestDocument: async (formData) => {
    const response = await fetch(`${API_BASE}/documents/ingest`, { method: 'POST', body: formData });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `Upload failed (${response.status})`);
    }
    return response.json();
  },
  listDocuments: () => request('/documents'),
  getDocument: (id) => request(`/documents/${id}`),
  deleteDocument: (id) => request(`/documents/${id}`, { method: 'DELETE' }),
  submitQuery: (query, model) =>
    request('/query', {
      method: 'POST',
      body: JSON.stringify({ query, model, include_graph_context: true }),
    }),
  getGraphNodes: () => request('/graph/nodes'),
  getSubgraph: (nodeId) => request(`/graph/subgraph/${nodeId}`),
  getGraphStats: () => request('/graph/stats'),
  getAuditLog: (page = 1, limit = 50) =>
    request(`/admin/audit-log?page=${page}&limit=${limit}`),
  getHealth: () => request('/health'),
};

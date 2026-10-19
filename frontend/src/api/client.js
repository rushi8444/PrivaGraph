const API_BASE = '/api/v1';

function getAuthHeader() {
  const token = localStorage.getItem('privagraph_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
      ...options.headers,
    },
    ...options,
  };

  const response = await fetch(url, config);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    if (response.status === 401) {
      // If unauthorized on protected routes (other than login attempt itself), clear token
      if (!endpoint.includes('/auth/login') && !endpoint.includes('/auth/register')) {
        localStorage.removeItem('privagraph_token');
        localStorage.removeItem('privagraph_user');
      }
    }
    throw new Error(error.detail || `API Error: ${response.status}`);
  }
  return response.json();
}

export const api = {
  // === Authentication ===
  register: (payload) =>
    request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  login: (payload) =>
    request('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getGoogleConfig: () => request('/auth/google/config'),
  loginWithGoogle: (payload) =>
    request('/auth/google', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getMe: () => request('/auth/me'),
  logout: () => request('/auth/logout', { method: 'POST' }),

  // === Documents ===
  ingestDocument: async (formData) => {
    const response = await fetch(`${API_BASE}/documents/ingest`, {
      method: 'POST',
      headers: { ...getAuthHeader() },
      body: formData,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `Upload failed (${response.status})`);
    }
    return response.json();
  },
  ingestDocumentAsync: async (formData) => {
    formData.append('background', 'true');
    const response = await fetch(`${API_BASE}/documents/ingest`, {
      method: 'POST',
      headers: { ...getAuthHeader() },
      body: formData,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `Upload failed (${response.status})`);
    }
    return response.json();
  },
  getJobStatus: (jobId) => request(`/documents/jobs/${jobId}`),
  listJobs: () => request('/documents/jobs'),
  listDocuments: () => request('/documents'),
  getDocument: (id) => request(`/documents/${id}`),
  deleteDocument: (id) => request(`/documents/${id}`, { method: 'DELETE' }),

  // === Query ===
  submitQuery: (query, model) =>
    request('/query', {
      method: 'POST',
      body: JSON.stringify({ query, model, include_graph_context: true }),
    }),

  // === Graph & Audit ===
  getGraphNodes: () => request('/graph/nodes'),
  getSubgraph: (nodeId) => request(`/graph/subgraph/${nodeId}`),
  getGraphStats: () => request('/graph/stats'),
  getAuditLog: (page = 1, limit = 50) =>
    request(`/admin/audit-log?page=${page}&limit=${limit}`),
  getHealth: () => request('/health'),
};

import { useState, useEffect, useCallback } from 'react';
import DocumentUploader from '../components/Documents/DocumentUploader';
import DocumentList from '../components/Documents/DocumentList';
import { api } from '../api/client';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState([]);

  const loadDocs = useCallback(async () => {
    try {
      const data = await api.listDocuments();
      setDocuments(data.documents || []);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  }, []);

  useEffect(() => {
    loadDocs();
  }, [loadDocs]);

  const totalEntities = documents.reduce((acc, d) => acc + (d.entity_count || 0), 0);
  const totalTriples = documents.reduce((acc, d) => acc + (d.triple_count || 0), 0);
  const uniqueDepts = new Set(documents.map((d) => d.department).filter(Boolean)).size;

  return (
    <div className="docs-page-container animate-in">
      {/* Summary KPI Strip */}
      <div className="docs-summary-strip">
        <div className="docs-summary-card">
          <span className="docs-summary-label">Ingested Files</span>
          <span className="docs-summary-value">{documents.length}</span>
        </div>
        <div className="docs-summary-card">
          <span className="docs-summary-label">Tokenized Entities</span>
          <span className="docs-summary-value">{totalEntities}</span>
        </div>
        <div className="docs-summary-card">
          <span className="docs-summary-label">Knowledge Triples</span>
          <span className="docs-summary-value">{totalTriples}</span>
        </div>
        <div className="docs-summary-card">
          <span className="docs-summary-label">Active Departments</span>
          <span className="docs-summary-value">{uniqueDepts}</span>
        </div>
      </div>

      <DocumentUploader onUploaded={loadDocs} />
      <DocumentList documents={documents} onDeleted={loadDocs} />
    </div>
  );
}

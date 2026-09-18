import { useState } from 'react';
import { FileTextIcon, NetworkIcon, KeyIcon, TrashIcon } from '../Common/Icons';
import { api } from '../../api/client';

export default function DocumentList({ documents, onDeleted }) {
  const [deletingId, setDeletingId] = useState(null);
  const [confirmId, setConfirmId] = useState(null);

  if (!documents?.length) {
    return (
      <div
        className="panel-card"
        style={{
          padding: '2.5rem 1rem',
          textAlign: 'center',
          color: 'var(--text-muted)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <FileTextIcon size={28} style={{ opacity: 0.35 }} />
        <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
          No enterprise documents registered
        </div>
        <p style={{ fontSize: '0.8rem', maxWidth: '380px' }}>
          Upload PDF or OKF Markdown documents above to extract SVO triples, tokenize PII, and populate the knowledge graph.
        </p>
      </div>
    );
  }

  const handleDelete = async (docId) => {
    if (confirmId !== docId) {
      setConfirmId(docId);
      return;
    }

    try {
      setDeletingId(docId);
      await api.deleteDocument(docId);
      setConfirmId(null);
      onDeleted?.();
    } catch (err) {
      console.error('Failed to delete document:', err);
      alert(`Failed to delete document: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  const getClassificationClass = (cls) => {
    switch (cls?.toUpperCase()) {
      case 'RESTRICTED':
        return 'badge-restricted';
      case 'CONFIDENTIAL':
        return 'badge-confidential';
      case 'INTERNAL':
        return 'badge-internal';
      default:
        return 'badge-public';
    }
  };

  return (
    <div>
      <div className="doc-section-header">
        <span className="doc-section-title">Ingested Knowledge Base ({documents.length})</span>
      </div>

      <div className="doc-table-container">
        <table className="enterprise-table">
          <thead>
            <tr>
              <th>Document Details</th>
              <th>Classification</th>
              <th>Department</th>
              <th>Author / Date</th>
              <th style={{ textAlign: 'right' }}>Entities</th>
              <th style={{ textAlign: 'right' }}>Graph Triples</th>
              <th style={{ textAlign: 'right', width: '90px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => {
              const isDeleting = deletingId === doc.id;
              const isConfirming = confirmId === doc.id;

              return (
                <tr key={doc.id}>
                  <td>
                    <div className="doc-title-cell">
                      <span className="doc-name">{doc.title || doc.id}</span>
                      <span className="doc-id">{doc.id}</span>
                    </div>
                  </td>
                  <td>
                    <span className={`badge ${getClassificationClass(doc.classification)}`}>
                      {doc.classification || 'INTERNAL'}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                    {doc.department || 'General'}
                  </td>
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column', fontSize: '0.775rem' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>{doc.author || 'System'}</span>
                      <span style={{ color: 'var(--text-muted)' }}>{doc.created || '—'}</span>
                    </div>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <span className="stat-pill">
                      <KeyIcon size={12} style={{ color: 'var(--text-muted)' }} />
                      {doc.entity_count ?? 0}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <span className="stat-pill">
                      <NetworkIcon size={12} style={{ color: 'var(--text-muted)' }} />
                      {doc.triple_count ?? 0}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    {isConfirming ? (
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <button
                          type="button"
                          className="btn btn-sm"
                          style={{
                            padding: '3px 8px',
                            fontSize: '0.7rem',
                            background: 'var(--class-restricted-bg)',
                            color: 'var(--class-restricted-text)',
                            borderColor: 'var(--class-restricted-border)',
                          }}
                          onClick={() => handleDelete(doc.id)}
                          disabled={isDeleting}
                        >
                          {isDeleting ? 'Deleting...' : 'Confirm'}
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-ghost"
                          style={{ padding: '3px 6px', fontSize: '0.7rem' }}
                          onClick={() => setConfirmId(null)}
                          disabled={isDeleting}
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        className="btn btn-sm btn-ghost"
                        style={{
                          padding: '4px 8px',
                          color: 'var(--text-muted)',
                        }}
                        onClick={() => handleDelete(doc.id)}
                        title="Delete document and purge graph triples"
                      >
                        <TrashIcon size={13} style={{ color: 'var(--class-restricted-text)' }} />
                        <span style={{ fontSize: '0.75rem' }}>Delete</span>
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

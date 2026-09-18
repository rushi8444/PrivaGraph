import { useState } from 'react';
import {
  CheckCircleIcon,
  AlertTriangleIcon,
  CopyIcon,
  SearchIcon,
  FileTextIcon,
  ChevronDownIcon,
  ChevronRightIcon,
} from '../Common/Icons';

export default function AuditTable({ entries, loading }) {
  const [filterText, setFilterText] = useState('');
  const [expandedIndex, setExpandedIndex] = useState(null);
  const [copiedHash, setCopiedHash] = useState(null);

  if (loading && !entries?.length) {
    return (
      <div className="panel-card" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        Loading cryptographic audit ledger...
      </div>
    );
  }

  if (!entries?.length) {
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
          No audit ledger entries recorded yet
        </div>
        <p style={{ fontSize: '0.8rem', maxWidth: '380px' }}>
          Document ingestion, query dispatches, token creations, and prompt scans will automatically populate this ledger.
        </p>
      </div>
    );
  }

  const filteredEntries = entries.filter((e) => {
    if (!filterText) return true;
    const term = filterText.toLowerCase();
    const eventType = e.event_type?.toLowerCase() || '';
    const details = JSON.stringify(e.details || {}).toLowerCase();
    return eventType.includes(term) || details.includes(term) || (e.entry_hash || '').includes(term);
  });

  const handleCopyHash = (hash, e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 1600);
  };

  const toggleExpand = (idx) => {
    setExpandedIndex(expandedIndex === idx ? null : idx);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
      {/* Search Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ position: 'relative', width: '280px' }}>
          <SearchIcon
            size={14}
            style={{
              position: 'absolute',
              left: '10px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--text-muted)',
            }}
          />
          <input
            type="text"
            className="input"
            style={{ paddingLeft: '32px', fontSize: '0.8rem' }}
            placeholder="Filter by event or details..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
          />
        </div>

        <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
          Showing {filteredEntries.length} of {entries.length} records
        </span>
      </div>

      {/* Table Container */}
      <div className="doc-table-container">
        <table className="enterprise-table">
          <thead>
            <tr>
              <th style={{ width: '32px' }}></th>
              <th>Timestamp (UTC)</th>
              <th>Event Type</th>
              <th>Operation Details</th>
              <th style={{ textAlign: 'right' }}>Hash Chain Proof</th>
            </tr>
          </thead>
          <tbody>
            {filteredEntries.map((entry, i) => {
              const isExpanded = expandedIndex === i;
              const dateStr = new Date(entry.timestamp).toISOString().replace('T', ' ').slice(0, 19);
              const isValid = entry.chain_valid !== false;

              return (
                <>
                  <tr
                    key={i}
                    onClick={() => toggleExpand(i)}
                    style={{ cursor: 'pointer', background: isExpanded ? 'var(--bg-card-hover)' : undefined }}
                  >
                    <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>
                      {isExpanded ? <ChevronDownIcon size={12} /> : <ChevronRightIcon size={12} />}
                    </td>
                    <td>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        {dateStr}
                      </span>
                    </td>
                    <td>
                      <span className="audit-event-chip">{entry.event_type}</span>
                    </td>
                    <td>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                        {entry.details?.doc_id && `Doc ID: ${entry.details.doc_id} • `}
                        {entry.details?.query && `"${entry.details.query.slice(0, 50)}..." • `}
                        {entry.details?.entities_reconstructed != null && `${entry.details.entities_reconstructed} entities • `}
                        {entry.details?.model && `Model: ${entry.details.model}`}
                        {!entry.details?.doc_id && !entry.details?.query && !entry.details?.entities_reconstructed && !entry.details?.model && (
                          JSON.stringify(entry.details || {}).slice(0, 60)
                        )}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.725rem',
                        }}
                      >
                        {isValid ? (
                          <CheckCircleIcon size={12} style={{ color: 'var(--status-verified)' }} />
                        ) : (
                          <AlertTriangleIcon size={12} style={{ color: 'var(--status-error)' }} />
                        )}
                        <span className="audit-hash-code">
                          {entry.entry_hash ? `${entry.entry_hash.slice(0, 10)}...` : 'GENESIS'}
                        </span>
                        {entry.entry_hash && (
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            style={{ padding: '2px 4px', border: 'none' }}
                            title="Copy SHA-256 Hash"
                            onClick={(e) => handleCopyHash(entry.entry_hash, e)}
                          >
                            <CopyIcon size={11} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>

                  {isExpanded && (
                    <tr key={`${i}-expanded`} style={{ background: '#0e1117' }}>
                      <td colSpan={5} style={{ padding: '12px 18px', borderTop: 'none' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontSize: '0.725rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                              Previous Hash: <span style={{ color: 'var(--text-secondary)' }}>{entry.prev_hash || 'GENESIS'}</span>
                            </span>
                            <span style={{ fontSize: '0.725rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                              Entry Hash: <span style={{ color: 'var(--text-secondary)' }}>{entry.entry_hash}</span>
                            </span>
                          </div>
                          <pre
                            style={{
                              fontFamily: 'var(--font-mono)',
                              fontSize: '0.75rem',
                              padding: '10px',
                              background: '#090b0f',
                              border: '1px solid var(--border-subtle)',
                              borderRadius: 'var(--radius-sm)',
                              color: '#cbd5e1',
                              overflowX: 'auto',
                              maxHeight: '160px',
                            }}
                          >
                            {JSON.stringify(entry.details, null, 2)}
                          </pre>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

import { useState } from 'react';
import {
  UserIcon,
  ShieldIcon,
  CpuIcon,
  UnlockIcon,
  EyeIcon,
  FileTextIcon,
} from '../Common/Icons';
import ZeroPIIModal from './ZeroPIIModal';

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  const [showProofModal, setShowProofModal] = useState(false);

  if (isUser) {
    return (
      <div className="message-entry user animate-in">
        <div className="message-entry-header">
          <UserIcon size={13} />
          <span>Analyst Request</span>
        </div>
        <div className="message-card">{message.text}</div>
      </div>
    );
  }

  const modelUsed = message.metadata?.model_used;
  const isOffline = modelUsed === 'offline-synthesizer' || modelUsed === 'offline-graph';
  const decryptedCount = message.metadata?.entities_reconstructed ?? 0;
  const latencyMs = message.metadata?.latency_ms;
  const citations = message.citations || [];
  const proof = message.zeroPiiProof;

  // Deduplicate citations by doc_id or title
  const uniqueDocCitations = Array.from(
    new Map(citations.map((c) => [c.doc_id || c.title, c])).values()
  );

  return (
    <>
      <div className="message-entry assistant animate-in">
        <div className="message-card">
          {/* Assistant Header / Security Provenance */}
          <div className="message-assistant-header">
            <div className="message-provenance">
              <span className="message-provenance-badge">
                <ShieldIcon size={12} />
                {isOffline ? 'Local Graph Synthesizer' : `Cloud: ${modelUsed}`}
              </span>
              {decryptedCount > 0 && (
                <span className="message-meta-stat">
                  <UnlockIcon size={12} />
                  {decryptedCount} {decryptedCount === 1 ? 'entity' : 'entities'} decrypted
                </span>
              )}
              {latencyMs != null && (
                <span className="message-meta-stat">
                  <CpuIcon size={12} />
                  {latencyMs}ms
                </span>
              )}
            </div>

            {/* Zero-PII Egress Proof Button */}
            {proof && (
              <button
                type="button"
                onClick={() => setShowProofModal(true)}
                className="btn btn-sm btn-ghost"
                style={{
                  fontSize: '0.72rem',
                  padding: '3px 8px',
                  borderRadius: '12px',
                  background: 'rgba(16, 185, 129, 0.1)',
                  color: '#10b981',
                  border: '1px solid rgba(16, 185, 129, 0.25)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  cursor: 'pointer',
                  fontWeight: 500,
                }}
                title="Inspect cryptographic proof that no PII left your local machine"
              >
                <EyeIcon size={13} />
                <span>Verify Zero-PII</span>
              </button>
            )}
          </div>

          {/* Answer Content */}
          <div className="message-assistant-body">{message.text}</div>

          {/* Minimalist Source Document Display */}
          {uniqueDocCitations.length > 0 && (
            <div
              style={{
                marginTop: '10px',
                paddingTop: '8px',
                borderTop: '1px solid var(--border-color, rgba(255,255,255,0.06))',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                flexWrap: 'wrap',
              }}
            >
              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 500 }}>
                Source:
              </span>
              {uniqueDocCitations.map((c, idx) => (
                <span
                  key={idx}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.72rem',
                    background: 'rgba(99, 102, 241, 0.08)',
                    border: '1px solid rgba(99, 102, 241, 0.2)',
                    color: 'var(--text-primary)',
                  }}
                >
                  <FileTextIcon size={11} style={{ color: 'var(--brand-primary, #6366f1)' }} />
                  <span style={{ fontWeight: 500 }}>{c.title}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Zero-PII Egress Proof Modal */}
      {showProofModal && proof && (
        <ZeroPIIModal
          proof={proof}
          answer={message.text}
          onClose={() => setShowProofModal(false)}
        />
      )}
    </>
  );
}

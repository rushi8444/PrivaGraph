import { useState } from 'react';
import {
  UserIcon,
  ShieldIcon,
  CpuIcon,
  UnlockIcon,
  EyeIcon,
  FileTextIcon,
  CopyIcon,
  CheckIcon,
} from '../Common/Icons';
import ZeroPIIModal from './ZeroPIIModal';
import MarkdownContent from './MarkdownContent';

const PROCESS_TIMINGS = [
  ['session_setup_ms', 'Session setup'],
  ['question_protection_ms', 'Protect the question'],
  ['graph_retrieval_ms', 'Find relevant facts'],
  ['citation_restore_ms', 'Restore source snippets'],
  ['safety_check_ms', 'Safety check'],
  ['ai_and_fallback_ms', 'AI response / local fallback'],
  ['answer_restore_ms', 'Restore the answer'],
];

function formatDuration(milliseconds) {
  const value = Number(milliseconds) || 0;
  return value < 1000 ? `${value} ms` : `${(value / 1000).toFixed(value >= 10000 ? 1 : 2)} s`;
}

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  const [showProofModal, setShowProofModal] = useState(false);
  const [copied, setCopied] = useState(false);

  const messageText = message.content || message.text || '';

  const handleCopy = () => {
    navigator.clipboard.writeText(messageText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <div className="message-entry user animate-in">
        <div className="message-entry-header">
          <UserIcon size={13} />
          <span>Analyst Request</span>
        </div>
        <div className="message-card">
          <MarkdownContent text={messageText} />
        </div>
      </div>
    );
  }

  const modelUsed = message.metadata?.model_used;
  const isOffline = modelUsed === 'offline-synthesizer' || modelUsed === 'offline-graph';
  const decryptedCount = message.metadata?.entities_reconstructed ?? 0;
  const latencyMs = message.metadata?.latency_ms;
  const timings = message.metadata?.timings_ms;
  const citations = message.citations || [];
  const proof = message.zeroPiiProof || message.zero_pii_proof;

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
                {isOffline ? 'Local Evidence Fallback' : `Cloud: ${modelUsed}`}
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
                  {formatDuration(latencyMs)}
                </span>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {/* Copy Message Button */}
              <button
                type="button"
                onClick={handleCopy}
                className="btn btn-sm btn-ghost"
                style={{
                  fontSize: '0.72rem',
                  padding: '3px 8px',
                  borderRadius: '12px',
                  background: 'rgba(255, 255, 255, 0.04)',
                  color: copied ? '#10b981' : 'var(--text-muted)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  cursor: 'pointer',
                }}
                title="Copy entire response"
              >
                {copied ? <CheckIcon size={12} /> : <CopyIcon size={12} />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>

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
          </div>

          {/* Answer Content rendered with Markdown and Code highlighting */}
          <div className="message-assistant-body" style={{ marginTop: '8px' }}>
            <MarkdownContent text={messageText} />
          </div>

          {timings && Object.keys(timings).length > 0 && (
            <details className="process-timing-panel" open>
              <summary>
                <span>Process times <small>(approx.)</small></span>
                <strong>Total {formatDuration(timings.total_ms ?? latencyMs)}</strong>
              </summary>
              <div className="process-timing-grid">
                {PROCESS_TIMINGS.filter(([key]) => timings[key] != null).map(([key, label]) => (
                  <div className="process-timing-row" key={key}>
                    <span>{label}</span><b>{formatDuration(timings[key])}</b>
                  </div>
                ))}
              </div>
              <p className="process-timing-note">Server-side time for each step; browser and network overhead may add a little.</p>
            </details>
          )}

          {/* Source Document Display */}
          {uniqueDocCitations.length > 0 && (
            <div
              style={{
                marginTop: '12px',
                paddingTop: '8px',
                borderTop: '1px solid var(--border-color, rgba(255,255,255,0.06))',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                flexWrap: 'wrap',
              }}
            >
              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 500 }}>
                Sources:
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
                  <span style={{ fontWeight: 500 }}>{c.title || c.doc_id}</span>
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
          answer={messageText}
          onClose={() => setShowProofModal(false)}
        />
      )}
    </>
  );
}

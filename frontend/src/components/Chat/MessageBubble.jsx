import { useState } from 'react';
import {
  UserIcon,
  ShieldIcon,
  CpuIcon,
  UnlockIcon,
  CopyIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  CheckCircleIcon,
} from '../Common/Icons';

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  const [showContext, setShowContext] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopyContext = () => {
    if (!message.graphContext) return;
    navigator.clipboard.writeText(message.graphContext);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

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

  return (
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
        </div>

        {/* Answer Content */}
        <div className="message-assistant-body">{message.text}</div>

        {/* Anonymized Graph Context Inspector */}
        {message.graphContext && (
          <div className="context-inspector">
            <button
              type="button"
              className="context-inspector-toggle"
              onClick={() => setShowContext((prev) => !prev)}
            >
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                {showContext ? <ChevronDownIcon size={12} /> : <ChevronRightIcon size={12} />}
                Anonymized Knowledge Graph Context Sent to Model
              </span>
              <span style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>
                {showContext ? 'Collapse' : 'Inspect Triples'}
              </span>
            </button>

            {showContext && (
              <div className="context-inspector-content">
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '6px' }}>
                  <button
                    type="button"
                    className="btn btn-sm btn-ghost"
                    onClick={handleCopyContext}
                    style={{ fontSize: '0.725rem', padding: '3px 8px' }}
                  >
                    {copied ? (
                      <>
                        <CheckCircleIcon size={12} style={{ color: 'var(--status-verified)' }} />
                        Copied
                      </>
                    ) : (
                      <>
                        <CopyIcon size={12} />
                        Copy Raw Triples
                      </>
                    )}
                  </button>
                </div>
                <pre className="context-code-block">{message.graphContext}</pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

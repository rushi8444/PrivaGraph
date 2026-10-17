import { useState } from 'react';
import {
  ShieldIcon,
  LockIcon,
  UnlockIcon,
  CheckCircleIcon,
  CopyIcon,
  XIcon,
  CpuIcon,
  TerminalIcon,
} from '../Common/Icons';

export default function ZeroPIIModal({ proof, answer, onClose }) {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState('side-by-side');

  if (!proof) return null;

  const handleCopyProof = () => {
    const payload = {
      timestamp: new Date().toISOString(),
      proof,
      final_answer: answer,
    };
    navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(5, 7, 12, 0.75)',
        backdropFilter: 'blur(6px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '960px',
          maxHeight: '90vh',
          backgroundColor: 'var(--bg-card, #0f172a)',
          border: '1px solid var(--border-color, #1e293b)',
          borderRadius: '12px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(16, 185, 129, 0.2)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          animation: 'fadeIn 0.15s ease-out',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid var(--border-color, #1e293b)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'linear-gradient(90deg, rgba(16, 185, 129, 0.08) 0%, transparent 100%)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                background: 'rgba(16, 185, 129, 0.15)',
                color: '#10b981',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid rgba(16, 185, 129, 0.3)',
              }}
            >
              <ShieldIcon size={20} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Zero-PII Cryptographic Proof Inspector
                </h3>
                <span
                  style={{
                    fontSize: '0.68rem',
                    padding: '2px 8px',
                    borderRadius: '12px',
                    background: 'rgba(16, 185, 129, 0.15)',
                    color: '#10b981',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                  }}
                >
                  Verified Zero Egress
                </span>
              </div>
              <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                Mathematical proof that no plaintext names, SSNs, or sensitive records left this device.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="btn btn-ghost btn-sm"
            style={{ padding: '6px', borderRadius: '6px', color: 'var(--text-secondary)' }}
            title="Close"
          >
            <XIcon size={18} />
          </button>
        </div>

        {/* Audit Stats Banner */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '12px',
            padding: '14px 20px',
            background: 'rgba(0, 0, 0, 0.25)',
            borderBottom: '1px solid var(--border-color, #1e293b)',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Vault Security
            </span>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#10b981', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <LockIcon size={13} />
              {proof.vault_storage_mode}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Cloud Boundary
            </span>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CpuIcon size={13} />
              {proof.egress_destination}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Tokens Masked
            </span>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <TerminalIcon size={13} />
              {proof.tokens_detected?.length || 0} Keyed HMAC Tokens
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Local Decryptions
            </span>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <UnlockIcon size={13} />
              {proof.entities_reconstructed} Entities Restored Locally
            </span>
          </div>
        </div>

        {/* Detected Tokens Badges Bar */}
        {proof.tokens_detected && proof.tokens_detected.length > 0 && (
          <div
            style={{
              padding: '10px 20px',
              borderBottom: '1px solid var(--border-color, #1e293b)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              flexWrap: 'wrap',
              background: 'rgba(56, 189, 248, 0.03)',
            }}
          >
            <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 600 }}>
              Egress Tokens:
            </span>
            {proof.tokens_detected.map((t, idx) => (
              <span
                key={idx}
                style={{
                  fontSize: '0.72rem',
                  fontFamily: 'var(--font-mono, monospace)',
                  padding: '2px 7px',
                  borderRadius: '4px',
                  background: 'rgba(56, 189, 248, 0.12)',
                  color: '#38bdf8',
                  border: '1px solid rgba(56, 189, 248, 0.25)',
                }}
              >
                {t}
              </span>
            ))}
          </div>
        )}

        {/* Modal Body / Side-by-Side Comparison */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '20px',
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '16px',
          }}
        >
          {/* Left Column: What Cloud LLM Saw */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              border: '1px solid rgba(239, 68, 68, 0.25)',
              borderRadius: '8px',
              padding: '14px',
              backgroundColor: 'rgba(239, 68, 68, 0.03)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    backgroundColor: '#ef4444',
                  }}
                />
                <h4 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Cloud LLM Egress (Anonymized)
                </h4>
              </div>
              <span style={{ fontSize: '0.68rem', color: '#ef4444', fontWeight: 600 }}>
                EXTERNAL BOUNDARY
              </span>
            </div>

            <div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', display: 'block', marginBottom: '4px' }}>
                Tokenized Query Sent to Model:
              </span>
              <div
                style={{
                  fontFamily: 'var(--font-mono, monospace)',
                  fontSize: '0.78rem',
                  padding: '8px 10px',
                  background: 'rgba(0, 0, 0, 0.4)',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-primary)',
                  wordBreak: 'break-word',
                }}
              >
                {proof.tokenized_query}
              </div>
            </div>

            <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', display: 'block', marginBottom: '4px' }}>
                Sanitized Graph Triples Sent to Model:
              </span>
              <pre
                style={{
                  flex: 1,
                  margin: 0,
                  fontFamily: 'var(--font-mono, monospace)',
                  fontSize: '0.75rem',
                  lineHeight: '1.4',
                  padding: '10px',
                  background: 'rgba(0, 0, 0, 0.5)',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)',
                  color: '#94a3b8',
                  maxHeight: '220px',
                  overflowY: 'auto',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {proof.anonymized_context || '(No graph context required for this query)'}
              </pre>
            </div>

            {proof.raw_llm_response && (
              <div>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', display: 'block', marginBottom: '4px' }}>
                  Raw Model Completion (Pre-Decryption):
                </span>
                <div
                  style={{
                    fontFamily: 'var(--font-mono, monospace)',
                    fontSize: '0.75rem',
                    padding: '8px 10px',
                    background: 'rgba(0, 0, 0, 0.4)',
                    borderRadius: '6px',
                    border: '1px solid var(--border-color)',
                    color: '#94a3b8',
                    maxHeight: '120px',
                    overflowY: 'auto',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {proof.raw_llm_response}
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Local On-Premises Ingress */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              borderRadius: '8px',
              padding: '14px',
              backgroundColor: 'rgba(16, 185, 129, 0.03)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    backgroundColor: '#10b981',
                  }}
                />
                <h4 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Local Ingress (Secure Perimeter)
                </h4>
              </div>
              <span style={{ fontSize: '0.68rem', color: '#10b981', fontWeight: 600 }}>
                ON-PREMISES ONLY
              </span>
            </div>

            <div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', display: 'block', marginBottom: '4px' }}>
                Reconstructed Final Answer:
              </span>
              <div
                style={{
                  fontSize: '0.825rem',
                  lineHeight: '1.5',
                  padding: '12px',
                  background: 'rgba(0, 0, 0, 0.4)',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-primary)',
                  maxHeight: '260px',
                  overflowY: 'auto',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {answer}
              </div>
            </div>

            <div
              style={{
                marginTop: 'auto',
                padding: '12px',
                borderRadius: '6px',
                background: 'rgba(16, 185, 129, 0.08)',
                border: '1px solid rgba(16, 185, 129, 0.2)',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#10b981', fontSize: '0.78rem', fontWeight: 600 }}>
                <CheckCircleIcon size={14} />
                Vault Isolation Integrity Check
              </div>
              <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                The cryptographic mapping between tokens and plaintext is held strictly in AES-256-GCM memory on this machine. Neither cloud providers nor network observers can reconstruct identities without local master key access.
              </p>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div
          style={{
            padding: '12px 20px',
            borderTop: '1px solid var(--border-color, #1e293b)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(0, 0, 0, 0.2)',
          }}
        >
          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
            Compliance Standard: GDPR Art. 32 / HIPAA Safe Harbor / SOC2 Type II
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              type="button"
              className="btn btn-sm btn-ghost"
              onClick={handleCopyProof}
              style={{ fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              {copied ? (
                <>
                  <CheckCircleIcon size={13} style={{ color: '#10b981' }} />
                  Copied Audit JSON
                </>
              ) : (
                <>
                  <CopyIcon size={13} />
                  Export Audit JSON
                </>
              )}
            </button>
            <button
              type="button"
              className="btn btn-sm btn-primary"
              onClick={onClose}
              style={{ fontSize: '0.78rem' }}
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

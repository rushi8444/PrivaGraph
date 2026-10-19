import { useState, useRef, useEffect, useCallback } from 'react';
import MessageBubble from './MessageBubble';
import { useChat } from '../../context/ChatContext';
import { api } from '../../api/client';
import {
  ShieldIcon,
  SendIcon,
  AlertTriangleIcon,
  LockIcon,
  NetworkIcon,
  TerminalIcon,
  FileTextIcon,
  UploadCloudIcon,
  XIcon,
  PlusIcon,
  CheckIcon,
} from '../Common/Icons';

const STARTER_PROMPTS = [
  {
    title: 'Organizational Hierarchy',
    prompt: 'Who does Alice Johnson report to, and what department does she lead?',
    icon: NetworkIcon,
  },
  {
    title: 'Department Roster',
    prompt: 'List all employees in the Engineering department and their managers.',
    icon: TerminalIcon,
  },
  {
    title: 'Executive Compensation',
    prompt: 'What is the compensation structure for Director roles without exposing individual SSNs?',
    icon: LockIcon,
  },
  {
    title: 'Confidentiality Policies',
    prompt: 'Summarize the confidentiality classification levels and audit access policies.',
    icon: ShieldIcon,
  },
];

export default function ChatPanel() {
  const {
    messages,
    attachedDocuments,
    loading,
    errorMessage,
    textareaRef,
    handleSendQuery,
    handleAttachDocument,
    handleDetachDocument,
    handleDirectFileUpload,
  } = useChat();

  const [input, setInput] = useState('');
  const [showAttachModal, setShowAttachModal] = useState(false);
  const [availableDocuments, setAvailableDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);

  const messagesEnd = useRef(null);
  const fileInputRef = useRef(null);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Load available documents catalog when modal opens
  const fetchAvailableDocuments = useCallback(async () => {
    try {
      const res = await api.listDocuments();
      setAvailableDocuments(res?.documents || []);
    } catch (err) {
      console.warn('Could not load documents catalog:', err);
    }
  }, []);

  useEffect(() => {
    fetchAvailableDocuments();
  }, [fetchAvailableDocuments]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  const handleInputChange = (e) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  };

  const onSend = (queryText) => {
    const text = queryText || input;
    if (!text.trim() || loading) return;
    handleSendQuery(text);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const onUploadFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await handleDirectFileUpload(file);
      await fetchAvailableDocuments();
      setShowAttachModal(false);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="chat-container">
      {/* Document Scope Toolbar */}
      <div className="chat-scope-bar">
        <div className="chat-scope-left">
          <span className="chat-scope-label">
            <FileTextIcon size={14} style={{ color: 'var(--status-verified)' }} />
            <span>Scope:</span>
          </span>

          {attachedDocuments.length === 0 ? (
            <span className="chat-scope-empty-hint">
              No documents scoped to this chat. Click "+ Attach Document" to add one.
            </span>
          ) : (
            <div className="chat-scope-pill-list">
              {attachedDocuments.map((doc) => (
                <span key={doc.doc_id} className="chat-scope-pill" title={doc.doc_id}>
                  <span>{doc.title || doc.doc_id}</span>
                  <button
                    type="button"
                    className="chat-scope-pill-remove"
                    onClick={(e) => handleDetachDocument(doc.doc_id, e)}
                    title="Detach document from this chat"
                  >
                    <XIcon size={11} />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        <button
          type="button"
          className="chat-scope-attach-btn"
          onClick={() => {
            fetchAvailableDocuments();
            setShowAttachModal(true);
          }}
          title="Attach or upload document for this chat"
        >
          <PlusIcon size={13} />
          <span>Attach Document</span>
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div className="chat-messages-area">
        {messages.length === 0 ? (
          <div className="chat-empty-state">
            <div className="chat-empty-icon-box">
              <ShieldIcon size={24} />
            </div>
            <div className="chat-empty-title">Confidential Query Gateway</div>
            <p className="chat-empty-description">
              Ask questions scoped strictly to your attached documents. Knowledge from other
              conversations or unattached documents remains completely isolated.
            </p>

            {/* Starter Prompt Cards */}
            <div className="chat-empty-starters">
              {STARTER_PROMPTS.map((item, idx) => {
                const Icon = item.icon;
                return (
                  <div
                    key={idx}
                    className="chat-starter-card"
                    onClick={() => onSend(item.prompt)}
                  >
                    <div className="chat-starter-title">
                      <Icon size={14} style={{ color: 'var(--status-verified)' }} />
                      <span>{item.title}</span>
                    </div>
                    <div className="chat-starter-prompt">{item.prompt}</div>
                  </div>
                );
              })}
            </div>

            {/* Feature Highlights */}
            <div className="chat-empty-features">
              <div className="chat-empty-feature-card">
                <h4>
                  <LockIcon size={14} style={{ color: 'var(--status-verified)' }} />
                  Chat-Scoped Isolation
                </h4>
                <p>Each chat session only queries facts and entities from its explicitly attached documents.</p>
              </div>
              <div className="chat-empty-feature-card">
                <h4>
                  <NetworkIcon size={14} style={{ color: 'var(--status-verified)' }} />
                  Multi-Hop BFS Traversal
                </h4>
                <p>Traverses relations inside allowed documents without cross-document contamination.</p>
              </div>
              <div className="chat-empty-feature-card">
                <h4>
                  <TerminalIcon size={14} style={{ color: 'var(--status-verified)' }} />
                  Zero Plaintext PII
                </h4>
                <p>Real names, SSNs, and salaries remain encrypted in your local vault at all times.</p>
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
        )}

        {loading && (
          <div className="message-entry assistant animate-in">
            <div
              className="message-card"
              style={{
                padding: '12px 16px',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
              }}
            >
              <div className="sidebar-pulse-dot" style={{ width: '8px', height: '8px' }} />
              <span
                style={{
                  fontSize: '0.825rem',
                  color: 'var(--text-secondary)',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                Searching scoped documents & verifying trust boundary...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEnd} />
      </div>

      {/* Error alert if any */}
      {errorMessage && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 12px',
            background: 'var(--class-restricted-bg)',
            border: '1px solid var(--class-restricted-border)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--class-restricted-text)',
            fontSize: '0.8rem',
          }}
        >
          <AlertTriangleIcon size={14} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Input Form */}
      <div className="chat-input-container">
        <textarea
          ref={textareaRef}
          className="chat-input-textarea"
          rows={1}
          placeholder={
            attachedDocuments.length === 0
              ? 'Ask a question (or attach a document above to scope this chat)...'
              : `Ask a question about ${attachedDocuments.map((d) => d.title || d.doc_id).join(', ')}...`
          }
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <div className="chat-input-footer">
          <div className="chat-input-hint">
            <span>Press Enter to send, Shift+Enter for newline</span>
          </div>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => onSend()}
            disabled={loading || !input.trim()}
          >
            <SendIcon size={13} />
            <span>Send</span>
          </button>
        </div>
      </div>

      {/* Attach / Upload Document Modal */}
      {showAttachModal && (
        <div className="attach-modal-overlay" onClick={() => setShowAttachModal(false)}>
          <div className="attach-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="attach-modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileTextIcon size={16} style={{ color: 'var(--status-verified)' }} />
                <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                  Attach Document to this Chat
                </span>
              </div>
              <button
                type="button"
                className="chat-scope-pill-remove"
                style={{ padding: '4px' }}
                onClick={() => setShowAttachModal(false)}
              >
                <XIcon size={16} />
              </button>
            </div>

            <div className="attach-modal-body">
              {/* Direct Upload Button */}
              <div
                style={{
                  padding: '16px',
                  background: 'var(--bg-card-subtle)',
                  border: '1px dashed var(--border-default)',
                  borderRadius: 'var(--radius-md)',
                  textAlign: 'center',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <UploadCloudIcon size={24} style={{ color: 'var(--status-verified)' }} />
                <div style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Upload New Document for this Chat
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Supports PDF, CSV, Excel, and Markdown
                </div>
                <input
                  type="file"
                  ref={fileInputRef}
                  style={{ display: 'none' }}
                  onChange={onUploadFile}
                  accept=".pdf,.csv,.xlsx,.xls,.md,.txt"
                />
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  style={{ marginTop: '4px' }}
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                >
                  {uploading ? 'Ingesting & Tokenizing...' : 'Choose File to Upload'}
                </button>
              </div>

              {/* Select from existing documents */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div
                  style={{
                    fontSize: '0.725rem',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                >
                  Or Select From Existing Documents:
                </div>

                {availableDocuments.length === 0 ? (
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center', padding: '12px' }}>
                    No other documents in the vault yet. Upload one above!
                  </div>
                ) : (
                  availableDocuments.map((doc) => {
                    const isAttached = attachedDocuments.some((d) => d.doc_id === doc.id);
                    return (
                      <div
                        key={doc.id}
                        className={`attach-doc-option ${isAttached ? 'attached' : ''}`}
                        onClick={() => {
                          if (isAttached) {
                            handleDetachDocument(doc.id);
                          } else {
                            handleAttachDocument(doc.id);
                          }
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <FileTextIcon size={16} style={{ color: isAttached ? 'var(--status-verified)' : 'var(--text-muted)' }} />
                          <div>
                            <div style={{ fontSize: '0.825rem', fontWeight: 550, color: 'var(--text-primary)' }}>
                              {doc.title || doc.id}
                            </div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                              {doc.department || 'General'} • {doc.classification || 'INTERNAL'}
                            </div>
                          </div>
                        </div>

                        <div>
                          {isAttached ? (
                            <span
                              style={{
                                fontSize: '0.725rem',
                                color: 'var(--status-verified)',
                                fontWeight: 600,
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px',
                              }}
                            >
                              <CheckIcon size={12} />
                              Attached
                            </span>
                          ) : (
                            <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>
                              + Attach
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

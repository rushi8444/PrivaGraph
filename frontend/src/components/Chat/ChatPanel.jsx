import { useState, useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';
import { api } from '../../api/client';
import {
  ShieldIcon,
  SendIcon,
  SearchIcon,
  AlertTriangleIcon,
  LockIcon,
  NetworkIcon,
  TerminalIcon,
} from '../Common/Icons';



export default function ChatPanel() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const messagesEnd = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSendQuery = async (queryText) => {
    const query = (queryText || input).trim();
    if (!query || loading) return;

    setErrorMessage(null);
    const userMsg = { id: Date.now(), role: 'user', text: query };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    try {
      const data = await api.submitQuery(query);
      const assistantMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        text: data.answer,
        metadata: data.metadata,
        graphContext: data.graph_context,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setErrorMessage(err.message);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          text: `Query failed: ${err.message}`,
          metadata: { model_used: 'error-handler', entities_reconstructed: 0 },
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendQuery();
    }
  };

  const handleInputChange = (e) => {
    setInput(e.target.value);
    // Auto-adjust height up to 160px
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  };

  return (
    <div className="chat-container">


      {/* Messages Scroll Area */}
      <div className="chat-messages-area">
        {messages.length === 0 ? (
          <div className="chat-empty-state">
            <div className="chat-empty-icon-box">
              <ShieldIcon size={24} />
            </div>
            <div className="chat-empty-title">Confidential Query Gateway</div>
            <p className="chat-empty-description">
              Query across enterprise repositories with zero raw PII cloud exposure.
              Entities are tokenized deterministically via keyed HMAC-SHA256, mapped to an in-memory
              knowledge graph, and resolved through an encrypted local AES-256-GCM vault.
            </p>

            <div className="chat-empty-features">
              <div className="chat-empty-feature-card">
                <h4>
                  <LockIcon size={14} style={{ color: 'var(--status-verified)' }} />
                  Local Vault Protection
                </h4>
                <p>Real names, SSNs, and salaries are isolated on-premises in encrypted memory.</p>
              </div>
              <div className="chat-empty-feature-card">
                <h4>
                  <NetworkIcon size={14} style={{ color: 'var(--status-verified)' }} />
                  Multi-Hop BFS Traversal
                </h4>
                <p>Resolves reporting hierarchies and department boundaries without cross-leakage.</p>
              </div>
              <div className="chat-empty-feature-card">
                <h4>
                  <TerminalIcon size={14} style={{ color: 'var(--status-verified)' }} />
                  Offline Synthesizer
                </h4>
                <p>Generates deterministic natural answers directly from graph triples when offline.</p>
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
        )}

        {loading && (
          <div className="message-entry assistant animate-in">
            <div className="message-card" style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div className="sidebar-pulse-dot" style={{ width: '8px', height: '8px' }} />
              <span style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                Traversing knowledge graph & verifying trust boundary...
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
          placeholder="Ask a question..."
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
            onClick={() => handleSendQuery()}
            disabled={loading || !input.trim()}
          >
            <SendIcon size={13} />
            <span>Send</span>
          </button>
        </div>
      </div>
    </div>
  );
}

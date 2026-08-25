import { useState, useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';
import { api } from '../../api/client';

export default function ChatPanel() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showContext, setShowContext] = useState({});
  const messagesEnd = useRef(null);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const query = input.trim();
    if (!query || loading) return;

    const userMsg = { id: Date.now(), role: 'user', text: query };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

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
      setMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, role: 'assistant', text: `⚠️ Error: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleContext = (msgId) => {
    setShowContext((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty-icon">🛡️</div>
            <div className="chat-empty-title">Privacy-Preserving Query</div>
            <div className="chat-empty-hint">
              Ask questions about your enterprise documents. All PII is tokenized
              before reaching the cloud LLM and reconstructed locally.
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id}>
              <MessageBubble message={msg} />
              {msg.graphContext && (
                <>
                  <div
                    className="chat-context-toggle"
                    onClick={() => toggleContext(msg.id)}
                  >
                    {showContext[msg.id] ? '▾ Hide' : '▸ Show'} anonymized context sent to LLM
                  </div>
                  {showContext[msg.id] && (
                    <div className="chat-context-panel">{msg.graphContext}</div>
                  )}
                </>
              )}
            </div>
          ))
        )}
        <div ref={messagesEnd} />
      </div>
      <div className="chat-input-row">
        <textarea
          className="chat-input"
          rows={1}
          placeholder="Ask a question about your documents..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button
          className="chat-send-btn"
          onClick={handleSend}
          disabled={loading || !input.trim()}
        >
          {loading ? '⏳' : 'Send'}
        </button>
      </div>
    </div>
  );
}

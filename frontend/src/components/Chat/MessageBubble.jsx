export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  return (
    <div className={`message-bubble ${message.role}`}>
      <div className="message-avatar">{isUser ? '👤' : '🛡️'}</div>
      <div>
        <div className="message-content">{message.text}</div>
        {message.metadata && (
          <div className="message-meta" style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '6px', fontSize: '12px', opacity: 0.85 }}>
            {message.metadata.model_used && (
              <span
                className="message-meta-item"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  background: message.metadata.model_used === 'offline-graph' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(99, 102, 241, 0.2)',
                  color: message.metadata.model_used === 'offline-graph' ? '#fcd34d' : '#a5b4fc',
                  border: `1px solid ${message.metadata.model_used === 'offline-graph' ? 'rgba(245, 158, 11, 0.4)' : 'rgba(99, 102, 241, 0.4)'}`
                }}
              >
                {message.metadata.model_used === 'offline-graph' ? '⚡ Offline Graph' : `🤖 ${message.metadata.model_used}`}
              </span>
            )}
            {message.metadata.entities_reconstructed != null && (
              <span className="message-meta-item">
                🔓 {message.metadata.entities_reconstructed} decrypted
              </span>
            )}
            {message.metadata.latency_ms != null && (
              <span className="message-meta-item">
                ⚡ {message.metadata.latency_ms}ms
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

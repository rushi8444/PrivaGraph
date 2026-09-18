import { useState, useRef } from 'react';
import { api } from '../../api/client';

export default function DocumentUploader({ onUploaded }) {
  const [dragover, setDragover] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState(null); // { type: 'error' | 'success', text: string }
  const fileInput = useRef(null);

  const handleFiles = async (files) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setMessage(null);

    let successCount = 0;
    let errors = [];

    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);
      try {
        await api.ingestDocument(formData);
        successCount++;
      } catch (err) {
        console.error('Upload failed:', err);
        errors.push(`${file.name}: ${err.message}`);
      }
    }

    setUploading(false);

    if (errors.length > 0) {
      setMessage({
        type: 'error',
        text: errors.join(' | ') + ' (Markdown files require OKF YAML frontmatter; PDFs must contain extractable text)',
      });
    } else if (successCount > 0) {
      setMessage({
        type: 'success',
        text: `Successfully ingested ${successCount} document${successCount > 1 ? 's' : ''}!`,
      });
    }

    if (successCount > 0) {
      onUploaded?.();
    }
  };

  return (
    <div style={{ marginBottom: 'var(--space-lg)' }}>
      <div
        className={`upload-zone ${dragover ? 'dragover' : ''}`}
        onClick={() => fileInput.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragover(true); }}
        onDragLeave={() => setDragover(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragover(false);
          handleFiles(e.dataTransfer.files);
        }}
      >
        <div className="upload-zone-icon">📄</div>
        <div className="upload-zone-text">
          {uploading ? 'Ingesting & Tokenizing Document...' : 'Drop Markdown (.md) or PDF (.pdf) files here or click to browse'}
        </div>
        <div className="upload-zone-hint">Supports .md (with OKF YAML frontmatter) and .pdf (auto-converted to OKF)</div>
        <input
          ref={fileInput}
          type="file"
          accept=".md,.pdf"
          multiple
          hidden
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {message && (
        <div
          style={{
            marginTop: '12px',
            padding: '12px 16px',
            borderRadius: '8px',
            fontSize: '14px',
            background: message.type === 'error' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
            border: `1px solid ${message.type === 'error' ? 'rgba(239, 68, 68, 0.4)' : 'rgba(16, 185, 129, 0.4)'}`,
            color: message.type === 'error' ? '#fca5a5' : '#86efac',
          }}
        >
          {message.type === 'error' ? '⚠️ ' : '✅ '}
          {message.text}
        </div>
      )}
    </div>
  );
}

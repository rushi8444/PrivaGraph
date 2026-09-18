import { useState, useRef } from 'react';
import { api } from '../../api/client';
import {
  UploadCloudIcon,
  CheckCircleIcon,
  AlertTriangleIcon,
  FileTextIcon,
} from '../Common/Icons';

export default function DocumentUploader({ onUploaded }) {
  const [dragover, setDragover] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState(null);
  const fileInput = useRef(null);

  const handleFiles = async (files) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setMessage(null);

    let successCount = 0;
    const errors = [];

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
        text: `${errors.join(' | ')} (Markdown requires OKF frontmatter; PDFs must contain extractable text)`,
      });
    } else if (successCount > 0) {
      setMessage({
        type: 'success',
        text: `Successfully ingested ${successCount} document${successCount > 1 ? 's' : ''} into knowledge graph.`,
      });
    }

    if (successCount > 0) {
      onUploaded?.();
    }
  };

  return (
    <div style={{ marginBottom: 'var(--space-md)' }}>
      <div
        className={`upload-dropzone ${dragover ? 'dragover' : ''}`}
        onClick={() => fileInput.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragover(true); }}
        onDragLeave={() => setDragover(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragover(false);
          handleFiles(e.dataTransfer.files);
        }}
      >
        <div className="upload-icon-container">
          <UploadCloudIcon size={24} />
        </div>
        <div>
          <div className="upload-primary-text">
            {uploading ? 'Processing, Tokenizing & Linking Triples...' : 'Upload enterprise documents to knowledge graph'}
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '3px' }}>
            Drag and drop files here, or click to browse your local filesystem
          </p>
        </div>

        <div className="upload-formats-strip">
          <span className="upload-format-tag">PDF (Native PyMuPDF)</span>
          <span className="upload-format-tag">Markdown (.md with OKF YAML)</span>
          <span className="upload-format-tag">Text (.txt)</span>
        </div>

        <input
          ref={fileInput}
          type="file"
          accept=".md,.pdf,.txt"
          multiple
          hidden
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {message && (
        <div
          style={{
            marginTop: '10px',
            padding: '10px 14px',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.825rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: message.type === 'error' ? 'var(--class-restricted-bg)' : 'var(--class-public-bg)',
            border: `1px solid ${message.type === 'error' ? 'var(--class-restricted-border)' : 'var(--class-public-border)'}`,
            color: message.type === 'error' ? 'var(--class-restricted-text)' : 'var(--class-public-text)',
          }}
        >
          {message.type === 'error' ? <AlertTriangleIcon size={14} /> : <CheckCircleIcon size={14} />}
          <span>{message.text}</span>
        </div>
      )}
    </div>
  );
}

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
  const [progressState, setProgressState] = useState(null); // { filename, stage, progress_pct }
  const [message, setMessage] = useState(null);
  const fileInput = useRef(null);

  const getStageLabel = (stage) => {
    switch (stage) {
      case 'queued': return 'Queued for processing...';
      case 'parsing': return 'Parsing & converting structure...';
      case 'detecting_pii': return 'Scanning PII entities (Presidio NER)...';
      case 'tokenizing': return 'Generating high-entropy tokens & vaulting...';
      case 'building_graph': return 'Extracting triples & linking graph...';
      case 'completed': return 'Document successfully ingested!';
      default: return 'Processing document...';
    }
  };

  const pollJobUntilDone = async (jobId, filename) => {
    while (true) {
      await new Promise((r) => setTimeout(r, 350));
      const job = await api.getJobStatus(jobId);
      setProgressState({
        filename,
        stage: job.stage,
        progress_pct: job.progress_pct || 0,
      });

      if (job.status === 'completed') {
        return job.result;
      }
      if (job.status === 'failed') {
        throw new Error(job.error || 'Ingestion pipeline failed');
      }
    }
  };

  const handleFiles = async (files) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setMessage(null);
    setProgressState(null);

    let successCount = 0;
    const errors = [];

    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);
      try {
        setProgressState({ filename: file.name, stage: 'queued', progress_pct: 5 });
        const initial = await api.ingestDocumentAsync(formData);
        if (initial.job_id) {
          await pollJobUntilDone(initial.job_id, file.name);
        }
        successCount++;
      } catch (err) {
        console.error('Upload failed:', err);
        errors.push(`${file.name}: ${err.message}`);
      }
    }

    setUploading(false);
    setProgressState(null);

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
            {uploading ? (
              <span style={{ color: 'var(--color-accent, #6366f1)', fontWeight: 600 }}>
                {progressState ? getStageLabel(progressState.stage) : 'Processing document...'}
              </span>
            ) : (
              'Upload enterprise documents to knowledge graph'
            )}
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '3px' }}>
            {uploading && progressState
              ? `${progressState.filename} — ${progressState.progress_pct}%`
              : 'Drag and drop files here, or click to browse your local filesystem'}
          </p>
        </div>

        {uploading && progressState && (
          <div
            style={{
              width: '85%',
              maxWidth: '420px',
              height: '6px',
              backgroundColor: 'rgba(255, 255, 255, 0.08)',
              borderRadius: '4px',
              overflow: 'hidden',
              marginTop: '10px',
            }}
          >
            <div
              style={{
                width: `${Math.max(5, progressState.progress_pct)}%`,
                height: '100%',
                backgroundColor: 'var(--color-accent, #6366f1)',
                borderRadius: '4px',
                transition: 'width 0.3s ease-in-out',
              }}
            />
          </div>
        )}

        <div className="upload-formats-strip">
          <span className="upload-format-tag">PDF (Native PyMuPDF)</span>
          <span className="upload-format-tag">Markdown (.md with OKF YAML)</span>
          <span className="upload-format-tag">Text (.txt)</span>
          <span className="upload-format-tag">CSV (.csv tables)</span>
        </div>

        <input
          ref={fileInput}
          type="file"
          accept=".md,.pdf,.txt,.csv"
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

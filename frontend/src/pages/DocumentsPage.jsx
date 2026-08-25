import { useState, useEffect, useCallback } from 'react';
import DocumentUploader from '../components/Documents/DocumentUploader';
import DocumentList from '../components/Documents/DocumentList';
import { api } from '../api/client';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState([]);

  const loadDocs = useCallback(async () => {
    try {
      const data = await api.listDocuments();
      setDocuments(data.documents || []);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  }, []);

  useEffect(() => { loadDocs(); }, [loadDocs]);

  return (
    <div className="animate-in">
      <DocumentUploader onUploaded={loadDocs} />
      <DocumentList documents={documents} />
    </div>
  );
}

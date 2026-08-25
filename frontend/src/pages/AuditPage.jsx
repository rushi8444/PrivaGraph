import { useState, useEffect } from 'react';
import AuditTable from '../components/AuditLog/AuditTable';
import { api } from '../api/client';

export default function AuditPage() {
  const [entries, setEntries] = useState([]);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getAuditLog();
        setEntries(data.entries || []);
      } catch (err) {
        console.error('Failed to load audit log:', err);
      }
    };
    load();
    const interval = setInterval(load, 10000); // Auto-refresh every 10s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="animate-in">
      <AuditTable entries={entries} />
    </div>
  );
}

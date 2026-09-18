import { useState, useEffect, useCallback } from 'react';
import AuditTable from '../components/AuditLog/AuditTable';
import { api } from '../api/client';
import { ShieldIcon, RefreshIcon, CheckCircleIcon } from '../components/Common/Icons';

export default function AuditPage() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadAudit = useCallback(async () => {
    try {
      setRefreshing(true);
      const data = await api.getAuditLog(1, 100);
      setEntries(data.entries || []);
    } catch (err) {
      console.error('Failed to load audit log:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadAudit();
    const interval = setInterval(loadAudit, 12000);
    return () => clearInterval(interval);
  }, [loadAudit]);

  const allChainValid = entries.length > 0 && entries.every((e) => e.chain_valid !== false);

  return (
    <div className="audit-page-container animate-in">
      {/* Integrity Banner */}
      <div className="audit-header-banner">
        <div className="audit-banner-left">
          <div className="audit-banner-icon">
            <ShieldIcon size={18} />
          </div>
          <div>
            <div className="audit-banner-title">Cryptographic SHA-256 Security Ledger</div>
            <div className="audit-banner-sub">
              Incremental hash-chained audit log guaranteeing non-repudiation and tamper detection across all pipeline events.
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div className={`audit-integrity-tag ${allChainValid ? '' : 'audit-tag-broken'}`}>
            <CheckCircleIcon size={13} />
            <span>{allChainValid ? 'Hash Chain Verified' : 'Integrity Check Required'}</span>
          </div>

          <button
            type="button"
            className="btn btn-sm btn-ghost"
            onClick={loadAudit}
            disabled={refreshing}
            title="Refresh Ledger"
          >
            <RefreshIcon size={13} className={refreshing ? 'sidebar-pulse-dot' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <AuditTable entries={entries} loading={loading} />
    </div>
  );
}

import { useLocation } from 'react-router-dom';
import { LockIcon, ShieldIcon } from '../Common/Icons';

const pageTitles = {
  '/query': 'Privacy-Preserving Query Engine',
  '/documents': 'Document Management & Ingestion',
  '/graph': 'Knowledge Graph Explorer',
  '/audit': 'Cryptographic Security Ledger',
};

export default function TopBar() {
  const { pathname } = useLocation();
  const currentTitle = pageTitles[pathname] || 'Enterprise Console';

  return (
    <header className="topbar">
      <div className="topbar-breadcrumbs">
        <span className="topbar-breadcrumb-root">PrivaGraph</span>
        <span className="topbar-breadcrumb-sep">/</span>
        <span className="topbar-breadcrumb-current">{currentTitle}</span>
      </div>

      <div className="topbar-status-group">
        <div className="topbar-status-chip">
          <LockIcon size={12} />
          <span>AES-256-GCM Vault</span>
        </div>
        <div className="topbar-status-chip">
          <ShieldIcon size={12} />
          <span>Zero-PII Cloud Boundary</span>
        </div>
      </div>
    </header>
  );
}

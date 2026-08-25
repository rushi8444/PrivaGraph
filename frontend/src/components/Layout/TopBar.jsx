import { useLocation } from 'react-router-dom';

const pageTitles = {
  '/query': 'Privacy-Preserving Query Engine',
  '/documents': 'Document Management',
  '/graph': 'Knowledge Graph Explorer',
  '/audit': 'Security Audit Trail',
};

export default function TopBar() {
  const { pathname } = useLocation();
  return (
    <header className="topbar">
      <span className="topbar-title">{pageTitles[pathname] || 'PrivaGraph'}</span>
      <div className="topbar-actions">
        <div className="topbar-chip">
          <span className="topbar-chip-dot green" />
          Vault Sealed
        </div>
        <div className="topbar-chip">
          <span className="topbar-chip-dot blue" />
          RBAC Active
        </div>
      </div>
    </header>
  );
}

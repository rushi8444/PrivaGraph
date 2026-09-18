import { NavLink } from 'react-router-dom';
import {
  ShieldIcon,
  ChatIcon,
  FileTextIcon,
  NetworkIcon,
  AuditIcon,
  LockIcon,
} from '../Common/Icons';

const navItems = [
  { to: '/query', icon: ChatIcon, label: 'Query Engine' },
  { to: '/documents', icon: FileTextIcon, label: 'Documents' },
  { to: '/graph', icon: NetworkIcon, label: 'Knowledge Graph' },
  { to: '/audit', icon: AuditIcon, label: 'Security Ledger' },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon-wrap">
            <ShieldIcon size={18} />
          </div>
          <div className="sidebar-brand-text">
            <span className="sidebar-brand-name">PrivaGraph</span>
            <span className="sidebar-brand-tag">Enterprise Gateway</span>
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="sidebar-nav-heading">Platform</div>
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
          >
            <span className="sidebar-link-icon">
              <Icon size={16} />
            </span>
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-security-badge">
          <div className="sidebar-status-left">
            <span className="sidebar-pulse-dot" />
            <span>Vault Sealed</span>
          </div>
          <LockIcon size={13} style={{ color: 'var(--status-verified)' }} />
        </div>
        <div className="sidebar-security-badge" style={{ marginTop: '2px' }}>
          <div className="sidebar-status-left">
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Core Pipeline</span>
          </div>
          <span className="sidebar-version-pill">v1.0-prod</span>
        </div>
      </div>
    </aside>
  );
}

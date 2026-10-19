import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  ShieldIcon,
  ChatIcon,
  FileTextIcon,
  AuditIcon,
  LockIcon,
  LogOutIcon,
  UserIcon,
} from '../Common/Icons';

const navItems = [
  { to: '/query', icon: ChatIcon, label: 'Query Engine' },
  { to: '/documents', icon: FileTextIcon, label: 'Documents' },
  { to: '/audit', icon: AuditIcon, label: 'Security Ledger' },
];

export default function Sidebar() {
  const { user, logout } = useAuth();

  const getInitials = (name) => {
    if (!name) return 'U';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };

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
        {/* User Account / Profile Card */}
        {user && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '8px 10px',
              marginBottom: '10px',
              borderRadius: '8px',
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
              <div
                style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  color: '#fff',
                  flexShrink: 0,
                }}
              >
                {getInitials(user.username)}
              </div>
              <div style={{ overflow: 'hidden' }}>
                <div
                  style={{
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                  title={user.username}
                >
                  {user.username}
                </div>
                <div
                  style={{
                    fontSize: '0.68rem',
                    color: 'var(--text-muted)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                  title={user.email}
                >
                  {user.email}
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={logout}
              className="btn btn-ghost btn-sm"
              style={{
                padding: '4px',
                borderRadius: '6px',
                color: 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
              }}
              title="Sign Out"
            >
              <LogOutIcon size={14} />
            </button>
          </div>
        )}

        <div className="sidebar-security-badge">
          <div className="sidebar-status-left">
            <span className="sidebar-pulse-dot" />
            <span>Vault Sealed</span>
          </div>
          <LockIcon size={13} style={{ color: 'var(--status-verified)' }} />
        </div>
        <div className="sidebar-security-badge" style={{ marginTop: '2px' }}>
          <div className="sidebar-status-left">
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>PostgreSQL Session</span>
          </div>
          <span className="sidebar-version-pill">v1.0-prod</span>
        </div>
      </div>
    </aside>
  );
}

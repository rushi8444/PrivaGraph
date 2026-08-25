import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/query',     icon: '💬', label: 'Query Chat' },
  { to: '/documents', icon: '📄', label: 'Documents' },
  { to: '/graph',     icon: '🕸️', label: 'Knowledge Graph' },
  { to: '/audit',     icon: '📋', label: 'Audit Log' },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">🛡️</div>
        <span className="sidebar-brand-name">PrivaGraph</span>
      </div>
      <nav className="sidebar-nav">
        {navItems.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
          >
            <span className="sidebar-link-icon">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">
        <div className="sidebar-status">
          <span className="status-dot" />
          Pipeline Active
        </div>
      </div>
    </aside>
  );
}

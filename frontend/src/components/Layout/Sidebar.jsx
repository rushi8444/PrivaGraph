import { useState, useRef, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useChat } from '../../context/ChatContext';
import {
  ShieldIcon,
  SidebarToggleIcon,
  PencilSquareIcon,
  LibraryIcon,
  SearchIcon,
  ChatIcon,
  EditIcon,
  TrashIcon,
  CheckIcon,
  LogOutIcon,
  MoreHorizontalIcon,
} from '../Common/Icons';

function groupConversationsByDate(conversations) {
  const groups = {
    Today: [],
    Yesterday: [],
    'Previous 7 Days': [],
    Older: [],
  };

  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const yesterdayStart = todayStart - 86400000;
  const sevenDaysAgo = todayStart - 6 * 86400000;

  for (const conv of conversations) {
    const rawDate = conv.updated_at || conv.created_at;
    const date = rawDate ? new Date(rawDate).getTime() : 0;
    if (date >= todayStart) {
      groups.Today.push(conv);
    } else if (date >= yesterdayStart) {
      groups.Yesterday.push(conv);
    } else if (date >= sevenDaysAgo) {
      groups['Previous 7 Days'].push(conv);
    } else {
      groups.Older.push(conv);
    }
  }

  return groups;
}

export default function Sidebar() {
  const { user, logout } = useAuth();
  const {
    conversations,
    activeConversationId,
    historyLoading,
    isSidebarCollapsed,
    toggleSidebar,
    handleNewChat,
    handleSelectConversation,
    handleRenameConversation,
    handleDeleteConversation,
  } = useChat();

  const location = useLocation();
  const isQueryPage = location.pathname === '/query';

  // Search filter & inline rename state
  const [showSearch, setShowSearch] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [renamingId, setRenamingId] = useState(null);
  const [renameTitle, setRenameTitle] = useState('');
  const [openMenuId, setOpenMenuId] = useState(null);
  const searchInputRef = useRef(null);

  // Close 3-dots dropdown menu when clicking anywhere outside
  useEffect(() => {
    const handleOutsideClick = () => setOpenMenuId(null);
    if (openMenuId) {
      window.addEventListener('click', handleOutsideClick);
      return () => window.removeEventListener('click', handleOutsideClick);
    }
  }, [openMenuId]);

  const getInitials = (name) => {
    if (!name) return 'U';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };

  const toggleSearch = () => {
    setShowSearch((prev) => {
      const next = !prev;
      if (next) {
        setTimeout(() => searchInputRef.current?.focus(), 50);
      } else {
        setSearchTerm('');
      }
      return next;
    });
  };

  const startRename = (conv, e) => {
    e.stopPropagation();
    setRenamingId(conv.id);
    setRenameTitle(conv.title);
  };

  const saveRename = (convId, e) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    if (renameTitle.trim()) {
      handleRenameConversation(convId, renameTitle.trim());
    }
    setRenamingId(null);
  };

  // Filter conversations if searching
  const filteredConversations = searchTerm.trim()
    ? conversations.filter((c) =>
        c.title.toLowerCase().includes(searchTerm.toLowerCase().trim())
      )
    : conversations;

  const grouped = groupConversationsByDate(filteredConversations);

  /* =========================================================================
     COLLAPSED STATE (ChatGPT / Claude Slim Rail)
     ========================================================================= */
  if (isSidebarCollapsed) {
    return (
      <aside className="sidebar collapsed">
        <div className="sidebar-collapsed-rail">
          {/* Top Rail Navigation Icons */}
          <div className="sidebar-rail-top">
            {/* Unhide / Toggle Sidebar Button */}
            <button
              type="button"
              className="sidebar-rail-btn"
              onClick={toggleSidebar}
              title="Open sidebar"
            >
              <SidebarToggleIcon size={19} />
            </button>

            {/* New Chat Button */}
            <button
              type="button"
              className="sidebar-rail-btn"
              onClick={handleNewChat}
              title="New chat"
            >
              <PencilSquareIcon size={18} />
            </button>

            {/* Search Chats (expands and opens search) */}
            <button
              type="button"
              className="sidebar-rail-btn"
              onClick={() => {
                toggleSidebar();
                setShowSearch(true);
                setTimeout(() => searchInputRef.current?.focus(), 150);
              }}
              title="Search chats"
            >
              <SearchIcon size={18} />
            </button>

            {/* Recent Chats (expands sidebar) */}
            <button
              type="button"
              className="sidebar-rail-btn"
              onClick={toggleSidebar}
              title="Recents"
            >
              <ChatIcon size={17} />
            </button>

            {/* Documents / Library Navigation */}
            <NavLink
              to="/documents"
              className={({ isActive }) => `sidebar-rail-btn ${isActive ? 'active' : ''}`}
              title="Documents"
            >
              <LibraryIcon size={18} />
            </NavLink>
          </div>

          {/* Bottom Rail User Profile Avatar */}
          <div className="sidebar-rail-bottom">
            <div
              className="sidebar-rail-avatar"
              onClick={logout}
              title={`${user?.username || 'User'} (Click to sign out)`}
            >
              {getInitials(user?.username)}
            </div>
          </div>
        </div>
      </aside>
    );
  }

  /* =========================================================================
     EXPANDED STATE (Clean ChatGPT / Claude Design)
     ========================================================================= */
  return (
    <aside className="sidebar">
      {/* Clean Brand Header with Search & Toggle Actions */}
      <div className="sidebar-header-clean">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '24px',
              height: '24px',
              borderRadius: '6px',
              background: 'rgba(52, 211, 153, 0.1)',
              border: '1px solid rgba(52, 211, 153, 0.25)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--status-verified)',
            }}
          >
            <ShieldIcon size={14} />
          </div>
          <span
            style={{
              fontSize: '0.95rem',
              fontWeight: 650,
              color: 'var(--text-primary)',
              letterSpacing: '-0.02em',
            }}
          >
            PrivaGraph
          </span>
        </div>

        <div className="sidebar-header-actions">
          <button
            type="button"
            className={`sidebar-icon-btn ${showSearch ? 'active' : ''}`}
            onClick={toggleSearch}
            title={showSearch ? 'Close search' : 'Search chats'}
          >
            <SearchIcon size={16} />
          </button>
          <button
            type="button"
            className="sidebar-icon-btn"
            onClick={toggleSidebar}
            title="Close sidebar"
          >
            <SidebarToggleIcon size={18} />
          </button>
        </div>
      </div>

      {/* Inline Search Bar (Visible when search icon is clicked) */}
      {showSearch && (
        <div className="sidebar-search-box">
          <input
            ref={searchInputRef}
            type="text"
            className="sidebar-search-input"
            placeholder="Search conversations..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      )}

      {/* Primary Action: New Chat */}
      <div>
        <button
          type="button"
          className="sidebar-new-btn"
          onClick={handleNewChat}
          title="New chat"
        >
          <PencilSquareIcon size={17} style={{ color: 'var(--text-secondary)' }} />
          <span>New chat</span>
        </button>
      </div>

      {/* Navigation: Documents */}
      <nav className="sidebar-nav" style={{ flex: 'none' }}>
        <NavLink to="/how-it-works" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
          <span className="sidebar-link-icon"><ShieldIcon size={17} /></span>
          <span>How it works</span>
        </NavLink>
        <NavLink
          to="/documents"
          className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
        >
          <span className="sidebar-link-icon">
            <LibraryIcon size={17} />
          </span>
          <span>Documents</span>
        </NavLink>
      </nav>

      {/* Recents Section (ChatGPT Style) */}
      <div className="sidebar-chats-container">
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '4px 8px 2px',
            fontSize: '0.72rem',
            fontWeight: 600,
            color: 'var(--text-dim)',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            fontFamily: 'var(--font-mono)',
          }}
        >
          <span>Recents</span>
          {conversations.length > 0 && (
            <span style={{ fontSize: '0.65rem', opacity: 0.7 }}>
              {filteredConversations.length}
            </span>
          )}
        </div>

        {filteredConversations.length === 0 ? (
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', padding: '6px 8px' }}>
            {historyLoading
              ? 'Loading history...'
              : searchTerm
              ? 'No matching chats found.'
              : 'No previous chats.'}
          </div>
        ) : (
          Object.entries(grouped).map(([groupName, items]) => {
            if (items.length === 0) return null;
            return (
              <div key={groupName} className="sidebar-chats-group">
                <div className="sidebar-chats-group-title">{groupName}</div>
                {items.map((conv) => {
                  const isActive = isQueryPage && conv.id === activeConversationId;
                  const isRenaming = conv.id === renamingId;

                  return (
                    <div
                      key={conv.id}
                      className={`sidebar-chat-item ${isActive ? 'active' : ''}`}
                      onClick={() => handleSelectConversation(conv.id)}
                      title={conv.title}
                    >
                      {isRenaming ? (
                        <form
                          className="sidebar-chat-rename-form"
                          onSubmit={(e) => saveRename(conv.id, e)}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <input
                            type="text"
                            autoFocus
                            className="sidebar-chat-rename-input"
                            value={renameTitle}
                            onChange={(e) => setRenameTitle(e.target.value)}
                            onBlur={(e) => saveRename(conv.id, e)}
                            onKeyDown={(e) => {
                              if (e.key === 'Escape') setRenamingId(null);
                            }}
                          />
                          <button type="submit" className="chat-item-action-btn" title="Save">
                            <CheckIcon size={12} style={{ color: 'var(--status-verified)' }} />
                          </button>
                        </form>
                      ) : (
                        <>
                          <div className="sidebar-chat-item-content">
                            <span className="sidebar-chat-item-title">{conv.title}</span>
                          </div>
                          <div
                            className={`sidebar-chat-item-actions ${conv.id === openMenuId ? 'open' : ''}`}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <button
                              type="button"
                              className={`sidebar-chat-menu-btn ${conv.id === openMenuId ? 'open' : ''}`}
                              onClick={(e) => {
                                e.stopPropagation();
                                setOpenMenuId((prev) => (prev === conv.id ? null : conv.id));
                              }}
                              title="Chat options"
                            >
                              <MoreHorizontalIcon size={16} />
                            </button>

                            {conv.id === openMenuId && (
                              <div className="sidebar-chat-dropdown" onClick={(e) => e.stopPropagation()}>
                                <button
                                  type="button"
                                  className="sidebar-chat-dropdown-item"
                                  onClick={(e) => {
                                    setOpenMenuId(null);
                                    startRename(conv, e);
                                  }}
                                >
                                  <EditIcon size={13} />
                                  <span>Rename</span>
                                </button>
                                <button
                                  type="button"
                                  className="sidebar-chat-dropdown-item delete"
                                  onClick={(e) => {
                                    setOpenMenuId(null);
                                    handleDeleteConversation(conv.id, e);
                                  }}
                                >
                                  <TrashIcon size={13} />
                                  <span>Delete</span>
                                </button>
                              </div>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })
        )}
      </div>

      {/* User Profile Card (ChatGPT Style) */}
      <div className="sidebar-footer" style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
        {user && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '6px 8px',
              borderRadius: '8px',
              transition: 'background 0.15s ease',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #2d3748 0%, #1e293b 100%)',
                  border: '1px solid var(--border-default)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  color: '#ffffff',
                  flexShrink: 0,
                }}
              >
                {getInitials(user.username)}
              </div>
              <div style={{ overflow: 'hidden' }}>
                <div
                  style={{
                    fontSize: '0.825rem',
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
                    fontSize: '0.7rem',
                    color: 'var(--text-muted)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  Enterprise Vault
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={logout}
              className="btn btn-ghost btn-sm"
              style={{
                padding: '5px',
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
      </div>
    </aside>
  );
}

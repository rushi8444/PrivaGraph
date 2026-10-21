import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { api } from '../api/client';

const ChatContext = createContext(null);

export function ChatProvider({ children }) {
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [attachedDocuments, setAttachedDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    return localStorage.getItem('privagraph_sidebar_collapsed') === 'true';
  });

  const toggleSidebar = () => {
    setIsSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('privagraph_sidebar_collapsed', String(next));
      return next;
    });
  };

  const navigate = useNavigate();
  const location = useLocation();
  const textareaRef = useRef(null);

  // Load all user conversations
  const fetchConversations = useCallback(async () => {
    try {
      setHistoryLoading(true);
      const list = await api.listConversations();
      setConversations(Array.isArray(list) ? list : []);
    } catch (err) {
      console.warn('Could not load conversations:', err);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  // Select a conversation from sidebar
  const handleSelectConversation = async (convId) => {
    if (convId === activeConversationId && location.pathname === '/query') return;
    setErrorMessage(null);
    setActiveConversationId(convId);
    setLoading(true);

    if (location.pathname !== '/query') {
      navigate('/query');
    }

    try {
      const detail = await api.getConversation(convId);
      setMessages(detail.messages || []);
      setAttachedDocuments(detail.documents || []);
    } catch (err) {
      setErrorMessage(`Failed to load conversation: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Start a fresh chat
  const handleNewChat = () => {
    if (loading) return;
    setActiveConversationId(null);
    setMessages([]);
    setAttachedDocuments([]);
    setErrorMessage(null);

    if (location.pathname !== '/query') {
      navigate('/query');
    }

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.focus();
    }
  };

  // Ensure active conversation exists
  const ensureActiveConversation = async (suggestedTitle = 'New Chat') => {
    if (activeConversationId) return activeConversationId;
    const conv = await api.createConversation(suggestedTitle);
    setActiveConversationId(conv.id);
    await fetchConversations();
    return conv.id;
  };

  // Attach a document to active conversation
  const handleAttachDocument = async (docId) => {
    try {
      const convId = await ensureActiveConversation();
      const updated = await api.attachDocumentToConversation(convId, docId);
      setAttachedDocuments(updated);
    } catch (err) {
      setErrorMessage(`Failed to attach document: ${err.message}`);
    }
  };

  // Detach a document from active conversation
  const handleDetachDocument = async (docId, e) => {
    if (e) e.stopPropagation();
    if (!activeConversationId) {
      setAttachedDocuments((prev) => prev.filter((d) => d.doc_id !== docId));
      return;
    }
    try {
      const updated = await api.detachDocumentFromConversation(activeConversationId, docId);
      setAttachedDocuments(updated);
    } catch (err) {
      setErrorMessage(`Failed to detach document: ${err.message}`);
    }
  };

  // Direct file upload into active conversation
  const handleDirectFileUpload = async (file) => {
    if (!file) return;
    setLoading(true);
    setErrorMessage(null);

    try {
      const fileStem = file.name.replace(/\.[^/.]+$/, '');
      const convId = await ensureActiveConversation(fileStem);

      const formData = new FormData();
      formData.append('file', file);
      formData.append('conversation_id', convId);

      await api.ingestDocument(formData);
      const docs = await api.getConversationDocuments(convId);
      setAttachedDocuments(docs);
      await fetchConversations();
    } catch (err) {
      setErrorMessage(`Document upload failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Rename a conversation
  const handleRenameConversation = async (convId, newTitle) => {
    const trimmed = (newTitle || '').trim();
    if (!trimmed) return;

    try {
      await api.renameConversation(convId, trimmed);
      setConversations((prev) =>
        prev.map((c) => (c.id === convId ? { ...c, title: trimmed } : c))
      );
    } catch (err) {
      setErrorMessage(`Failed to rename conversation: ${err.message}`);
    }
  };

  // Delete a conversation
  const handleDeleteConversation = async (convId, e) => {
    if (e) e.stopPropagation();
    if (!window.confirm('Delete this chat session permanently?')) return;

    try {
      await api.deleteConversation(convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (activeConversationId === convId) {
        handleNewChat();
      }
    } catch (err) {
      setErrorMessage(`Failed to delete conversation: ${err.message}`);
    }
  };

  // Submit query
  const handleSendQuery = async (queryText) => {
    const query = (queryText || '').trim();
    if (!query || loading) return;

    setErrorMessage(null);
    const userMsg = { id: Date.now(), role: 'user', content: query };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    try {
      const data = await api.submitQuery(query, undefined, activeConversationId);
      const assistantMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.answer,
        metadata: data.metadata,
        graphContext: data.graph_context,
        citations: data.citations || [],
        zeroPiiProof: data.zero_pii_proof || null,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      if (!activeConversationId && data.conversation_id) {
        setActiveConversationId(data.conversation_id);
      }
      fetchConversations();
    } catch (err) {
      setErrorMessage(err.message);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: `Query failed: ${err.message}`,
          metadata: { model_used: 'error-handler', entities_reconstructed: 0 },
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const value = {
    conversations,
    activeConversationId,
    messages,
    attachedDocuments,
    loading,
    historyLoading,
    errorMessage,
    setErrorMessage,
    isSidebarCollapsed,
    toggleSidebar,
    textareaRef,
    fetchConversations,
    handleSelectConversation,
    handleNewChat,
    handleAttachDocument,
    handleDetachDocument,
    handleDirectFileUpload,
    handleRenameConversation,
    handleDeleteConversation,
    handleSendQuery,
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChat() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
}

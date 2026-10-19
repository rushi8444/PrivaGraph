import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ChatProvider, useChat } from './context/ChatContext';
import ProtectedRoute from './components/Auth/ProtectedRoute';
import Sidebar from './components/Layout/Sidebar';
import TopBar from './components/Layout/TopBar';
import DocumentsPage from './pages/DocumentsPage';
import QueryPage from './pages/QueryPage';
import AuditPage from './pages/AuditPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';

function AuthenticatedContent() {
  const { isSidebarCollapsed } = useChat();
  return (
    <div className={`app-layout ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      <Sidebar />
      <TopBar />
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}

function AuthenticatedLayout() {
  return (
    <ChatProvider>
      <AuthenticatedContent />
    </ChatProvider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Auth Routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected Application Routes */}
          <Route
            element={
              <ProtectedRoute>
                <AuthenticatedLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<Navigate to="/query" replace />} />
            <Route path="/query" element={<QueryPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/audit" element={<AuditPage />} />
            <Route path="/graph" element={<Navigate to="/query" replace />} />
            <Route path="*" element={<Navigate to="/query" replace />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

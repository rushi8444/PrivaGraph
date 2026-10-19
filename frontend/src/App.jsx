import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/Auth/ProtectedRoute';
import Sidebar from './components/Layout/Sidebar';
import TopBar from './components/Layout/TopBar';
import DocumentsPage from './pages/DocumentsPage';
import QueryPage from './pages/QueryPage';
import AuditPage from './pages/AuditPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';

function AuthenticatedLayout({ children }) {
  return (
    <div className="app-layout">
      <Sidebar />
      <TopBar />
      <main className="app-main">{children}</main>
    </div>
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
            path="/*"
            element={
              <ProtectedRoute>
                <AuthenticatedLayout>
                  <Routes>
                    <Route path="/" element={<Navigate to="/query" replace />} />
                    <Route path="/documents" element={<DocumentsPage />} />
                    <Route path="/query" element={<QueryPage />} />
                    <Route path="/graph" element={<Navigate to="/query" replace />} />
                    <Route path="/audit" element={<AuditPage />} />
                    <Route path="*" element={<Navigate to="/query" replace />} />
                  </Routes>
                </AuthenticatedLayout>
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

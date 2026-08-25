import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Layout/Sidebar';
import TopBar from './components/Layout/TopBar';
import DocumentsPage from './pages/DocumentsPage';
import QueryPage from './pages/QueryPage';
import GraphPage from './pages/GraphPage';
import AuditPage from './pages/AuditPage';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <TopBar />
        <main className="app-main">
          <Routes>
            <Route path="/" element={<Navigate to="/query" replace />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/query" element={<QueryPage />} />
            <Route path="/graph" element={<GraphPage />} />
            <Route path="/audit" element={<AuditPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

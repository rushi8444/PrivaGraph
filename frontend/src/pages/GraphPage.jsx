import { useState, useEffect } from 'react';
import GraphCanvas from '../components/Graph/GraphCanvas';
import { api } from '../api/client';
import { NetworkIcon } from '../components/Common/Icons';

export default function GraphPage() {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const data = await api.getGraphNodes();
        setNodes(data.nodes || []);
        setEdges(data.edges || []);
      } catch (err) {
        console.error('Failed to load graph:', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <div className="graph-explorer-wrapper" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
          <span className="sidebar-pulse-dot" />
          <span>Computing graph topology & force simulation...</span>
        </div>
      </div>
    );
  }

  if (!nodes.length) {
    return (
      <div className="graph-explorer-wrapper" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: 'var(--radius-md)', background: 'var(--bg-card)', border: '1px solid var(--border-default)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
            <NetworkIcon size={24} />
          </div>
          <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            No Knowledge Graph Nodes Extracted
          </div>
          <p style={{ fontSize: '0.8rem', maxWidth: '360px', color: 'var(--text-muted)' }}>
            Ingest enterprise documents via the Documents tab to extract SVO triples and visualize multi-document relationships.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-in">
      <GraphCanvas nodes={nodes} edges={edges} />
    </div>
  );
}

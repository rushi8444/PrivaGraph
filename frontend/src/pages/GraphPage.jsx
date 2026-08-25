import { useState, useEffect } from 'react';
import GraphCanvas from '../components/Graph/GraphCanvas';
import { api } from '../api/client';

export default function GraphPage() {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getGraphNodes();
        setNodes(data.nodes || []);
        setEdges(data.edges || []);
      } catch (err) {
        console.error('Failed to load graph:', err);
      }
    };
    load();
  }, []);

  if (!nodes.length) {
    return (
      <div className="graph-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
          <div style={{ fontSize: '3rem', opacity: 0.4, marginBottom: '1rem' }}>🕸️</div>
          <p>No graph data yet. Ingest documents to build the knowledge graph.</p>
        </div>
      </div>
    );
  }

  return <GraphCanvas nodes={nodes} edges={edges} />;
}

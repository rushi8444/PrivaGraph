export default function NodeTooltip({ x, y, node }) {
  const docCount = node.doc_ids?.length || 0;

  return (
    <div
      className="node-tooltip-card"
      style={{
        left: Math.min(x + 14, window.innerWidth - 240),
        top: Math.max(y - 20, 70),
      }}
    >
      <div className="node-tooltip-title">{node.label || node.id}</div>

      <div className="node-tooltip-field">
        <span className="node-tooltip-field-name">Entity Type:</span>
        <span className="node-tooltip-field-val">{node.entity_type || 'STANDARD'}</span>
      </div>

      <div className="node-tooltip-field">
        <span className="node-tooltip-field-name">Namespace:</span>
        <span className="node-tooltip-field-val">{node.namespace || 'global'}</span>
      </div>

      <div className="node-tooltip-field">
        <span className="node-tooltip-field-name">Classification:</span>
        <span className="node-tooltip-field-val" style={{ textTransform: 'uppercase' }}>
          {node.classification || 'INTERNAL'}
        </span>
      </div>

      {docCount > 0 && (
        <div className="node-tooltip-field">
          <span className="node-tooltip-field-name">Linked Documents:</span>
          <span className="node-tooltip-field-val">{docCount} source{docCount > 1 ? 's' : ''}</span>
        </div>
      )}
    </div>
  );
}

export default function NodeTooltip({ x, y, node }) {
  return (
    <div className="node-tooltip" style={{ left: x + 12, top: y - 12 }}>
      <div className="node-tooltip-id">{node.id}</div>
      <div className="node-tooltip-row">
        <span className="node-tooltip-label">Type</span>
        <span>{node.entity_type || 'unknown'}</span>
      </div>
      <div className="node-tooltip-row">
        <span className="node-tooltip-label">Namespace</span>
        <span>{node.namespace}</span>
      </div>
      <div className="node-tooltip-row">
        <span className="node-tooltip-label">Classification</span>
        <span>{node.classification}</span>
      </div>
    </div>
  );
}

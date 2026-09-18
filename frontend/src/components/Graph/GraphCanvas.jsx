import { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';
import NodeTooltip from './NodeTooltip';
import {
  ZoomInIcon,
  ZoomOutIcon,
  ResetIcon,
  NetworkIcon,
} from '../Common/Icons';

// Natural Earth & Mineral Palette (Non-AI-slop)
const NODE_COLORS = {
  PERSON: '#4a678f',      // Muted Slate Navy
  SALARY: '#356b4f',      // Restrained Moss Green
  SSN: '#873934',         // Muted Terracotta / Rust
  EMAIL: '#2c6270',       // Muted Petrol Teal
  PHONE: '#7e5d2c',       // Warm Sand Amber
  DEPARTMENT: '#7d4834',  // Earthy Clay
  PROJECT_CODE: '#5c527f',// Muted Slate Plum
  DEFAULT: '#475569',     // Charcoal Neutral
};

const LEGEND_ITEMS = [
  { label: 'PERSON', color: '#4a678f' },
  { label: 'SALARY', color: '#356b4f' },
  { label: 'SSN / ID', color: '#873934' },
  { label: 'CONTACT', color: '#2c6270' },
  { label: 'STRUCTURAL', color: '#475569' },
];

export default function GraphCanvas({ nodes, edges }) {
  const svgRef = useRef(null);
  const zoomBehaviorRef = useRef(null);
  const [tooltip, setTooltip] = useState(null);

  const handleZoomIn = useCallback(() => {
    if (!svgRef.current || !zoomBehaviorRef.current) return;
    d3.select(svgRef.current).transition().duration(250).call(zoomBehaviorRef.current.scaleBy, 1.3);
  }, []);

  const handleZoomOut = useCallback(() => {
    if (!svgRef.current || !zoomBehaviorRef.current) return;
    d3.select(svgRef.current).transition().duration(250).call(zoomBehaviorRef.current.scaleBy, 0.75);
  }, []);

  const handleResetZoom = useCallback(() => {
    if (!svgRef.current || !zoomBehaviorRef.current) return;
    d3.select(svgRef.current).transition().duration(350).call(
      zoomBehaviorRef.current.transform,
      d3.zoomIdentity
    );
  }, []);

  useEffect(() => {
    if (!nodes?.length || !svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    const g = svg.append('g');

    const zoom = d3.zoom()
      .scaleExtent([0.2, 5])
      .on('zoom', (event) => g.attr('transform', event.transform));

    zoomBehaviorRef.current = zoom;
    svg.call(zoom);

    // Arrowhead marker definition
    svg.append('defs').append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 18)
      .attr('refY', 0)
      .attr('markerWidth', 5)
      .attr('markerHeight', 5)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#475569');

    const nodesCopy = nodes.map((d) => ({ ...d }));
    const edgesCopy = edges.map((d) => ({ ...d }));

    const simulation = d3.forceSimulation(nodesCopy)
      .force('link', d3.forceLink(edgesCopy).id((d) => d.id).distance(110))
      .force('charge', d3.forceManyBody().strength(-240))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide(26));

    const link = g.selectAll('.graph-link')
      .data(edgesCopy).join('line')
      .attr('stroke', '#334155')
      .attr('stroke-width', 1.2)
      .attr('stroke-opacity', 0.5)
      .attr('marker-end', 'url(#arrowhead)');

    const linkLabel = g.selectAll('.graph-link-label')
      .data(edgesCopy).join('text')
      .attr('fill', '#64748b')
      .attr('font-size', '8px')
      .attr('font-family', 'var(--font-mono)')
      .attr('text-anchor', 'middle')
      .attr('pointer-events', 'none')
      .text((d) => d.predicate);

    const node = g.selectAll('.graph-node')
      .data(nodesCopy).join('g')
      .attr('class', 'graph-node')
      .call(d3.drag()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
      );

    node.append('circle')
      .attr('r', 7)
      .attr('fill', (d) => NODE_COLORS[d.entity_type] || NODE_COLORS.DEFAULT)
      .attr('stroke', '#0d1015')
      .attr('stroke-width', 1.5)
      .style('cursor', 'grab')
      .on('mouseover', (event, d) => {
        setTooltip({ x: event.clientX, y: event.clientY, node: d });
      })
      .on('mouseout', () => setTooltip(null));

    node.append('text')
      .attr('dx', 11)
      .attr('dy', 3.5)
      .attr('fill', '#94a3b8')
      .attr('font-size', '9px')
      .attr('font-family', 'var(--font-mono)')
      .attr('pointer-events', 'none')
      .text((d) => d.label || d.id);

    simulation.on('tick', () => {
      link
        .attr('x1', (d) => d.source.x).attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x).attr('y2', (d) => d.target.y);

      linkLabel
        .attr('x', (d) => (d.source.x + d.target.x) / 2)
        .attr('y', (d) => (d.source.y + d.target.y) / 2);

      node.attr('transform', (d) => `translate(${d.x},${d.y})`);
    });

    return () => simulation.stop();
  }, [nodes, edges]);

  return (
    <div className="graph-explorer-wrapper">
      <svg ref={svgRef} style={{ width: '100%', height: '100%' }} />

      {/* Top Info Toolbar */}
      <div className="graph-top-toolbar">
        <div className="graph-pill-badge">
          <NetworkIcon size={12} />
          <span>{nodes.length} Nodes</span>
        </div>
        <div className="graph-pill-badge">
          <span>{edges.length} Directed Relationships</span>
        </div>
      </div>

      {/* Floating Controls Dock */}
      <div className="graph-controls-dock">
        <button
          type="button"
          className="graph-dock-btn"
          title="Zoom In"
          onClick={handleZoomIn}
        >
          <ZoomInIcon size={14} />
        </button>
        <button
          type="button"
          className="graph-dock-btn"
          title="Zoom Out"
          onClick={handleZoomOut}
        >
          <ZoomOutIcon size={14} />
        </button>
        <button
          type="button"
          className="graph-dock-btn"
          title="Reset View"
          onClick={handleResetZoom}
        >
          <ResetIcon size={13} />
        </button>
      </div>

      {/* Graph Legend Overlay */}
      <div className="graph-legend-overlay">
        {LEGEND_ITEMS.map((item) => (
          <div key={item.label} className="graph-legend-item">
            <span className="graph-legend-color-dot" style={{ backgroundColor: item.color }} />
            <span>{item.label}</span>
          </div>
        ))}
      </div>

      {tooltip && <NodeTooltip {...tooltip} />}
    </div>
  );
}

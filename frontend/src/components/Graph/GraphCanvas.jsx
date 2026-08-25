import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import NodeTooltip from './NodeTooltip';

const NODE_COLORS = {
  PERSON: '#6366f1',
  SALARY: '#10b981',
  SSN: '#ef4444',
  EMAIL: '#06b6d4',
  PHONE: '#f59e0b',
  PROJECT_CODE: '#8b5cf6',
  DEFAULT: '#64748b',
};

export default function GraphCanvas({ nodes, edges }) {
  const svgRef = useRef(null);
  const [tooltip, setTooltip] = useState(null);

  useEffect(() => {
    if (!nodes?.length || !svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    const g = svg.append('g');
    svg.call(
      d3.zoom()
        .scaleExtent([0.3, 4])
        .on('zoom', (event) => g.attr('transform', event.transform))
    );

    svg.append('defs').append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20).attr('refY', 0)
      .attr('markerWidth', 6).attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#64748b');

    const nodesCopy = nodes.map((d) => ({ ...d }));
    const edgesCopy = edges.map((d) => ({ ...d }));

    const simulation = d3.forceSimulation(nodesCopy)
      .force('link', d3.forceLink(edgesCopy).id((d) => d.id).distance(120))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide(30));

    const link = g.selectAll('.graph-link')
      .data(edgesCopy).join('line')
      .attr('stroke', '#475569').attr('stroke-width', 1.5)
      .attr('stroke-opacity', 0.4)
      .attr('marker-end', 'url(#arrowhead)');

    const linkLabel = g.selectAll('.graph-link-label')
      .data(edgesCopy).join('text')
      .attr('class', 'graph-link-label')
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
      .attr('r', 8)
      .attr('fill', (d) => NODE_COLORS[d.entity_type] || NODE_COLORS.DEFAULT)
      .attr('stroke', (d) => {
        const base = NODE_COLORS[d.entity_type] || NODE_COLORS.DEFAULT;
        return d3.color(base)?.brighter(0.6)?.toString() || base;
      })
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .on('mouseover', (event, d) => {
        setTooltip({ x: event.pageX, y: event.pageY, node: d });
      })
      .on('mouseout', () => setTooltip(null));

    node.append('text').attr('dx', 14).attr('dy', 4).text((d) => d.label || d.id);

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
    <div className="graph-container">
      <svg ref={svgRef} />
      <div className="graph-stats-overlay">
        <span className="graph-stat-chip">🔵 {nodes?.length || 0} nodes</span>
        <span className="graph-stat-chip">➡️ {edges?.length || 0} edges</span>
      </div>
      {tooltip && <NodeTooltip {...tooltip} />}
    </div>
  );
}

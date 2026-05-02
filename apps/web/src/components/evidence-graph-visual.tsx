"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

type GraphNode = {
  id: string;
  label: string;
  type: string;
  source: string;
};

type GraphEdge = {
  id: string;
  source: string;
  target: string;
  relationship: string;
  evidence: string;
  sourceType: string;
};

type EvidenceGraphVisualProps = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

const nodeColors: Record<string, string> = {
  provider: "#b3261e",
  procedure: "#1a73e8",
  organization: "#e8710a",
  document: "#6b7280",
  reference: "#0d9488",
  claim: "#7c3aed",
  billing_company: "#e8710a",
  entity: "#6b7280",
};

const graphHeight = 420;

export function EvidenceGraphVisual({ nodes, edges }: EvidenceGraphVisualProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 500, height: graphHeight });

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const setWidth = (width: number) => {
      setDimensions({ width: Math.max(Math.round(width), 300), height: graphHeight });
    };

    setWidth(element.offsetWidth);
    if (typeof ResizeObserver === "undefined") return;

    const observer = new ResizeObserver(([entry]) => {
      setWidth(entry?.contentRect.width ?? element.offsetWidth);
    });
    observer.observe(element);

    return () => observer.disconnect();
  }, []);

  const graphData = useMemo(() => {
    const graphNodes = nodes.map((n) => ({
      id: n.id,
      label: n.label,
      nodeType: n.type,
      nodeSource: n.source,
    }));
    const nodeIds = new Set(nodes.map((n) => n.id));
    const links = edges
      .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
      .map((e) => ({
        source: e.source,
        target: e.target,
        relationship: e.relationship,
      }));
    return { nodes: graphNodes, links };
  }, [nodes, edges]);

  if (nodes.length === 0) return null;

  return (
    <div ref={containerRef} className="graph-visual-container">
      <ForceGraph2D
        graphData={graphData}
        width={dimensions.width}
        height={dimensions.height}
        backgroundColor="transparent"
        nodeLabel="label"
        nodeColor={(node: Record<string, unknown>) =>
          nodeColors[(node.nodeType as string) ?? ""] ?? "#6b7280"
        }
        nodeRelSize={6}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        linkLabel="relationship"
        linkColor={() => "#94a3b8"}
        nodeCanvasObjectMode={() => "after" as const}
        nodeCanvasObject={(node: Record<string, unknown>, ctx: CanvasRenderingContext2D, globalScale: number) => {
          const label = (node.label as string) ?? "";
          const fontSize = Math.max(10 / globalScale, 2);
          ctx.font = `${fontSize}px sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "top";
          ctx.fillStyle = "#334155";
          ctx.fillText(label, (node.x as number) ?? 0, ((node.y as number) ?? 0) + 8);
        }}
        cooldownTicks={60}
        enableZoomInteraction={true}
        enablePanInteraction={true}
      />
      <div className="graph-legend">
        {Object.entries(nodeColors).map(([type, color]) => {
          if (!nodes.some((n) => n.type === type)) return null;
          return (
            <span key={type} className="legend-item">
              <span className="legend-dot" style={{ backgroundColor: color }} />
              {type}
            </span>
          );
        })}
      </div>
    </div>
  );
}

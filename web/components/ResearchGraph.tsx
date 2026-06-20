"use client";

import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import type { WorkbenchGraph, WorkbenchNode } from "@/lib/api";

interface ResearchGraphProps {
  data: WorkbenchGraph;
  selectedNodeId?: string | null;
  onNodeClick?: (node: WorkbenchNode) => void;
}

const NODE_COLORS: Record<string, string> = {
  session_started: "#3b82f6",
  plan_created: "#8b5cf6",
  subtask_started: "#f59e0b",
  subtask_completed: "#10b981",
  subtask_failed: "#ef4444",
  search_planned: "#06b6d4",
  search_executed: "#0ea5e9",
  source_added: "#84cc16",
  finding_extracted: "#22c55e",
  agent_action: "#64748b",
  reflection: "#ec4899",
  replan: "#f97316",
  checkpoint: "#eab308",
  intervention: "#dc2626",
  fork: "#7c3aed",
  synthesis_started: "#6366f1",
  report_generated: "#14b8a6",
  session_completed: "#10b981",
  session_failed: "#ef4444",
  default: "#94a3b8",
};

export default function ResearchGraph({
  data,
  selectedNodeId,
  onNodeClick,
}: ResearchGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [dims, setDims] = useState({ width: 800, height: 600 });

  useEffect(() => {
    if (!svgRef.current) return;
    const resize = () => {
      const rect = svgRef.current?.parentElement?.getBoundingClientRect();
      setDims({
        width: rect?.width || 800,
        height: rect?.height || 600,
      });
    };
    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);

  useEffect(() => {
    if (!svgRef.current || data.nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const { width, height } = dims;
    svg.attr("width", width).attr("height", height);

    const g = svg.append("g");
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 5])
      .on("zoom", (event) => {
        g.attr("transform", event.transform.toString());
      });
    svg.call(zoom as any);

    const nodes: (WorkbenchNode & { x?: number; y?: number })[] = data.nodes.map((n) => ({ ...n }));
    const links = data.edges.map((e) => ({ ...e }));

    const simulation = d3
      .forceSimulation(nodes as any)
      .force(
        "link",
        d3
          .forceLink(links as any)
          .id((d: any) => d.id)
          .distance(100)
      )
      .force("charge", d3.forceManyBody().strength(-400))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide().radius(30));

    const link = g
      .append("g")
      .attr("stroke", "#94a3b8")
      .attr("stroke-opacity", 0.4)
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke-width", 1.5);

    const node = g
      .append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .style("cursor", "pointer")
      .call(
        d3
          .drag<any, any>()
          .on("start", (event, d: any) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d: any) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d: any) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      );

    node
      .append("circle")
      .attr("r", (d: any) => (d.kind === "agent_action" ? 6 : 10))
      .attr("fill", (d: any) => NODE_COLORS[d.kind] || NODE_COLORS.default)
      .attr("stroke", (d: any) => (d.id === selectedNodeId ? "#1e3a8a" : "#fff"))
      .attr("stroke-width", (d: any) => (d.id === selectedNodeId ? 3 : 1.5));

    node
      .append("text")
      .text((d: any) => d.label?.slice(0, 30) || d.kind)
      .attr("x", 14)
      .attr("y", 4)
      .attr("font-size", "11px")
      .attr("fill", "currentColor")
      .attr("pointer-events", "none");

    node.on("click", (_event, d: any) => {
      onNodeClick?.(d);
    });

    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      node.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
    });

    return () => {
      simulation.stop();
    };
  }, [data, dims, selectedNodeId, onNodeClick]);

  if (data.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-neutral-500">
        暂无节点，等待研究开始...
      </div>
    );
  }

  return <svg ref={svgRef} className="w-full h-full" />;
}

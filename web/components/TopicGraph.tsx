"use client";

import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import type { GraphData, GraphLink, GraphNode } from "@/lib/api";

interface TopicGraphProps {
  data: GraphData;
  onNodeClick?: (node: GraphNode) => void;
}

export default function TopicGraph({ data, onNodeClick }: TopicGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  useEffect(() => {
    if (!svgRef.current || data.nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = svgRef.current.clientWidth;
    const height = 600;
    svg.attr("width", width).attr("height", height);

    const g = svg.append("g");

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform.toString());
      });

    svg.call(zoom as any);

    const nodes: (GraphNode & { x?: number; y?: number; vx?: number; vy?: number })[] =
      data.nodes.map((n) => ({ ...n }));
    const links: (GraphLink & {
      source?: string | GraphNode;
      target?: string | GraphNode;
    })[] = data.links.map((l) => ({ ...l }));

    const simulation = d3
      .forceSimulation(nodes as any)
      .force(
        "link",
        d3
          .forceLink(links as any)
          .id((d: any) => d.id)
          .distance((d: any) => 200 / Math.sqrt(d.weight || 1))
      )
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force(
        "collide",
        d3.forceCollide().radius((d: any) => 10 + Math.sqrt(d.value || 1) * 2)
      );

    const link = g
      .append("g")
      .attr("stroke", "#94a3b8")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke-width", (d: any) => Math.sqrt(d.weight || 1));

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
      .attr("r", (d: any) => 6 + Math.sqrt(d.value || 1) * 2)
      .attr("fill", (d: any) =>
        selectedNode && selectedNode.id === d.id ? "#2563eb" : "#60a5fa"
      )
      .attr("stroke", "#1e40af")
      .attr("stroke-width", 1.5);

    node
      .append("text")
      .text((d: any) => d.name)
      .attr("x", (d: any) => 8 + Math.sqrt(d.value || 1) * 2)
      .attr("y", 4)
      .attr("font-size", "12px")
      .attr("fill", "currentColor")
      .attr("pointer-events", "none");

    node.on("click", (_event, d: any) => {
      setSelectedNode(d);
      onNodeClick?.(d);
    });

    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => (d.source as any).x)
        .attr("y1", (d: any) => (d.source as any).y)
        .attr("x2", (d: any) => (d.target as any).x)
        .attr("y2", (d: any) => (d.target as any).y);

      node.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
    });

    return () => {
      simulation.stop();
    };
  }, [data, onNodeClick, selectedNode]);

  if (data.nodes.length === 0) {
    return (
      <div className="h-[400px] flex items-center justify-center text-neutral-500 border rounded-xl bg-neutral-50 dark:bg-neutral-900">
        暂无足够数据生成关联图
      </div>
    );
  }

  return (
    <div className="border rounded-xl overflow-hidden bg-white dark:bg-neutral-900">
      <svg ref={svgRef} className="w-full" />
      {selectedNode && (
        <div className="px-4 py-2 border-t text-sm bg-neutral-50 dark:bg-neutral-800">
          <span className="font-medium">{selectedNode.name}</span>
          <span className="text-neutral-500 ml-2">
            出现 {selectedNode.value} 次
          </span>
        </div>
      )}
    </div>
  );
}

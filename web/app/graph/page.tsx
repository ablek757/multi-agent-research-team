"use client";

import { useEffect, useState } from "react";
import { getGraph, type GraphData, type GraphNode } from "@/lib/api";
import TopicGraph from "@/components/TopicGraph";

export default function GraphPage() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  useEffect(() => {
    getGraph(1, 100)
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold mb-1">主题关联网络</h1>
        <p className="text-neutral-600 dark:text-neutral-400 text-sm">
          基于实体共现构建的力导向图，节点大小表示出现频次，连线粗细表示共现强度
        </p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-neutral-500">加载中...</div>
      ) : data ? (
        <>
          <TopicGraph data={data} onNodeClick={setSelectedNode} />
          {selectedNode && (
            <div className="bg-white dark:bg-neutral-900 border rounded-xl p-4">
              <h3 className="font-semibold">{selectedNode.name}</h3>
              <p className="text-sm text-neutral-500 mt-1">
                在知识库中出现 {selectedNode.value} 次。拖动节点可调整布局，滚轮可缩放。
              </p>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}

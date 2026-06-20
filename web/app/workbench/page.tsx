"use client";

import { useEffect, useRef, useState } from "react";
import { Compass, Loader2, Play } from "lucide-react";
import {
  type TraceEvent,
  type WorkbenchGraph,
  type WorkbenchNode,
  type WorkbenchSession,
  forkWorkbenchSession,
  getWorkbenchGraph,
  getWorkbenchSession,
  sendWorkbenchIntervention,
  startWorkbenchSession,
  subscribeWorkbenchEvents,
} from "@/lib/api";
import ResearchGraph from "@/components/ResearchGraph";
import EventTimeline from "@/components/EventTimeline";
import NodeInspector from "@/components/NodeInspector";
import WorkbenchControls from "@/components/WorkbenchControls";

export default function WorkbenchPage() {
  const [topic, setTopic] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [session, setSession] = useState<WorkbenchSession | null>(null);
  const [graph, setGraph] = useState<WorkbenchGraph>({ nodes: [], edges: [], session_id: "", status: "" });
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [selectedNode, setSelectedNode] = useState<WorkbenchNode | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const unsubscribeRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    const load = async () => {
      try {
        const s = await getWorkbenchSession(sessionId);
        setSession(s);
        if (s.graph) setGraph(s.graph);
      } catch (err: any) {
        setError(err.message || "加载会话失败");
      }
    };
    load();

    unsubscribeRef.current = subscribeWorkbenchEvents(sessionId, (event) => {
      setEvents((prev) => {
        if (prev.some((e) => e.id === event.id)) return prev;
        return [...prev, event];
      });
      // 会话完成或失败时刷新一次完整状态
      if (event.type === "session_completed" || event.type === "session_failed") {
        load();
      }
    });

    const interval = setInterval(() => {
      getWorkbenchGraph(sessionId)
        .then(setGraph)
        .catch(() => null);
    }, 3000);

    return () => {
      unsubscribeRef.current?.();
      clearInterval(interval);
    };
  }, [sessionId]);

  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await startWorkbenchSession(topic, true);
      setSessionId(res.session_id);
      const s = await getWorkbenchSession(res.session_id);
      setSession(s);
      if (s.graph) setGraph(s.graph);
      setEvents([]);
      setSelectedNode(null);
    } catch (err: any) {
      setError(err.message || "启动失败");
    } finally {
      setLoading(false);
    }
  };

  const handleIntervene = async (action: string, payload: Record<string, unknown> = {}) => {
    if (!sessionId) return;
    setLoading(true);
    try {
      await sendWorkbenchIntervention(sessionId, action, payload);
      const s = await getWorkbenchSession(sessionId);
      setSession(s);
      if (s.graph) setGraph(s.graph);
    } catch (err: any) {
      setError(err.message || "干预失败");
    } finally {
      setLoading(false);
    }
  };

  const handleFork = async (eventId: string) => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const res = await forkWorkbenchSession(sessionId, eventId, session?.topic);
      setSessionId(res.session_id);
      const s = await getWorkbenchSession(res.session_id);
      setSession(s);
      if (s.graph) setGraph(s.graph);
      setEvents([]);
      setSelectedNode(null);
    } catch (err: any) {
      setError(err.message || "分叉失败");
    } finally {
      setLoading(false);
    }
  };

  const handleEventClick = (event: TraceEvent) => {
    const node = graph.nodes.find((n) => n.id === event.node_id);
    if (node) setSelectedNode(node);
  };

  return (
    <div className="h-[calc(100vh-7rem)] flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <Compass className="w-8 h-8 text-blue-600" />
        <div>
          <h1 className="text-2xl font-bold">认知探索工作台</h1>
          <p className="text-neutral-600 dark:text-neutral-400">
            可观测、可干预、可分叉的交互式研究图谱
          </p>
        </div>
      </div>

      <form onSubmit={handleStart} className="flex gap-2">
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="输入研究主题，例如：量子计算在药物发现中的应用"
          className="flex-1 px-4 py-2 rounded-lg border bg-white dark:bg-neutral-800 focus:ring-2 focus:ring-blue-500 outline-none"
        />
        <button
          type="submit"
          disabled={loading || !topic.trim()}
          className="flex items-center gap-2 px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          开始探索
        </button>
      </form>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300 text-sm">
          {error}
        </div>
      )}

      {sessionId && (
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4 min-h-0">
          <div className="lg:col-span-2 flex flex-col gap-4 min-h-0">
            <div className="flex-1 bg-white dark:bg-neutral-900 border rounded-xl overflow-hidden min-h-0">
              <ResearchGraph
                data={graph}
                selectedNodeId={selectedNode?.id}
                onNodeClick={setSelectedNode}
              />
            </div>
            <div className="h-48 bg-white dark:bg-neutral-900 border rounded-xl p-4 overflow-hidden">
              <h3 className="text-sm font-semibold mb-2">事件时间线</h3>
              <EventTimeline
                events={events}
                selectedEventId={selectedNode?.id}
                onEventClick={handleEventClick}
              />
            </div>
          </div>

          <div className="lg:col-span-2 flex flex-col gap-4 min-h-0">
            <div className="bg-white dark:bg-neutral-900 border rounded-xl p-4">
              <WorkbenchControls
                session={session}
                onIntervene={handleIntervene}
                onFork={handleFork}
                loading={loading}
              />
            </div>
            <div className="flex-1 bg-white dark:bg-neutral-900 border rounded-xl p-4 overflow-hidden">
              <NodeInspector node={selectedNode} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

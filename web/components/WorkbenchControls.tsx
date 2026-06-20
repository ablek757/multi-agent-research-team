"use client";

import { useState } from "react";
import { Pause, Play, Split, Send, Loader2 } from "lucide-react";
import type { WorkbenchSession } from "@/lib/api";

interface WorkbenchControlsProps {
  session: WorkbenchSession | null;
  onIntervene: (action: string, payload?: Record<string, unknown>) => void;
  onFork: (eventId: string) => void;
  loading?: boolean;
}

export default function WorkbenchControls({
  session,
  onIntervene,
  onFork,
  loading,
}: WorkbenchControlsProps) {
  const [query, setQuery] = useState("");
  const status = session?.status;

  const handleInject = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    onIntervene("inject_query", { query: query.trim() });
    setQuery("");
  };

  const latestEventId =
    session?.graph?.nodes?.[session.graph.nodes.length - 1]?.id || "";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm text-neutral-500">会话状态</div>
          <div className="font-semibold capitalize">{status || "未启动"}</div>
        </div>
        <div className="flex gap-2">
          {status === "paused" ? (
            <button
              onClick={() => onIntervene("resume")}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              继续
            </button>
          ) : (
            <button
              onClick={() => onIntervene("pause")}
              disabled={loading || status !== "running"}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-neutral-800 text-white rounded-md text-sm hover:bg-neutral-900 disabled:opacity-50"
            >
              <Pause className="w-4 h-4" />
              暂停
            </button>
          )}
          <button
            onClick={() => latestEventId && onFork(latestEventId)}
            disabled={loading || !latestEventId}
            className="flex items-center gap-1.5 px-3 py-1.5 border rounded-md text-sm hover:bg-neutral-50 dark:hover:bg-neutral-800 disabled:opacity-50"
          >
            <Split className="w-4 h-4" />
            分叉
          </button>
        </div>
      </div>

      <form onSubmit={handleInject} className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="注入搜索查询或开放问题..."
          className="flex-1 px-3 py-1.5 rounded-md border bg-white dark:bg-neutral-800 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
        />
        <button
          type="submit"
          disabled={loading || !query.trim() || status !== "running"}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          注入
        </button>
      </form>

      {Boolean(session?.metadata?.summary) && (
        <SummaryCards summary={session!.metadata.summary} />
      )}
    </div>
  );
}

function SummaryCards({ summary }: { summary: unknown }) {
  const s = summary as Record<string, number | null | undefined>;
  return (
    <div className="grid grid-cols-2 gap-2 text-sm">
      {s.sources !== undefined && s.sources !== null && (
        <div className="bg-neutral-50 dark:bg-neutral-800 rounded-md p-2 text-center">
          <div className="font-bold text-blue-600">{s.sources}</div>
          <div className="text-xs text-neutral-500">来源</div>
        </div>
      )}
      {s.findings !== undefined && s.findings !== null && (
        <div className="bg-neutral-50 dark:bg-neutral-800 rounded-md p-2 text-center">
          <div className="font-bold">{s.findings}</div>
          <div className="text-xs text-neutral-500">发现</div>
        </div>
      )}
    </div>
  );
}

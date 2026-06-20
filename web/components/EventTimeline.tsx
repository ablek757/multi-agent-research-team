"use client";

import type { TraceEvent } from "@/lib/api";

interface EventTimelineProps {
  events: TraceEvent[];
  selectedEventId?: string | null;
  onEventClick?: (event: TraceEvent) => void;
}

const KIND_LABELS: Record<string, string> = {
  session_started: "会话开始",
  plan_created: "计划创建",
  subtask_started: "子任务开始",
  subtask_completed: "子任务完成",
  subtask_failed: "子任务失败",
  search_planned: "搜索规划",
  search_executed: "搜索执行",
  source_added: "来源加入",
  finding_extracted: "发现提取",
  agent_action: "Agent 动作",
  reflection: "元认知反思",
  replan: "重规划",
  checkpoint: "检查点",
  intervention: "用户干预",
  fork: "分叉",
  synthesis_started: "综合撰稿",
  report_generated: "报告生成",
  session_completed: "会话完成",
  session_failed: "会话失败",
};

export default function EventTimeline({
  events,
  selectedEventId,
  onEventClick,
}: EventTimelineProps) {
  const sorted = [...events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  return (
    <div className="h-full overflow-auto pr-2 space-y-2">
      {sorted.length === 0 && (
        <div className="text-neutral-500 text-sm text-center py-8">暂无事件</div>
      )}
      {sorted.map((event) => {
        const label =
          (event.payload?.label as string) ||
          KIND_LABELS[event.type] ||
          event.type;
        const isSelected = event.node_id === selectedEventId || event.id === selectedEventId;
        return (
          <button
            key={event.id}
            onClick={() => onEventClick?.(event)}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm border transition-colors ${
              isSelected
                ? "bg-blue-50 border-blue-300 dark:bg-blue-900/20 dark:border-blue-700"
                : "bg-white dark:bg-neutral-900 border-neutral-200 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800"
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-neutral-500">
                {new Date(event.timestamp).toLocaleTimeString()}
              </span>
              <span className="font-medium">{label}</span>
            </div>
            {event.agent && (
              <div className="text-xs text-neutral-500 mt-0.5">@{event.agent}</div>
            )}
          </button>
        );
      })}
    </div>
  );
}

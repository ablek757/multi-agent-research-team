"use client";

import { FileText, Link2, Lightbulb, CalendarDays } from "lucide-react";

interface StatsCardsProps {
  stats: {
    report_count: number;
    entity_count: number;
    topic_count: number;
    source_count: number;
    finding_count: number;
    event_count: number;
  };
}

export default function StatsCards({ stats }: StatsCardsProps) {
  const items = [
    { label: "研究报告", value: stats.report_count, icon: FileText },
    { label: "关键实体", value: stats.entity_count, icon: Link2 },
    { label: "研究主题", value: stats.topic_count, icon: Lightbulb },
    { label: "参考来源", value: stats.source_count, icon: Link2 },
    { label: "关键发现", value: stats.finding_count, icon: Lightbulb },
    { label: "时间事件", value: stats.event_count, icon: CalendarDays },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <div
            key={item.label}
            className="bg-white dark:bg-neutral-900 border rounded-xl p-4 flex items-center gap-3 shadow-sm"
          >
            <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <Icon className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <div className="text-2xl font-bold">{item.value}</div>
              <div className="text-xs text-neutral-500">{item.label}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

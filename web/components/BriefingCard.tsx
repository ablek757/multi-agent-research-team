"use client";

import { Calendar, FileText } from "lucide-react";
import type { IntelligenceBriefing } from "@/lib/api";

interface BriefingCardProps {
  briefing: IntelligenceBriefing;
}

export default function BriefingCard({ briefing }: BriefingCardProps) {
  return (
    <div className="bg-white dark:bg-neutral-900 border rounded-xl p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start gap-3">
        <div className="p-2 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg shrink-0">
          <FileText className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
        </div>
        <div className="min-w-0">
          <h3 className="font-semibold text-lg truncate">{briefing.title}</h3>
          <p className="text-sm text-neutral-500 truncate mt-0.5">
            主题：{briefing.topic}
          </p>
          <div className="flex flex-wrap gap-3 mt-3 text-xs text-neutral-500">
            <span className="flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" />
              {briefing.date || briefing.created_at || "未知时间"}
            </span>
            <span>{briefing.alerts.length} 条告警</span>
          </div>
        </div>
      </div>
      <div className="mt-4 text-sm text-neutral-700 dark:text-neutral-300 line-clamp-4 whitespace-pre-line">
        {briefing.content.slice(0, 300)}
        {briefing.content.length > 300 ? "..." : ""}
      </div>
    </div>
  );
}

"use client";

import Link from "next/link";
import type { Event } from "@/lib/api";

interface TimelineChartProps {
  events: Event[];
}

export default function TimelineChart({ events }: TimelineChartProps) {
  if (events.length === 0) {
    return (
      <div className="h-[200px] flex items-center justify-center text-neutral-500 border rounded-xl bg-neutral-50 dark:bg-neutral-900">
        暂无时间线数据
      </div>
    );
  }

  return (
    <div className="relative border-l-2 border-blue-200 dark:border-blue-900 ml-4 my-4 space-y-6">
      {events.map((event) => (
        <div key={event.id} className="relative pl-8">
          <span className="absolute -left-[9px] top-1.5 w-4 h-4 rounded-full bg-blue-500 border-2 border-white dark:border-neutral-900" />
          <div className="bg-white dark:bg-neutral-900 border rounded-lg p-4">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <span className="font-semibold text-blue-700 dark:text-blue-400">
                {event.date_text}
              </span>
              {event.date_iso && (
                <span className="text-xs text-neutral-500">({event.date_iso})</span>
              )}
            </div>
            <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">
              {event.description}
            </p>
            <Link
              href={`/reports/${encodeURIComponent(event.report_id)}`}
              className="inline-block mt-2 text-xs text-blue-600 hover:underline"
            >
              查看报告 →
            </Link>
          </div>
        </div>
      ))}
    </div>
  );
}

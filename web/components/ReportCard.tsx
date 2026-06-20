"use client";

import Link from "next/link";
import { Calendar, FileText } from "lucide-react";
import type { Report } from "@/lib/api";

interface ReportCardProps {
  report: Report;
}

export default function ReportCard({ report }: ReportCardProps) {
  return (
    <Link
      href={`/reports/${encodeURIComponent(report.id)}`}
      className="block bg-white dark:bg-neutral-900 border rounded-xl p-5 hover:shadow-md transition-shadow"
    >
      <div className="flex items-start gap-3">
        <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg shrink-0">
          <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400" />
        </div>
        <div className="min-w-0">
          <h3 className="font-semibold text-lg truncate">{report.title}</h3>
          {report.topic && (
            <p className="text-sm text-neutral-500 truncate mt-0.5">
              主题：{report.topic}
            </p>
          )}
          <div className="flex flex-wrap gap-3 mt-3 text-xs text-neutral-500">
            <span className="flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" />
              {report.created_at || "未知时间"}
            </span>
            <span>{report.findings.length} 条发现</span>
            <span>{report.entities.length} 个实体</span>
            <span>{report.sources.length} 个来源</span>
          </div>
          {report.entities.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {report.entities.slice(0, 5).map((e) => (
                <span
                  key={e.id}
                  className="px-2 py-0.5 bg-neutral-100 dark:bg-neutral-800 rounded text-xs"
                >
                  {e.name}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}

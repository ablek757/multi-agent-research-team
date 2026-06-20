"use client";

import { ExternalLink, TrendingUp, Sparkles, Target } from "lucide-react";
import type { IntelligenceAlert } from "@/lib/api";

interface AlertCardProps {
  alert: IntelligenceAlert;
}

export default function AlertCard({ alert }: AlertCardProps) {
  const { article, scores } = alert;
  return (
    <div className="bg-white dark:bg-neutral-900 border rounded-xl p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold text-lg leading-tight">{article.title}</h3>
          <p className="text-sm text-neutral-500 mt-1">
            来源：{article.source} · {article.published_date || "未知日期"}
          </p>
        </div>
        <a
          href={article.url}
          target="_blank"
          rel="noreferrer"
          className="shrink-0 p-2 text-neutral-400 hover:text-blue-600"
        >
          <ExternalLink className="w-4 h-4" />
        </a>
      </div>

      <p className="text-sm text-neutral-700 dark:text-neutral-300 mt-3 line-clamp-3">
        {article.abstract || "暂无摘要"}
      </p>

      <div className="flex flex-wrap gap-2 mt-4">
        <ScoreBadge
          icon={Target}
          label="相关"
          value={scores.relevance}
          color="bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300"
        />
        <ScoreBadge
          icon={Sparkles}
          label="新颖"
          value={scores.novelty}
          color="bg-purple-50 text-purple-700 dark:bg-purple-900/20 dark:text-purple-300"
        />
        <ScoreBadge
          icon={TrendingUp}
          label="突破"
          value={scores.breakthrough}
          color="bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300"
        />
      </div>

      {scores.reason && (
        <p className="text-xs text-neutral-500 mt-3">{scores.reason}</p>
      )}
    </div>
  );
}

function ScoreBadge({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
  color: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium ${color}`}
    >
      <Icon className="w-3.5 h-3.5" />
      {label} {value}
    </span>
  );
}

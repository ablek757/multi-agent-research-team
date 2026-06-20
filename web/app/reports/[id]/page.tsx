"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Calendar, ExternalLink, Lightbulb } from "lucide-react";
import { getReport, type Report } from "@/lib/api";
import MarkdownViewer from "@/components/MarkdownViewer";

export default function ReportDetailPage() {
  const params = useParams();
  const id = decodeURIComponent(params.id as string);

  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getReport(id)
      .then(setReport)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <div className="text-center py-12 text-neutral-500">加载中...</div>;
  }

  if (error || !report) {
    return (
      <div className="text-center py-12 text-red-500">
        {error || "报告不存在"}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Link
        href="/reports"
        className="inline-flex items-center gap-1 text-sm text-neutral-600 hover:text-blue-600"
      >
        <ArrowLeft className="w-4 h-4" /> 返回报告库
      </Link>

      <div className="bg-white dark:bg-neutral-900 border rounded-xl p-6">
        <h1 className="text-2xl font-bold mb-2">{report.title}</h1>
        {report.topic && (
          <p className="text-neutral-600 dark:text-neutral-400 mb-4">
            研究主题：{report.topic}
          </p>
        )}
        <div className="flex flex-wrap gap-4 text-sm text-neutral-500 mb-4">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            {report.created_at || "未知时间"}
          </span>
          <span>模型：{report.model || "-"}</span>
        </div>

        {report.entities.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold mb-2 flex items-center gap-1">
              <Lightbulb className="w-4 h-4" /> 关键实体
            </h3>
            <div className="flex flex-wrap gap-2">
              {report.entities.map((e) => (
                <span
                  key={e.id}
                  className="px-2.5 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-full text-xs"
                >
                  {e.name}
                </span>
              ))}
            </div>
          </div>
        )}

        {report.findings.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold mb-2">关键发现</h3>
            <ul className="list-disc list-inside space-y-1 text-sm text-neutral-700 dark:text-neutral-300">
              {report.findings.slice(0, 10).map((f, idx) => (
                <li key={idx}>{f.text}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="bg-white dark:bg-neutral-900 border rounded-xl p-6">
        <MarkdownViewer content={report.content} />
      </div>

      {report.sources.length > 0 && (
        <div className="bg-white dark:bg-neutral-900 border rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-4">参考来源</h2>
          <ul className="space-y-2">
            {report.sources.map((source) => (
              <li key={source.index} className="text-sm">
                <span className="text-neutral-500">[{source.index}]</span>{" "}
                <a
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-blue-600 hover:underline inline-flex items-center gap-1"
                >
                  {source.title}
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

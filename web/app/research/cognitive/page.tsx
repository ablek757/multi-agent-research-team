"use client";

import { useEffect, useState } from "react";
import { Brain, Loader2, Play, FileText } from "lucide-react";
import { getResearchStatus, listOutputFormats, startResearch, ResearchJob } from "@/lib/api";

export default function CognitiveResearchPage() {
  const [topic, setTopic] = useState("");
  const [cognitive, setCognitive] = useState(true);
  const [selectedFormats, setSelectedFormats] = useState<string[]>(["markdown"]);
  const [formats, setFormats] = useState<string[]>([]);
  const [job, setJob] = useState<ResearchJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    listOutputFormats().then((data) => setFormats(data.formats));
  }, []);

  useEffect(() => {
    if (!job || job.status === "completed" || job.status === "failed") return;
    const interval = setInterval(() => {
      getResearchStatus(job.job_id).then(setJob);
    }, 2000);
    return () => clearInterval(interval);
  }, [job]);

  const toggleFormat = (fmt: string) => {
    setSelectedFormats((prev) =>
      prev.includes(fmt) ? prev.filter((f) => f !== fmt) : [...prev, fmt]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    setLoading(true);
    setError("");
    setJob(null);
    try {
      const res = await startResearch(topic, cognitive, selectedFormats);
      const initial = await getResearchStatus(res.job_id);
      setJob(initial);
    } catch (err: any) {
      setError(err.message || "启动研究失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div className="flex items-center gap-3">
        <Brain className="w-8 h-8 text-blue-600" />
        <div>
          <h1 className="text-2xl font-bold">认知增强研究</h1>
          <p className="text-neutral-600 dark:text-neutral-400">
            输入主题，系统自动分解子任务、执行多 Agent 研究并生成多模态成果。
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="bg-white dark:bg-neutral-900 border rounded-xl p-6 space-y-6">
        <div>
          <label className="block text-sm font-medium mb-2">研究主题</label>
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="例如：量子计算在药物发现中的应用"
            className="w-full px-4 py-2 rounded-lg border bg-white dark:bg-neutral-800 focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>

        <div className="flex items-center gap-3">
          <input
            id="cognitive"
            type="checkbox"
            checked={cognitive}
            onChange={(e) => setCognitive(e.target.checked)}
            className="w-5 h-5 text-blue-600"
          />
          <label htmlFor="cognitive" className="text-sm font-medium">
            启用认知增强（任务分解、反思、重规划）
          </label>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">输出格式</label>
          <div className="flex flex-wrap gap-2">
            {formats.map((fmt) => (
              <button
                key={fmt}
                type="button"
                onClick={() => toggleFormat(fmt)}
                className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${
                  selectedFormats.includes(fmt)
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white dark:bg-neutral-800 hover:bg-neutral-100 dark:hover:bg-neutral-700"
                }`}
              >
                {fmt}
              </button>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !topic.trim()}
          className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          {loading ? "启动中..." : "开始研究"}
        </button>
      </form>

      {error && (
        <div className="p-4 rounded-lg bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}

      {job && (
        <div className="bg-white dark:bg-neutral-900 border rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <FileText className="w-5 h-5" />
              任务状态：{job.status}
            </h2>
            {job.status !== "completed" && job.status !== "failed" && (
              <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
            )}
          </div>

          {job.logs && job.logs.length > 0 && (
            <div className="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 h-64 overflow-auto text-sm space-y-1">
              {job.logs.map((log, idx) => (
                <div key={idx} className="text-neutral-700 dark:text-neutral-300">
                  {log}
                </div>
              ))}
            </div>
          )}

          {job.metrics && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-blue-600">{job.metrics.overall_score}</div>
                <div className="text-xs text-neutral-500">综合评分</div>
              </div>
              <div className="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold">{job.sources}</div>
                <div className="text-xs text-neutral-500">来源数</div>
              </div>
              <div className="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold">{job.findings}</div>
                <div className="text-xs text-neutral-500">关键发现</div>
              </div>
              <div className="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold">{job.outputs?.length || 0}</div>
                <div className="text-xs text-neutral-500">输出文件</div>
              </div>
            </div>
          )}

          {job.outputs && job.outputs.length > 0 && (
            <div className="space-y-2">
              <h3 className="font-medium">生成文件</h3>
              <div className="space-y-1">
                {job.outputs.map((out, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 bg-neutral-50 dark:bg-neutral-800 rounded-lg"
                  >
                    <span className="font-medium">{out.format}</span>
                    {out.path ? (
                      <span className="text-sm text-neutral-500 truncate max-w-xs">{out.path}</span>
                    ) : (
                      <span className="text-sm text-red-500">{out.error}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

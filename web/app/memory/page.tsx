"use client";

import { useState } from "react";
import Link from "next/link";
import { Search, Sparkles } from "lucide-react";
import { semanticSearch, Report } from "@/lib/api";

export default function MemoryPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<{ report: Report; score: number }[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await semanticSearch(query, 10);
      setResults(data.results);
      setSearched(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="flex items-center gap-3">
        <Sparkles className="w-8 h-8 text-purple-600" />
        <div>
          <h1 className="text-2xl font-bold">语义记忆检索</h1>
          <p className="text-neutral-600 dark:text-neutral-400">
            基于向量 embedding 召回历史相关研究，发现跨主题关联。
          </p>
        </div>
      </div>

      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="输入研究主题或关键词..."
          className="flex-1 px-4 py-2 rounded-lg border bg-white dark:bg-neutral-800 focus:ring-2 focus:ring-purple-500 outline-none"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="flex items-center gap-2 px-5 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
        >
          <Search className="w-4 h-4" />
          {loading ? "检索中..." : "语义搜索"}
        </button>
      </form>

      {searched && results.length === 0 && (
        <div className="text-center text-neutral-500 py-12 border rounded-xl bg-white dark:bg-neutral-900">
          未找到语义相关报告。
        </div>
      )}

      <div className="space-y-4">
        {results.map(({ report, score }) => (
          <Link
            key={report.id}
            href={`/reports/${report.id}`}
            className="block bg-white dark:bg-neutral-900 border rounded-xl p-5 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-lg font-semibold">{report.title}</h2>
              <span className="text-sm font-medium text-purple-600 bg-purple-50 dark:bg-purple-900/20 px-2 py-1 rounded">
                相似度 {score.toFixed(3)}
              </span>
            </div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 line-clamp-2">
              {report.content?.slice(0, 200) || "无摘要"}
            </p>
            <div className="mt-3 text-xs text-neutral-500">
              {report.entities?.slice(0, 8).map((e) => (
                <span
                  key={e.id}
                  className="inline-block mr-2 mb-1 px-2 py-0.5 bg-neutral-100 dark:bg-neutral-800 rounded"
                >
                  {e.name}
                </span>
              ))}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

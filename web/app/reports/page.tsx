"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { listReports, searchReports, type Report } from "@/lib/api";
import ReportCard from "@/components/ReportCard";
import SearchBar from "@/components/SearchBar";

function ReportsPageContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  const [query, setQuery] = useState(initialQuery);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);

  const fetchData = async (q: string) => {
    setLoading(true);
    try {
      if (q) {
        const results = await searchReports(q, 50);
        setReports(results.map((r) => r.report));
        setTotal(results.length);
      } else {
        const data = await listReports(undefined, 50, 0);
        setReports(data.reports);
        setTotal(data.total);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(initialQuery);
  }, [initialQuery]);

  const handleSearch = (q: string) => {
    setQuery(q);
    const url = new URL(window.location.href);
    if (q) url.searchParams.set("q", q);
    else url.searchParams.delete("q");
    window.history.pushState({}, "", url.toString());
    fetchData(q);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-2">研究报告库</h1>
        <p className="text-neutral-600 dark:text-neutral-400">
          共 {total} 份报告
        </p>
      </div>

      <SearchBar
        initialQuery={query}
        onSearch={handleSearch}
        placeholder="搜索报告标题、主题、实体或发现..."
      />

      {loading ? (
        <div className="text-center py-12 text-neutral-500">加载中...</div>
      ) : reports.length === 0 ? (
        <div className="text-center py-12 text-neutral-500 border rounded-xl bg-white dark:bg-neutral-900">
          {query ? "未找到匹配的报告" : "暂无报告"}
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {reports.map((report) => (
            <ReportCard key={report.id} report={report} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function ReportsPage() {
  return (
    <Suspense
      fallback={
        <div className="text-center py-12 text-neutral-500">加载中...</div>
      }
    >
      <ReportsPageContent />
    </Suspense>
  );
}

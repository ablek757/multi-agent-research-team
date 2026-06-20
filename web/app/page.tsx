import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { getStats, listReports } from "@/lib/api";
import StatsCards from "@/components/StatsCards";
import ReportCard from "@/components/ReportCard";
import SearchBar from "@/components/SearchBar";

export default async function HomePage() {
  const stats = await getStats();
  const recent = await listReports(undefined, 6, 0);

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-bold mb-2">研究成果知识库</h1>
        <p className="text-neutral-600 dark:text-neutral-400 mb-6">
          结构化存储、主题关联分析、时间线追踪与全文检索
        </p>
        <StatsCards stats={stats} />
      </section>

      <section className="bg-white dark:bg-neutral-900 border rounded-xl p-6">
        <h2 className="text-lg font-semibold mb-4">快速搜索</h2>
        <SearchBar action="/reports" />
      </section>

      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">最近研究</h2>
          <Link
            href="/reports"
            className="text-sm text-blue-600 hover:underline flex items-center gap-1"
          >
            查看全部 <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
        {recent.reports.length === 0 ? (
          <div className="text-neutral-500 border rounded-xl p-8 text-center bg-white dark:bg-neutral-900">
            暂无报告。运行{" "}
            <code className="bg-neutral-100 dark:bg-neutral-800 px-1.5 py-0.5 rounded text-sm">
              python main.py &quot;主题&quot;
            </code>{" "}
            生成并自动导入。
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {recent.reports.map((report) => (
              <ReportCard key={report.id} report={report} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

import Link from "next/link";
import { ArrowRight, Radio } from "lucide-react";
import { getIntelligenceTopics, listAlerts, listBriefings } from "@/lib/api";
import AlertCard from "@/components/AlertCard";
import BriefingCard from "@/components/BriefingCard";
import ScanButton from "@/components/ScanButton";

export default async function IntelligencePage() {
  let topicsData: { topics: Record<string, { entities: string[]; report_ids: string[] }> } = { topics: {} };
  let alertsData: { alerts: any[] } = { alerts: [] };
  let briefingsData: { briefings: any[] } = { briefings: [] };

  try {
    [topicsData, alertsData, briefingsData] = await Promise.all([
      getIntelligenceTopics(),
      listAlerts(undefined, 6, 0),
      listBriefings(undefined, 3, 0),
    ]);
  } catch (err) {
    // 构建时 API 可能未运行，使用空数据
  }

  const topics = Object.entries(topicsData.topics);

  return (
    <div className="space-y-8">
      <section className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold mb-2 flex items-center gap-2">
            <Radio className="w-6 h-6 text-red-500" />
            实时研究情报中心
          </h1>
          <p className="text-neutral-600 dark:text-neutral-400">
            7×24 小时扫描全球学术源，发现与你知识库主题相关的新突破
          </p>
        </div>
        <ScanButton />
      </section>

      <section className="bg-white dark:bg-neutral-900 border rounded-xl p-6">
        <h2 className="text-lg font-semibold mb-4">监控主题</h2>
        {topics.length === 0 ? (
          <p className="text-neutral-500">
            暂无监控主题。请先运行研究任务，将报告导入知识库。
          </p>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {topics.map(([topic, meta]) => (
              <div
                key={topic}
                className="border rounded-lg p-4 bg-neutral-50 dark:bg-neutral-800/50"
              >
                <h3 className="font-medium truncate">{topic}</h3>
                <p className="text-xs text-neutral-500 mt-1">
                  {meta.report_ids.length} 份报告 · {meta.entities.length} 个实体
                </p>
                {meta.entities.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {meta.entities.slice(0, 5).map((e) => (
                      <span
                        key={e}
                        className="px-1.5 py-0.5 bg-white dark:bg-neutral-800 border rounded text-xs"
                      >
                        {e}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">最新告警</h2>
          <Link
            href="/intelligence/alerts"
            className="text-sm text-blue-600 hover:underline flex items-center gap-1"
          >
            查看全部 <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
        {alertsData.alerts.length === 0 ? (
          <div className="text-neutral-500 border rounded-xl p-8 text-center bg-white dark:bg-neutral-900">
            暂无告警。点击右上角「立即扫描」手动触发一次学术源扫描。
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {alertsData.alerts.map((alert) => (
              <AlertCard key={alert.id} alert={alert} />
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">最新简报</h2>
          <Link
            href="/intelligence/briefings"
            className="text-sm text-blue-600 hover:underline flex items-center gap-1"
          >
            查看全部 <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
        {briefingsData.briefings.length === 0 ? (
          <div className="text-neutral-500 border rounded-xl p-8 text-center bg-white dark:bg-neutral-900">
            暂无简报。扫描并生成告警后会自动生成个性化简报。
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {briefingsData.briefings.map((briefing) => (
              <BriefingCard key={briefing.id} briefing={briefing} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

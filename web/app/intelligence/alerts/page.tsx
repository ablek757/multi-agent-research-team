import { listAlerts } from "@/lib/api";
import AlertCard from "@/components/AlertCard";
import Pagination from "@/components/Pagination";

interface AlertsPageProps {
  searchParams: Promise<{ topic?: string; offset?: string }>;
}

export default async function AlertsPage({ searchParams }: AlertsPageProps) {
  const { topic, offset = "0" } = await searchParams;
  const offsetNum = parseInt(offset, 10) || 0;
  const limit = 12;
  const data = await listAlerts(topic, limit, offsetNum);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-2">全部告警</h1>
        <p className="text-neutral-600 dark:text-neutral-400">
          共 {data.total} 条与知识库主题相关的情报告警
        </p>
      </div>

      {data.alerts.length === 0 ? (
        <div className="text-neutral-500 border rounded-xl p-8 text-center bg-white dark:bg-neutral-900">
          暂无告警。
        </div>
      ) : (
        <>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.alerts.map((alert) => (
              <AlertCard key={alert.id} alert={alert} />
            ))}
          </div>
          <Pagination
            total={data.total}
            limit={data.limit}
            offset={data.offset}
            basePath="/intelligence/alerts"
          />
        </>
      )}
    </div>
  );
}

import { getTimeline } from "@/lib/api";
import TimelineChart from "@/components/TimelineChart";

export default async function TimelinePage() {
  const events = await getTimeline();

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold mb-1">研究时间线</h1>
        <p className="text-neutral-600 dark:text-neutral-400 text-sm">
          从各研究报告中自动抽取的关键事件，按时间顺序排列
        </p>
      </div>
      <div className="bg-white dark:bg-neutral-900 border rounded-xl p-6">
        <TimelineChart events={events} />
      </div>
    </div>
  );
}

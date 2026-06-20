import { listBriefings } from "@/lib/api";
import BriefingCard from "@/components/BriefingCard";
import Pagination from "@/components/Pagination";

interface BriefingsPageProps {
  searchParams: Promise<{ topic?: string; offset?: string }>;
}

export default async function BriefingsPage({
  searchParams,
}: BriefingsPageProps) {
  const { topic, offset = "0" } = await searchParams;
  const offsetNum = parseInt(offset, 10) || 0;
  const limit = 12;
  const data = await listBriefings(topic, limit, offsetNum);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-2">全部简报</h1>
        <p className="text-neutral-600 dark:text-neutral-400">
          共 {data.total} 份个性化研究简报
        </p>
      </div>

      {data.briefings.length === 0 ? (
        <div className="text-neutral-500 border rounded-xl p-8 text-center bg-white dark:bg-neutral-900">
          暂无简报。
        </div>
      ) : (
        <>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.briefings.map((briefing) => (
              <BriefingCard key={briefing.id} briefing={briefing} />
            ))}
          </div>
          <Pagination
            total={data.total}
            limit={data.limit}
            offset={data.offset}
            basePath="/intelligence/briefings"
          />
        </>
      )}
    </div>
  );
}

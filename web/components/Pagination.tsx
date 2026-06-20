import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  basePath: string;
}

export default function Pagination({
  total,
  limit,
  offset,
  basePath,
}: PaginationProps) {
  const hasPrev = offset > 0;
  const hasNext = offset + limit < total;

  const buildHref = (newOffset: number) => {
    const params = new URLSearchParams();
    params.set("offset", String(newOffset));
    return `${basePath}?${params.toString()}`;
  };

  return (
    <div className="flex items-center justify-center gap-4 pt-4">
      {hasPrev ? (
        <Link
          href={buildHref(Math.max(0, offset - limit))}
          className="flex items-center gap-1 px-3 py-2 border rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-800 text-sm"
        >
          <ChevronLeft className="w-4 h-4" /> 上一页
        </Link>
      ) : (
        <span className="flex items-center gap-1 px-3 py-2 border rounded-lg text-neutral-400 cursor-not-allowed text-sm">
          <ChevronLeft className="w-4 h-4" /> 上一页
        </span>
      )}
      <span className="text-sm text-neutral-600 dark:text-neutral-400">
        {offset + 1} - {Math.min(offset + limit, total)} / {total}
      </span>
      {hasNext ? (
        <Link
          href={buildHref(offset + limit)}
          className="flex items-center gap-1 px-3 py-2 border rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-800 text-sm"
        >
          下一页 <ChevronRight className="w-4 h-4" />
        </Link>
      ) : (
        <span className="flex items-center gap-1 px-3 py-2 border rounded-lg text-neutral-400 cursor-not-allowed text-sm">
          下一页 <ChevronRight className="w-4 h-4" />
        </span>
      )}
    </div>
  );
}

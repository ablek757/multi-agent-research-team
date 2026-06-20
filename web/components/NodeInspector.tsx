"use client";

import type { WorkbenchNode } from "@/lib/api";

interface NodeInspectorProps {
  node: WorkbenchNode | null;
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  if (value === undefined || value === null || value === "") return null;
  return (
    <div className="mb-3">
      <div className="text-xs font-medium text-neutral-500 mb-0.5">{label}</div>
      <div className="text-sm text-neutral-900 dark:text-neutral-100 break-words">{value}</div>
    </div>
  );
}

function str(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function arr(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export default function NodeInspector({ node }: NodeInspectorProps) {
  if (!node) {
    return (
      <div className="h-full flex items-center justify-center text-neutral-500 text-sm">
        选择节点查看详情
      </div>
    );
  }

  const p = node.payload || {};
  const description = str(p.description);
  const goal = str(p.goal);
  const query = str(p.query);
  const queries = arr(p.queries);
  const finding = str(p.finding);
  const url = str(p.url);
  const title = str(p.title);
  const summary = str(p.summary);
  const reasoning = str(p.reasoning);
  const informationGaps = arr(p.information_gaps);
  const suggestedQueries = arr(p.suggested_queries);
  const subtasks = arr(p.subtasks);
  const sources = p.sources;
  const findings = p.findings;
  const error = str(p.error);

  return (
    <div className="h-full overflow-auto pr-1">
      <div className="text-xs font-medium text-blue-600 uppercase tracking-wide mb-2">
        {node.kind}
      </div>
      <h3 className="font-semibold text-sm mb-4">{node.label}</h3>

      <Field label="ID" value={node.id} />
      {description && <Field label="描述" value={description} />}
      {goal && <Field label="目标" value={goal} />}
      {query && <Field label="查询" value={query} />}
      {queries.length > 0 && (
        <Field
          label="查询列表"
          value={
            <ul className="list-disc pl-4 space-y-0.5">
              {queries.map((q, i) => (
                <li key={i}>{String(q)}</li>
              ))}
            </ul>
          }
        />
      )}
      {finding && <Field label="发现" value={finding} />}
      {url && (
        <Field
          label="URL"
          value={
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              className="text-blue-600 hover:underline break-all"
            >
              {url}
            </a>
          }
        />
      )}
      {title && <Field label="标题" value={title} />}
      {summary && <Field label="摘要" value={summary} />}
      {reasoning && <Field label="推理" value={reasoning} />}
      {informationGaps.length > 0 && (
        <Field
          label="信息缺口"
          value={
            <ul className="list-disc pl-4 space-y-0.5">
              {informationGaps.map((g, i) => (
                <li key={i}>{String(g)}</li>
              ))}
            </ul>
          }
        />
      )}
      {suggestedQueries.length > 0 && (
        <Field
          label="建议查询"
          value={
            <ul className="list-disc pl-4 space-y-0.5">
              {suggestedQueries.map((q, i) => (
                <li key={i}>{String(q)}</li>
              ))}
            </ul>
          }
        />
      )}
      {subtasks.length > 0 && (
        <Field
          label="子任务"
          value={
            <ul className="list-disc pl-4 space-y-0.5">
              {subtasks.map((st, i) => {
                const s = st as { id?: string; description?: string; status?: string };
                return (
                  <li key={i}>
                    {s.id}: {s.description}
                    {s.status ? ` [${s.status}]` : ""}
                  </li>
                );
              })}
            </ul>
          }
        />
      )}
      {sources !== undefined && <Field label="来源数" value={String(sources)} />}
      {findings !== undefined && <Field label="发现数" value={String(findings)} />}
      {error && (
        <Field label="错误" value={<span className="text-red-600">{error}</span>} />
      )}
    </div>
  );
}

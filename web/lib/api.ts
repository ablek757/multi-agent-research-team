const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export interface Source {
  index: number;
  title: string;
  url: string;
  snippet: string;
}

export interface Finding {
  text: string;
  source_index?: number;
  source_url?: string;
}

export interface Entity {
  id: string;
  name: string;
  report_ids: string[];
  count: number;
}

export interface Topic {
  id: string;
  name: string;
  report_ids: string[];
  count: number;
}

export interface Event {
  id: string;
  date_text: string;
  date_iso?: string;
  description: string;
  report_id: string;
  report_title: string;
}

export interface Report {
  id: string;
  title: string;
  topic: string;
  created_at: string;
  model: string;
  content: string;
  sources: Source[];
  findings: Finding[];
  entities: Entity[];
  topics: Topic[];
  events: Event[];
  markdown_path?: string;
  state_path?: string;
}

export interface Stats {
  report_count: number;
  entity_count: number;
  topic_count: number;
  source_count: number;
  finding_count: number;
  event_count: number;
  updated_at: string;
}

export interface GraphNode {
  id: string;
  name: string;
  value: number;
}

export interface GraphLink {
  source: string;
  target: string;
  weight: number;
  report_ids: string[];
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function getStats(): Promise<Stats> {
  return fetchJson<Stats>("/api/stats");
}

export async function listReports(
  q?: string,
  limit = 20,
  offset = 0
): Promise<{ total: number; limit: number; offset: number; reports: Report[] }> {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return fetchJson(`/api/reports?${params.toString()}`);
}

export async function getReport(id: string): Promise<Report> {
  return fetchJson<Report>(`/api/reports/${encodeURIComponent(id)}`);
}

export async function searchReports(
  q: string,
  topK = 20
): Promise<{ report: Report; score: number }[]> {
  const params = new URLSearchParams();
  params.set("q", q);
  params.set("top_k", String(topK));
  return fetchJson(`/api/search?${params.toString()}`);
}

export async function getGraph(
  minEdgeWeight = 1,
  topN = 100
): Promise<GraphData> {
  const params = new URLSearchParams();
  params.set("min_edge_weight", String(minEdgeWeight));
  params.set("top_n_nodes", String(topN));
  return fetchJson(`/api/graph?${params.toString()}`);
}

export async function getTimeline(): Promise<Event[]> {
  return fetchJson<Event[]>("/api/timeline");
}

export interface AlertScores {
  relevance: number;
  novelty: number;
  breakthrough: number;
  reason: string;
}

export interface AlertArticle {
  id: string;
  title: string;
  abstract: string;
  authors: string[];
  url: string;
  doi: string;
  published_date: string;
  source: string;
}

export interface IntelligenceAlert {
  id: string;
  topic: string;
  article: AlertArticle;
  scores: AlertScores;
  created_at: string;
  notified: boolean;
}

export interface IntelligenceBriefing {
  id: string;
  topic: string;
  title: string;
  date: string;
  content: string;
  alerts: IntelligenceAlert[];
  created_at: string;
  markdown_path?: string;
}

export interface IntelligenceTopics {
  topics: Record<string, { entities: string[]; report_ids: string[] }>;
}

export async function getIntelligenceTopics(): Promise<IntelligenceTopics> {
  return fetchJson<IntelligenceTopics>("/api/intelligence/topics");
}

export async function listAlerts(
  topic?: string,
  limit = 20,
  offset = 0
): Promise<{ total: number; limit: number; offset: number; alerts: IntelligenceAlert[] }> {
  const params = new URLSearchParams();
  if (topic) params.set("topic", topic);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return fetchJson(`/api/intelligence/alerts?${params.toString()}`);
}

export async function listBriefings(
  topic?: string,
  limit = 20,
  offset = 0
): Promise<{ total: number; limit: number; offset: number; briefings: IntelligenceBriefing[] }> {
  const params = new URLSearchParams();
  if (topic) params.set("topic", topic);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return fetchJson(`/api/intelligence/briefings?${params.toString()}`);
}

export async function runIntelligenceScan(topics?: string[]): Promise<{ scanned_topics: string[]; total_alerts: number }> {
  return fetchJson<{ scanned_topics: string[]; total_alerts: number }>("/api/intelligence/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topics }),
  });
}

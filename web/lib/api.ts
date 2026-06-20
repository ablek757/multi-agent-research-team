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

export interface ResearchJob {
  job_id: string;
  status: string;
  topic: string;
  created_at: string;
  logs?: string[];
  sources?: number;
  findings?: number;
  metrics?: Record<string, number>;
  outputs?: { format: string; path?: string; error?: string }[];
  state_path?: string;
  error?: string;
}

export async function startResearch(
  topic: string,
  cognitive = false,
  formats?: string[],
  depth?: number
): Promise<{ job_id: string; status: string }> {
  return fetchJson("/api/research", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, cognitive, formats, depth }),
  });
}

export async function getResearchStatus(jobId: string): Promise<ResearchJob> {
  return fetchJson<ResearchJob>(`/api/research/${encodeURIComponent(jobId)}`);
}

export async function semanticSearch(
  query: string,
  topK = 10
): Promise<{ query: string; results: { report: Report; score: number }[] }> {
  return fetchJson("/api/memory/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: topK }),
  });
}

export async function getRelatedReports(
  reportId: string,
  topK = 10
): Promise<{ reports: { report: Report; score: number }[] }> {
  return fetchJson(`/api/reports/${encodeURIComponent(reportId)}/related?top_k=${topK}`);
}

export interface StyleProfile {
  language: string;
  paragraph_length: string;
  citation_density: string;
  structure_preference: string;
  transition_words: string[];
  critical_intensity: number;
  tone: string;
  custom_notes: string;
  sample_count: number;
}

export async function getStyleProfile(): Promise<StyleProfile> {
  return fetchJson<StyleProfile>("/api/style/profile");
}

export async function learnStyle(payload: {
  original?: string;
  revised?: string;
  feedback?: string;
}): Promise<StyleProfile> {
  return fetchJson<StyleProfile>("/api/style/learn", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function listOutputFormats(): Promise<{ formats: string[] }> {
  return fetchJson<{ formats: string[] }>("/api/formats");
}

// ---------------------------------------------------------------------------
// Workbench API
// ---------------------------------------------------------------------------

export interface WorkbenchSession {
  id: string;
  topic: string;
  status: string;
  cognitive: boolean;
  created_at: string;
  updated_at: string;
  parent_id?: string;
  fork_event_id?: string;
  snapshots: Record<string, unknown>;
  intervention_queue: unknown[];
  metadata: Record<string, unknown>;
  graph?: WorkbenchGraph;
}

export interface WorkbenchGraph {
  nodes: WorkbenchNode[];
  edges: WorkbenchEdge[];
  session_id: string;
  status: string;
}

export interface WorkbenchNode {
  id: string;
  label: string;
  kind: string;
  payload: Record<string, unknown>;
}

export interface WorkbenchEdge {
  source: string;
  target: string;
  type: string;
}

export interface TraceEvent {
  id: string;
  session_id: string;
  type: string;
  timestamp: string;
  payload: Record<string, unknown>;
  parent_id?: string;
  node_id?: string;
  agent?: string;
}

export async function startWorkbenchSession(
  topic: string,
  cognitive = true
): Promise<{ session_id: string; status: string; topic: string }> {
  return fetchJson("/api/workbench/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, cognitive }),
  });
}

export async function listWorkbenchSessions(): Promise<{ sessions: WorkbenchSession[] }> {
  return fetchJson("/api/workbench/sessions");
}

export async function getWorkbenchSession(sessionId: string): Promise<WorkbenchSession> {
  return fetchJson(`/api/workbench/sessions/${encodeURIComponent(sessionId)}`);
}

export async function getWorkbenchGraph(sessionId: string): Promise<WorkbenchGraph> {
  return fetchJson(`/api/workbench/sessions/${encodeURIComponent(sessionId)}/graph`);
}

export function subscribeWorkbenchEvents(
  sessionId: string,
  onEvent: (event: TraceEvent) => void
): () => void {
  const eventSource = new EventSource(
    `${API_BASE}/api/workbench/sessions/${encodeURIComponent(sessionId)}/events`
  );
  eventSource.onmessage = (message) => {
    try {
      const data = JSON.parse(message.data);
      if (data.type === "heartbeat") return;
      onEvent(data as TraceEvent);
    } catch {
      // ignore malformed events
    }
  };
  return () => eventSource.close();
}

export async function sendWorkbenchIntervention(
  sessionId: string,
  action: string,
  payload: Record<string, unknown> = {}
): Promise<{ session_id: string; action: string; queued: boolean }> {
  return fetchJson(`/api/workbench/sessions/${encodeURIComponent(sessionId)}/intervene`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, payload }),
  });
}

export async function forkWorkbenchSession(
  sessionId: string,
  eventId: string,
  topic?: string
): Promise<{ session_id: string; parent_id: string; fork_event_id: string; status: string }> {
  return fetchJson(`/api/workbench/sessions/${encodeURIComponent(sessionId)}/fork`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_id: eventId, topic }),
  });
}

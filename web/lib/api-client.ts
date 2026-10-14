import { useCallback, useRef } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Optional bearer for AUTH_ENABLED deployments. NEXT_PUBLIC_* is shipped to the browser,
// so only set this to a short-lived or demo-scoped token.
const API_TOKEN = process.env.NEXT_PUBLIC_API_TOKEN;

export interface Telemetry {
  request_id: string;
  intent: string;
  tables: string[];
  columns_kept: string[];
  tokens_full_est: number;
  tokens_pruned_est: number;
  reduction_pct: number;
  latency_ms: { total: number; router: number; prune: number; llm: number; db: number };
  ast_verdict: string;
  attempts: number;
  /** Where the SQL came from: a saved demo answer, an earlier answer reused, or the model. */
  source?: "example" | "cache" | "model";
}

export interface EmailDraft {
  to_role: string;
  subject: string;
  body: string;
  needs_approval: boolean;
}

export interface GtmTrigger {
  type: string;
  owner: string;
  due_in_days: number;
  reason: string;
}

export interface Actions {
  email_draft: EmailDraft | null;
  cs_tags: string[];
  gtm_triggers: GtmTrigger[];
}

export interface QueryResponse {
  question: string;
  sql_query: string;
  result: string;
  timestamp: string;
  success: boolean;
  execution_time: number | null;
  request_id: string | null;
  telemetry: Telemetry | null;
  actions: Actions | null;
}

export interface ErrorBody {
  error: {
    code: string;
    message: string;
    details: { field?: string; code?: string; message?: string }[];
    requestId: string;
    timestamp: string;
  };
}

export class ApiError extends Error {
  code: string;
  requestId?: string;
  constructor(code: string, message: string, requestId?: string) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.requestId = requestId;
  }
}

export type ActionKey = "email_draft" | "cs_tags" | "gtm_triggers";

export interface ApproveRequest {
  request_id: string;
  action_key: ActionKey;
  decision: "approve" | "reject";
}

export interface ApproveResponse {
  status: string;
  decision: "approve" | "reject";
  request_id: string;
  action_key: ActionKey;
  actor: string;
}

function headers(): HeadersInit {
  return {
    "Content-Type": "application/json",
    ...(API_TOKEN ? { Authorization: `Bearer ${API_TOKEN}` } : {}),
  };
}

async function toApiError(res: Response): Promise<ApiError> {
  const body = (await res.json().catch(() => null)) as ErrorBody | null;
  return new ApiError(body?.error?.code ?? "UNKNOWN", body?.error?.message ?? `HTTP ${res.status}`, body?.error?.requestId);
}

export async function postQuery(question: string, signal?: AbortSignal): Promise<QueryResponse> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/v1/query`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ question }),
      signal,
    });
  } catch {
    if (signal?.aborted) throw new ApiError("CANCELLED", "Query cancelled");
    throw new ApiError("NETWORK_ERROR", "Cannot reach the API. Check that it is running.");
  }
  if (!res.ok) throw await toApiError(res);
  return res.json();
}

export async function approveAction(body: ApproveRequest): Promise<ApproveResponse> {
  const res = await fetch(`${API_BASE}/api/v1/actions/approve`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw await toApiError(res);
  return res.json();
}

export interface HistoryItem extends QueryResponse {}

export async function fetchHistory(limit = 10, cursor?: string): Promise<{ items: HistoryItem[]; next_cursor: string | null; total: number }> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) params.set("cursor", cursor);
  const res = await fetch(`${API_BASE}/api/v1/history?${params}`, { headers: headers() });
  if (!res.ok) throw await toApiError(res);
  return res.json();
}

/**
 * Runs a query. Starting a new run aborts the previous in-flight one, and
 * `cancel` aborts the current run (surfaced as ApiError code CANCELLED).
 */
export function useRunQuery() {
  const controllerRef = useRef<AbortController | null>(null);
  const mutation = useMutation<QueryResponse, ApiError, string>({
    mutationFn: (question: string) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      return postQuery(question, controller.signal);
    },
  });
  const cancel = useCallback(() => controllerRef.current?.abort(), []);
  return { ...mutation, cancel };
}

export function useApproveAction() {
  return useMutation<ApproveResponse, ApiError, ApproveRequest>({
    mutationFn: approveAction,
  });
}

export interface AppConfig {
  demo_mode: boolean;
  tables: string[];
  examples: string[];
  llm_model: string;
}

export async function fetchConfig(): Promise<AppConfig> {
  const res = await fetch(`${API_BASE}/api/v1/config`, { headers: headers() });
  if (!res.ok) throw await toApiError(res);
  return res.json();
}

// Refetch so the banner follows the API when its mode changes (e.g. DEMO_MODE restarted).
export function useAppConfig() {
  return useQuery<AppConfig, ApiError>({
    queryKey: ["app-config"],
    queryFn: fetchConfig,
    staleTime: 10_000,
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
  });
}

export type ColumnStat =
  | { column: string; kind: "numeric"; min: number | string | null; max: number | string | null; avg: number | null }
  | { column: string; kind: "text"; distinct: number; top: [string | number | null, number][] };

export interface TableProfile {
  name: string;
  rows: number;
  columns: string[];
  sample_columns: string[];
  sample: (string | number | boolean | null)[][];
  stats: ColumnStat[];
}

export interface DataSample {
  demo_mode: boolean;
  tables: TableProfile[];
}

export async function fetchSample(rows = 5): Promise<DataSample> {
  const res = await fetch(`${API_BASE}/api/v1/sample?rows=${rows}`, { headers: headers() });
  if (!res.ok) throw await toApiError(res);
  return res.json();
}

export function useDataSample() {
  return useQuery<DataSample, ApiError>({
    queryKey: ["data-sample"],
    queryFn: () => fetchSample(5),
    staleTime: 30_000,
  });
}

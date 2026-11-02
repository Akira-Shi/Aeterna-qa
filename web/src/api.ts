// All calls go through /api (Vite dev proxy -> http://127.0.0.1:8000). The gate metric is never shown.
export const API_BASE = "/api";

export interface ColumnProfile { name: string; dtype: string; missing: number; distinct: number }
export interface Dataset { dataset_id: string; filename: string; rows: number; n_columns: number; columns: ColumnProfile[] }

export interface TaskBody {
  dataset_id: string;
  target: string;
  task_type: "binary" | "multiclass" | "regression";
  positive_label: string | null;
  model_family: "linear" | "tree_ensemble" | "distance" | "neural";
  id_columns: string[];
  drop_columns: string[];
  planner: "rule" | "groq";
}

export interface JobStarted { job_id: string; status: string; planner: string; warnings: string[] }
export interface JobStatus {
  job_id: string;
  status: "queued" | "running" | "done" | "failed" | "planner_unavailable" | "interrupted" | string;
  progress: { iteration: number; of: number };
  planner: string;
  message: string | null;
  warnings: string[];
  can_rerun_with_rule: boolean;
  stage2: { suggested: boolean; approved: boolean };
}

export interface Repair {
  iteration: number;
  column: string | null;
  operation: string | null;
  reason: string | null;
  delta: number | null;
  se: number | null;
  threshold: number | null;
  status: string;
  error: string | null;
  verdict: { code: string; text: string } | null;
  plain_fix: string | null;
  chain_id?: number | null;
}
export interface Stage1 {
  mode: "gated" | "detection_only" | string;
  headline?: string;
  n_committed?: number;
  n_evaluations?: number;
  n_chains?: number;
  repairs?: Repair[];
  gate?: string;
}

export interface Step {
  index: number;
  stage: string;
  columns: string[];
  method: string;
  rule_id: string;
  reason: string;
  alternative: string;
  allowed_methods: string[];
  editable: boolean;
}
export interface Suggest {
  steps: Step[];
  fallback: boolean;
  fallback_note: string | null;
  compare_note: string | null;
  final: string;
  approved: boolean;
}
export interface Decision { step: number; action: "accept" | "edit"; method?: string }

export interface ArtifactFile { name: string; available: boolean; url: string; media_type: string }
export interface Preview {
  columns: string[];
  row_labels: number[];
  n_changed_rows_total: number;
  changed_cells_per_row: number[];
  before: Record<string, unknown>[];
  after: Record<string, unknown>[];
  rows_dropped: number;
}
export interface Artifacts { files: ArtifactFile[]; preview: Preview; note: string; pipeline_note: string }

export class ApiError extends Error {
  messages: string[];
  status: number;
  constructor(status: number, messages: string[]) {
    super(messages.join(" "));
    this.status = status;
    this.messages = messages;
  }
}

// Turns FastAPI's 4xx/422 `detail` (string | {errors, warnings} | [{msg, loc}]) into plain messages.
function detailMessages(detail: unknown, fallback: string): string[] {
  if (typeof detail === "string") return [detail];
  if (Array.isArray(detail)) {
    return detail.map((d) => {
      const o = d as { msg?: string; loc?: unknown[] };
      const where = Array.isArray(o.loc) ? o.loc.filter((x) => x !== "body").join(".") : "";
      return where ? `${where}: ${o.msg ?? "invalid"}` : (o.msg ?? "invalid");
    });
  }
  if (detail && typeof detail === "object" && Array.isArray((detail as { errors?: unknown }).errors)) {
    return ((detail as { errors: unknown[] }).errors).map(String);
  }
  return [fallback];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(API_BASE + path, init);
  } catch {
    throw new ApiError(0, ["Cannot reach the API. Start it with `python -m api` from the aeterna_qa folder."]);
  }
  if (!res.ok) {
    let body: { detail?: unknown } = {};
    try { body = await res.json(); } catch { /* not JSON */ }
    throw new ApiError(res.status, detailMessages(body.detail, `Request failed (${res.status}).`));
  }
  return (await res.json()) as T;
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "content-type": "application/json" },
  body: JSON.stringify(body),
});

export const uploadDataset = (file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return request<Dataset>("/datasets", { method: "POST", body: fd });
};
export const startStage1 = (b: TaskBody) => request<JobStarted>("/jobs/stage1", json("POST", b));
export const rerun = (id: string) => request<JobStarted>(`/jobs/${id}/rerun`, json("POST", { planner: "rule" }));
export const getJob = (id: string) => request<JobStatus>(`/jobs/${id}`);
export const getStage1 = (id: string) => request<Stage1>(`/jobs/${id}/stage1`);
export const suggest = (id: string) => request<Suggest>(`/jobs/${id}/stage2/suggest`, { method: "POST" });
export const approve = (id: string, decisions: Decision[]) =>
  request<unknown>(`/jobs/${id}/stage2/approve`, json("POST", { decisions }));
export const getArtifacts = (id: string) => request<Artifacts>(`/jobs/${id}/artifacts`);
export const artifactHref = (f: ArtifactFile) => API_BASE + f.url;

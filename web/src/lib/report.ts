// The report the API returns (GET /api/v1/kyc/report/{id}), and how the UI words its fields.
// Every field is optional on purpose: a failed assessment's report holds only `error`.

export type Tier = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface Citation {
  knowledge_base?: string;
  document?: string;
  article?: string;
  snippet_id?: string;
}

export interface Dimension {
  score?: number;
  tier?: string;
  weight?: string;
}

export interface AuditTrace {
  task_id?: string;
  agents_invoked?: string[];
  retrieval_queries?: number;
  data_backend?: string;
  agent_sources?: Record<string, string | null>;
  fallbacks?: Record<string, string[]>;
  [status: `${string}_status`]: string | undefined;
}

export interface Report {
  report_id?: string;
  generated_at?: string;
  error?: string;
  status?: string;
  explanation?: string;
  explanation_source?: string;
  entity?: { name?: string; type?: string; jurisdiction?: string };
  risk_summary?: {
    overall_risk_tier?: string;
    overall_risk_score?: number;
    tier_basis?: string;
    sanctions_screening?: string;
    edd_required?: boolean;
    decision_recommendation?: string;
  };
  dimension_scores?: Record<string, Dimension>;
  key_findings?: string[];
  regulatory_triggers?: { rule?: string; citation?: Citation | null }[];
  recommended_actions?: string[];
  audit_trace?: AuditTrace;
  timeline?: { step?: string; time?: string }[];
  total_latency_seconds?: number;
}

export const AGENTS = [
  { id: "identity", name: "Identity", does: "Customer record and identity documents" },
  { id: "screening", name: "Screening", does: "Sanctions, PEP and adverse media" },
  { id: "corporate", name: "Corporate", does: "Registry record and beneficial owners" },
  { id: "transaction", name: "Transaction", does: "Transaction patterns" },
  { id: "compliance", name: "Compliance", does: "Scores, tier, citations and explanation" },
] as const;

export type AgentId = (typeof AGENTS)[number]["id"];

export const DIMENSIONS = [
  { key: "identity", label: "Identity" },
  { key: "screening", label: "Screening" },
  { key: "corporate_ubo", label: "Corporate and ownership" },
  { key: "regulatory", label: "Regulatory" },
  { key: "transaction", label: "Transaction" },
] as const;

const TIER_BASIS: Record<string, string> = {
  score: "Score band",
  sanctions_match: "Sanctions hold",
};

const SANCTIONS: Record<string, string> = {
  potential_match: "Potential match",
  no_match: "No match",
  not_run: "Did not run",
};

// Where an agent's result came from (src/argus/agents/provenance.py).
const SOURCES: Record<string, string> = {
  computed: "Computed from the data plane",
  fallback: "Fallback: a service was unavailable",
  demo_profile: "Recorded demo profile",
  unavailable: "Agent unavailable",
};

const EXPLANATION_SOURCES: Record<string, string> = {
  model: "Written by the language model from the findings",
  fallback: "Written from a template: no language model answered",
};

export const NOT_REPORTED = "Not reported";

export function tierBasisLabel(value?: string): string {
  return (value && TIER_BASIS[value]) || NOT_REPORTED;
}

export function sanctionsLabel(value?: string): string {
  return (value && SANCTIONS[value]) || NOT_REPORTED;
}

export function eddLabel(value?: boolean): string {
  if (value === true) return "Required";
  if (value === false) return "Not required by a rule";
  return NOT_REPORTED;
}

export function sourceLabel(value?: string | null): string {
  return (value && SOURCES[value]) || NOT_REPORTED;
}

export function explanationSourceLabel(value?: string): string {
  return (value && EXPLANATION_SOURCES[value]) || NOT_REPORTED;
}

/** The risk tier in lower case, for the colour token; anything unexpected is `unknown`. */
export function tierTone(tier?: string): "low" | "medium" | "high" | "critical" | "unknown" {
  const tone = tier?.toLowerCase();
  return tone === "low" || tone === "medium" || tone === "high" || tone === "critical"
    ? tone
    : "unknown";
}

/** A score as a bar width: clamped to 0–100. */
export function barPercent(score?: number): number {
  return Math.max(0, Math.min(100, Number.isFinite(score) ? Number(score) : 0));
}

export interface Evidence {
  grounded: boolean;
  text: string;
}

/** Whether the knowledge bases answered, or which tools fell back, in one sentence. */
export function evidenceSummary(trace: AuditTrace = {}): Evidence {
  const queries = trace.retrieval_queries;
  const fallbacks = Object.entries(trace.fallbacks ?? {}).filter(([, tools]) => tools.length);
  if (fallbacks.length) {
    const named = fallbacks.map(([agent, tools]) => `${agent} (${tools.join(", ")})`);
    return { grounded: false, text: `Fallback used: ${named.join(", ")}` };
  }
  if (typeof queries === "number" && queries > 0) {
    const backend = trace.data_backend ?? "unknown";
    const searches = queries === 1 ? "1 search" : `${queries} searches`;
    return { grounded: true, text: `Knowledge bases answered ${searches} (${backend} data)` };
  }
  return { grounded: false, text: "No knowledge-base search answered" };
}

/** The citation's parts that are present, each with its label. */
export function citationParts(citation?: Citation | null): { label: string; value: string }[] {
  return [
    { label: "Knowledge base", value: citation?.knowledge_base },
    { label: "Document", value: citation?.document },
    { label: "Article", value: citation?.article },
  ].filter((part): part is { label: string; value: string } => Boolean(part.value));
}

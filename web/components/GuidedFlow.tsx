"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { QueryResponse } from "@/lib/api-client";
import { fadeUp, stagger } from "@/lib/motion";
import { parseResultRepr } from "@/lib/parse-result";

const INTENT_HELP: Record<string, string> = {
  aggregate: "It needs a summary (average, sum or count) over rows.",
  filter: "It needs the rows that match a condition.",
  rank: "It needs the top or bottom rows.",
  trend: "It needs values grouped by a category.",
  join: "It needs data combined from more than one table.",
  metadata: "It asks about the database itself.",
};

export interface GuideStep {
  title: string;
  detail: string;
}

/** Plain-language steps derived from one response's telemetry. No extra model calls. */
export function buildSteps(response: QueryResponse): GuideStep[] {
  const t = response.telemetry;
  const rows = parseResultRepr(response.result);
  return [
    {
      title: "Understood the question",
      detail: t ? `Read as a "${t.intent}" question. ${INTENT_HELP[t.intent] ?? ""}`.trim() : "Intent not recorded.",
    },
    {
      title: "Picked the relevant tables",
      detail: t
        ? `Used ${t.tables.join(", ") || "no tables"}. The model saw ${t.reduction_pct.toFixed(0)}% less schema than the full database.`
        : "Schema not recorded.",
    },
    {
      title: "Wrote the SQL",
      detail: t
        ? t.source === "example"
          ? "Used a saved example query, so no model call was needed."
          : t.source === "cache"
            ? "Reused an earlier answer, so no model call was needed."
            : `${t.attempts} attempt${t.attempts === 1 ? "" : "s"}. A retry happens only when a safety or subject check fails.`
        : "Attempts not recorded.",
    },
    {
      title: "Checked it is safe",
      detail: t
        ? t.ast_verdict === "pass"
          ? "Read-only SELECT that only touches tables in your database."
          : `Blocked: ${t.ast_verdict}.`
        : "Safety verdict not recorded.",
    },
    {
      title: "Ran it",
      detail: `${t ? `Database time ${t.latency_ms.db.toFixed(0)} ms. ` : ""}${
        rows ? `${rows.length} row${rows.length === 1 ? "" : "s"} returned.` : "Result returned as raw text."
      }`,
    },
  ];
}

const PENDING_TITLES = [
  "Understood the question",
  "Picked the relevant tables",
  "Wrote the SQL",
  "Checked it is safe",
  "Ran it",
];

export function GuidedFlow({ response, demoMode }: { response: QueryResponse | null; demoMode: boolean }) {
  const reduce = useReducedMotion();
  const steps = response
    ? buildSteps(response)
    : PENDING_TITLES.map((title) => ({ title, detail: "Run a question to see this step." }));

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted">
        {demoMode
          ? "Demo data: student grades. Set DEMO_MODE=false to use your own database."
          : "Your own database. Each step below shows what happened to your question."}
      </p>
      <motion.ol variants={stagger(reduce)} initial="hidden" animate="show" className="flex flex-col gap-2">
        {steps.map((step, idx) => (
          <motion.li key={step.title} variants={fadeUp} className="flex gap-3 rounded-panel border border-edge bg-surface p-3">
            <span className="tnum flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent">
              {idx + 1}
            </span>
            <div className="flex min-w-0 flex-col gap-0.5">
              <span className="text-sm font-medium">{step.title}</span>
              <span className="text-sm text-muted">{step.detail}</span>
            </div>
          </motion.li>
        ))}
      </motion.ol>
    </div>
  );
}

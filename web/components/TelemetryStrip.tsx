"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { Telemetry } from "@/lib/api-client";

interface TelemetryStripProps {
  telemetry: Telemetry | null;
}

const STAGES: { key: keyof Telemetry["latency_ms"]; label: string }[] = [
  { key: "router", label: "Router" },
  { key: "prune", label: "Prune" },
  { key: "llm", label: "LLM" },
  { key: "db", label: "DB" },
];

export function TelemetryStrip({ telemetry }: TelemetryStripProps) {
  const reduce = useReducedMotion();

  if (!telemetry) {
    return <p className="text-sm text-muted">Latency and pruning stats appear after a run.</p>;
  }

  const { latency_ms: latency } = telemetry;
  const stageTotal = STAGES.reduce((sum, s) => sum + latency[s.key], 0) || 1;

  return (
    <div className="flex flex-col gap-3 text-sm">
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 tnum sm:grid-cols-4">
        <div>
          <dt className="text-xs text-muted">Total</dt>
          <dd>{latency.total.toFixed(0)} ms</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Schema kept</dt>
          <dd>{telemetry.reduction_pct.toFixed(0)}% smaller</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">AST check</dt>
          <dd className={telemetry.ast_verdict === "pass" ? "text-success" : "text-danger"}>{telemetry.ast_verdict}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Attempts</dt>
          <dd>{telemetry.attempts}</dd>
        </div>
      </dl>

      <ul className="flex flex-col gap-2" aria-label="Latency by stage">
        {STAGES.map((stage) => {
          const pct = (latency[stage.key] / stageTotal) * 100;
          return (
            <li key={stage.key} className="grid grid-cols-[3.5rem_1fr_4.5rem] items-center gap-2 tnum">
              <span className="text-xs text-muted">{stage.label}</span>
              <div className="h-2 overflow-hidden rounded-full bg-edge" role="presentation">
                <motion.div
                  className="h-full rounded-full bg-accent"
                  initial={false}
                  animate={{ width: `${pct}%` }}
                  transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 300, damping: 30 }}
                />
              </div>
              <span className="text-right text-xs">{latency[stage.key].toFixed(0)} ms</span>
            </li>
          );
        })}
      </ul>

      <p className="sql-mono text-xs text-muted">request {telemetry.request_id}</p>
    </div>
  );
}

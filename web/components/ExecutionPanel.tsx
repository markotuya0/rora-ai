"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import type { QueryResponse } from "@/lib/api-client";
import { ActionCards } from "./ActionCards";
import { DataTable } from "./DataTable";
import { GuidedFlow } from "./GuidedFlow";
import { DiffView } from "./DiffView";
import { SQLEditor } from "./SQLEditor";
import { TelemetryStrip } from "./TelemetryStrip";

export type ExecTab = "steps" | "sql" | "diff" | "rows";

const TABS: { id: ExecTab; label: string }[] = [
  { id: "steps", label: "Steps" },
  { id: "sql", label: "SQL" },
  { id: "diff", label: "Diff" },
  { id: "rows", label: "Rows" },
];

interface ExecutionPanelProps {
  response: QueryResponse | null;
  previousSql: string | null;
  tab: ExecTab;
  onTabChange: (tab: ExecTab) => void;
  demoMode: boolean;
}

export function ExecutionPanel({ response, previousSql, tab, onTabChange, demoMode }: ExecutionPanelProps) {
  const reduce = useReducedMotion();

  return (
    <section aria-label="Execution" className="flex min-w-0 flex-col gap-4 rounded-panel border border-edge bg-panel p-4 shadow-panel">
      <div role="tablist" aria-label="Execution views" className="flex gap-1 border-b border-edge">
        {TABS.map((t, idx) => {
          const selected = tab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              role="tab"
              id={`tab-${t.id}`}
              aria-selected={selected}
              aria-controls={`panel-${t.id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => onTabChange(t.id)}
              className={`relative min-h-11 px-3 text-sm md:min-h-0 md:py-2 ${selected ? "text-ink" : "text-muted"}`}
            >
              {t.label} <kbd className="text-xs text-muted">{idx + 1}</kbd>
              {selected && (
                <motion.span
                  layoutId="tab-indicator"
                  className="absolute inset-x-0 -bottom-px h-0.5 bg-accent"
                  transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
            </button>
          );
        })}
      </div>

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="min-w-0">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={reduce ? { duration: 0 } : { duration: 0.18 }}
          >
            {tab === "steps" && <GuidedFlow response={response} demoMode={demoMode} />}
            {tab === "sql" && <SQLEditor sql={response?.sql_query ?? null} />}
            {tab === "diff" && <DiffView before={previousSql} after={response?.sql_query ?? null} />}
            {tab === "rows" && <DataTable result={response?.result ?? null} question={response?.question} />}
          </motion.div>
        </AnimatePresence>
      </div>

      <TelemetryStrip telemetry={response?.telemetry ?? null} />

      <ActionCards key={response?.request_id ?? "none"} requestId={response?.request_id ?? null} actions={response?.actions ?? null} />
    </section>
  );
}

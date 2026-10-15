"use client";

import { diffLines } from "@/lib/diff";

interface DiffViewProps {
  before: string | null;
  after: string | null;
}

// Marks are text as well as colour so changes stay readable without colour vision.
const MARK: Record<"same" | "add" | "del", string> = { same: " ", add: "+", del: "−" };
const ROW_CLASS: Record<"same" | "add" | "del", string> = {
  same: "text-muted",
  add: "bg-accent-soft text-ink",
  del: "bg-danger/10 text-danger",
};

export function DiffView({ before, after }: DiffViewProps) {
  if (!after) {
    return <p className="text-sm text-muted">Nothing to compare yet.</p>;
  }
  if (!before) {
    return <p className="text-sm text-muted">Run a second question to see how its SQL changed from this one.</p>;
  }

  const lines = diffLines(before, after);
  const changed = lines.some((l) => l.kind !== "same");

  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs text-muted">{changed ? "Changed since the previous run" : "No change since the previous run"}</p>
      <div role="table" aria-label="SQL diff" className="sql-mono overflow-x-auto rounded-panel border border-edge bg-code">
        {lines.map((line, idx) => (
          <div key={idx} role="row" className={`flex whitespace-pre px-3 ${ROW_CLASS[line.kind]}`}>
            <span role="cell" aria-hidden="true" className="w-4 shrink-0 select-none">
              {MARK[line.kind]}
            </span>
            <span role="cell">{line.text || " "}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

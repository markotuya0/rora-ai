"use client";

import { useState } from "react";

interface SQLEditorProps {
  sql: string | null;
}

export function SQLEditor({ sql }: SQLEditorProps) {
  const [copied, setCopied] = useState(false);

  if (!sql) {
    return <p className="text-sm text-muted">Run a question to see the generated SQL.</p>;
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(sql ?? "");
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted">Read-only · validated before execution</span>
        <button
          type="button"
          onClick={copy}
          className="min-h-11 rounded border border-edge px-3 text-xs md:min-h-0 md:py-1"
        >
          {copied ? "Copied" : "Copy SQL"}
        </button>
      </div>
      <pre
        aria-label="Generated SQL"
        className="sql-mono overflow-x-auto whitespace-pre rounded-panel border border-edge bg-code p-3 text-ink"
      >
        {sql}
      </pre>
    </div>
  );
}

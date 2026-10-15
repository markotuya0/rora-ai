"use client";

import type { RefObject } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { useElapsed } from "@/hooks/useElapsed";
import { fadeUp, stagger } from "@/lib/motion";

// Questions the demo data can answer; shown when the prompt is empty.
export const EXAMPLE_QUESTIONS = [
  "Average score per subject",
  "Top 3 students in Math",
  "Who scored below 70?",
  "How many students got an A?",
];

interface PromptPanelProps {
  value: string;
  onChange: (value: string) => void;
  onRun: () => void;
  onCancel: () => void;
  running: boolean;
  intent?: string;
  tables?: string[];
  inputRef?: RefObject<HTMLTextAreaElement>;
  examples?: string[];
  placeholder?: string;
}

export function PromptPanel({
  value, onChange, onRun, onCancel, running, intent, tables, inputRef, examples = EXAMPLE_QUESTIONS,
  placeholder = "e.g. Average score per subject",
}: PromptPanelProps) {
  const canRun = value.trim().length > 0 && !running;
  const seconds = useElapsed(running);
  const reduce = useReducedMotion();

  function onKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter" && canRun) {
      event.preventDefault();
      onRun();
    }
  }

  return (
    <section aria-labelledby="prompt-heading" className="flex flex-col gap-3 rounded-panel border border-edge bg-panel p-4 shadow-panel">
      <div className="flex items-center justify-between gap-2">
        <h2 id="prompt-heading" className="text-sm font-semibold">
          Ask a question
        </h2>
        {intent && (
          <span className="rounded-full bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent tnum" data-testid="intent-badge">
            {intent}
          </span>
        )}
      </div>

      <label htmlFor="prompt-input" className="sr-only">
        Natural language question
      </label>
      <textarea
        id="prompt-input"
        ref={inputRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        rows={4}
        placeholder={placeholder}
        className="w-full resize-y rounded-panel border border-edge bg-surface p-3 text-sm text-ink placeholder:text-muted"
      />

      {!value.trim() && examples.length > 0 && (
        <motion.ul aria-label="Example questions" variants={stagger(reduce, 0.04)} initial="hidden" animate="show" className="flex flex-col gap-2">
          {examples.map((q) => (
            <motion.li key={q} variants={fadeUp}>
              <button
                type="button"
                onClick={() => onChange(q)}
                className="min-h-11 w-full rounded-panel border border-edge px-3 text-left text-sm text-ink md:min-h-0 md:py-1.5"
              >
                {q}
              </button>
            </motion.li>
          ))}
        </motion.ul>
      )}

      {tables && tables.length > 0 && (
        <ul aria-label="Tables used" className="flex flex-wrap gap-1.5">
          {tables.map((t) => (
            <li key={t} className="sql-mono rounded border border-edge px-1.5 py-0.5 text-muted">
              {t}
            </li>
          ))}
        </ul>
      )}

      <div className="flex items-center gap-2">
        {running ? (
          <button
            type="button"
            onClick={onCancel}
            className="min-h-11 flex-1 rounded-panel border border-danger px-4 text-sm font-medium text-danger md:min-h-0"
          >
            Stop <kbd className="ml-1 text-xs text-muted">⌘.</kbd>
          </button>
        ) : (
          <motion.button
            type="button"
            onClick={onRun}
            disabled={!canRun}
            whileTap={canRun && !reduce ? { scale: 0.98 } : undefined}
            transition={{ duration: 0.12 }}
            className="min-h-11 flex-1 rounded-panel bg-accent px-4 text-sm font-semibold text-surface transition-opacity disabled:opacity-40 md:min-h-0"
          >
            Run query <kbd className="ml-1 text-xs opacity-75">⌘↵</kbd>
          </motion.button>
        )}
      </div>
      <p className="text-xs text-muted" role="status" aria-live="polite">
        {running
          ? `Running… ${seconds}s${seconds >= 10 ? ". The local model is slow; this can take 30s or more." : ""}`
          : "Press / to focus the question."}
      </p>
    </section>
  );
}

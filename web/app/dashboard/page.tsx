"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { fadeUp, transition } from "@/lib/motion";
import { ExecutionPanel, type ExecTab } from "@/components/ExecutionPanel";
import { PromptPanel } from "@/components/PromptPanel";
import { useAppConfig, useDataSample, useRunQuery, type QueryResponse } from "@/lib/api-client";
import { DataSample } from "@/components/DataSample";
import { Disclosure } from "@/components/Disclosure";
import { useKeyboardShortcuts, type Shortcut } from "@/hooks/useKeyboardShortcuts";

export default function DashboardPage() {
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [previousSql, setPreviousSql] = useState<string | null>(null);
  const [tab, setTab] = useState<ExecTab>("steps");
  const config = useAppConfig();
  const sample = useDataSample();
  const reduce = useReducedMotion();
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const responseRef = useRef<QueryResponse | null>(null);
  const { mutate, isPending, error, cancel } = useRunQuery();

  const onRun = useCallback(() => {
    const trimmed = question.trim();
    if (!trimmed || isPending) return;
    mutate(trimmed, {
      onSuccess: (next) => {
        // Diff compares against the previous successful run in this session.
        setPreviousSql(responseRef.current?.sql_query ?? null);
        responseRef.current = next;
        setResponse(next);
      },
    });
  }, [question, isPending, mutate]);

  const shortcuts = useMemo<Shortcut[]>(
    () => [
      { key: "/", handler: () => inputRef.current?.focus() },
      { key: "1", handler: () => setTab("steps") },
      { key: "2", handler: () => setTab("sql") },
      { key: "3", handler: () => setTab("diff") },
      { key: "4", handler: () => setTab("rows") },
      { key: ".", mod: true, handler: () => cancel() },
    ],
    [cancel],
  );
  useKeyboardShortcuts(shortcuts);

  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-7xl items-center justify-between border-b border-edge px-4 py-3">
        <h1 className="text-base font-semibold">RORA ops console</h1>
      </header>

      <div className="mx-auto max-w-7xl px-4 pt-4">
        <ModeBanner config={config.data} loading={config.isLoading} failed={config.isError} />
      </div>

      <section aria-label="Your data" className="mx-auto max-w-7xl px-4 pt-4">
        <Disclosure title="Your data: what is in the database">
          <DataSample data={sample.data} loading={sample.isLoading} failed={sample.isError} />
        </Disclosure>
      </section>

      <main className="mx-auto grid max-w-7xl gap-4 p-4 md:grid-cols-[minmax(280px,360px)_minmax(0,1fr)] md:items-start">
        <div className="flex flex-col gap-4">
          <PromptPanel
            value={question}
            onChange={setQuestion}
            onRun={onRun}
            onCancel={cancel}
            running={isPending}
            intent={response?.telemetry?.intent}
            tables={response?.telemetry?.tables}
            inputRef={inputRef}
            examples={config.data?.examples ?? []}
            placeholder={config.data?.demo_mode === false ? "Ask a question about your data" : undefined}
          />

          <AnimatePresence initial={false}>
            {error && (
              <motion.p
                key={error.message + (error.requestId ?? "")}
                role="alert"
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={transition(reduce)}
                className="rounded-panel border border-danger/40 bg-danger/10 p-3 text-sm text-danger"
              >
                {error.code === "CANCELLED" ? "Query cancelled." : error.message}
                {error.requestId && <span className="sql-mono ml-2 text-xs">({error.requestId})</span>}
              </motion.p>
            )}
          </AnimatePresence>
        </div>

        <ExecutionPanel
          response={response}
          previousSql={previousSql}
          tab={tab}
          onTabChange={setTab}
          demoMode={config.data?.demo_mode ?? true}
        />
      </main>
    </div>
  );
}

function ModeBanner({
  config,
  loading,
  failed,
}: {
  config: { demo_mode: boolean; tables: string[] } | undefined;
  loading: boolean;
  failed: boolean;
}) {
  if (failed) {
    return (
      <p role="alert" className="rounded-panel border border-danger/40 bg-danger/10 p-3 text-sm text-danger">
        Can&apos;t reach the API. Check that it is running, then reload.
      </p>
    );
  }
  if (loading || !config) return null;
  return (
    <motion.p
      variants={fadeUp}
      initial="hidden"
      animate="show"
      className="rounded-panel border border-edge bg-panel p-3 text-sm text-muted"
    >
      {config.demo_mode
        ? "Demo mode: answering from bundled student grades. To use your own database, set DEMO_MODE=false."
        : `Your database. Tables you can ask about: ${config.tables.join(", ") || "none found"}.`}
    </motion.p>
  );
}

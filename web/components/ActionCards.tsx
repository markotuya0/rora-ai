"use client";

import { useState } from "react";
import { useApproveAction, type ActionKey, type Actions } from "@/lib/api-client";

interface ActionCardsProps {
  requestId: string | null;
  actions: Actions | null;
}

type Decision = "approve" | "reject";

export function ActionCards({ requestId, actions }: ActionCardsProps) {
  const approve = useApproveAction();
  const [decided, setDecided] = useState<Partial<Record<ActionKey, Decision>>>({});

  const hasEmail = Boolean(actions?.email_draft);
  const hasTags = (actions?.cs_tags?.length ?? 0) > 0;
  const hasTriggers = (actions?.gtm_triggers?.length ?? 0) > 0;

  if (!requestId || !actions || !(hasEmail || hasTags || hasTriggers)) {
    return null;
  }

  function decide(key: ActionKey, decision: Decision) {
    if (!requestId) return;
    approve.mutate(
      { request_id: requestId, action_key: key, decision },
      { onSuccess: () => setDecided((prev) => ({ ...prev, [key]: decision })) },
    );
  }

  const failure = approve.error;

  return (
    <section aria-labelledby="actions-heading" className="flex flex-col gap-3">
      <h3 id="actions-heading" className="text-sm font-semibold">
        Suggested actions
      </h3>
      <p className="text-xs text-muted">Nothing runs until you approve it.</p>

      {failure && (
        <p role="alert" className="text-sm text-danger">
          {failure.message}
          {failure.requestId && <span className="sql-mono ml-2 text-xs">({failure.requestId})</span>}
        </p>
      )}

      {hasEmail && actions?.email_draft && (
        <article className="flex flex-col gap-2 rounded-panel border border-edge bg-surface p-3">
          <header className="text-xs text-muted">Email draft to {actions.email_draft.to_role}</header>
          <p className="text-sm font-medium">{actions.email_draft.subject}</p>
          <p className="whitespace-pre-wrap text-sm text-muted">{actions.email_draft.body}</p>
          <DecisionRow pending={approve.isPending} decided={decided.email_draft} onDecide={(d) => decide("email_draft", d)} />
        </article>
      )}

      {hasTags && actions?.cs_tags && (
        <article className="flex flex-col gap-2 rounded-panel border border-edge bg-surface p-3">
          <header className="text-xs text-muted">CS tags</header>
          <ul className="flex flex-wrap gap-1.5">
            {actions.cs_tags.map((tag) => (
              <li key={tag} className="rounded-full bg-accent-soft px-2 py-0.5 text-xs text-accent">
                {tag}
              </li>
            ))}
          </ul>
          <DecisionRow pending={approve.isPending} decided={decided.cs_tags} onDecide={(d) => decide("cs_tags", d)} />
        </article>
      )}

      {hasTriggers && actions?.gtm_triggers && (
        <article className="flex flex-col gap-2 rounded-panel border border-edge bg-surface p-3">
          <header className="text-xs text-muted">GTM triggers</header>
          <ul className="flex flex-col gap-2 text-sm">
            {actions.gtm_triggers.map((t, idx) => (
              <li key={idx}>
                <span className="font-medium">{t.type}</span> · {t.owner} · due in {t.due_in_days}d
                <p className="text-xs text-muted">{t.reason}</p>
              </li>
            ))}
          </ul>
          <DecisionRow pending={approve.isPending} decided={decided.gtm_triggers} onDecide={(d) => decide("gtm_triggers", d)} />
        </article>
      )}
    </section>
  );
}

function DecisionRow({ pending, decided, onDecide }: { pending: boolean; decided?: Decision; onDecide: (d: Decision) => void }) {
  if (decided) {
    return <p className="text-xs text-muted">{decided === "approve" ? "Approved" : "Rejected"}</p>;
  }
  return (
    <div className="flex gap-2">
      <button type="button" disabled={pending} onClick={() => onDecide("approve")} className="min-h-11 flex-1 rounded-panel bg-accent px-3 text-sm font-medium text-surface disabled:opacity-40 md:min-h-0 md:py-1.5">
        Approve
      </button>
      <button type="button" disabled={pending} onClick={() => onDecide("reject")} className="min-h-11 flex-1 rounded-panel border border-edge px-3 text-sm disabled:opacity-40 md:min-h-0 md:py-1.5">
        Reject
      </button>
    </div>
  );
}

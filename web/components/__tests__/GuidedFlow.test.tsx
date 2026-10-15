import { render, screen } from "@testing-library/react";
import { GuidedFlow, buildSteps } from "@/components/GuidedFlow";
import type { QueryResponse } from "@/lib/api-client";

const RESPONSE: QueryResponse = {
  question: "Top 3 students in Math",
  sql_query: "SELECT name FROM grades WHERE subject = 'Math' LIMIT 3",
  result: "[('Aman',), ('Anshu',)]",
  timestamp: "2026-10-14T00:00:00Z",
  success: true,
  execution_time: 1.2,
  request_id: "req-1",
  telemetry: {
    request_id: "req-1",
    intent: "rank",
    tables: ["grades"],
    columns_kept: ["name", "subject"],
    tokens_full_est: 100,
    tokens_pruned_est: 20,
    reduction_pct: 80,
    latency_ms: { total: 900, router: 0, prune: 1, llm: 850, db: 12 },
    ast_verdict: "pass",
    attempts: 2,
  },
  actions: null,
};

describe("buildSteps", () => {
  it("explains each stage in plain language from the telemetry", () => {
    const steps = buildSteps(RESPONSE);
    expect(steps.map((s) => s.title)).toEqual([
      "Understood the question",
      "Picked the relevant tables",
      "Wrote the SQL",
      "Checked it is safe",
      "Ran it",
    ]);
    expect(steps[1].detail).toContain("80% less schema");
    expect(steps[2].detail).toContain("2 attempts");
    expect(steps[4].detail).toContain("2 rows returned");
  });

  it("reports a blocked safety verdict", () => {
    const steps = buildSteps({ ...RESPONSE, telemetry: { ...RESPONSE.telemetry!, ast_verdict: "reject: unknown tables" } });
    expect(steps[3].detail).toContain("Blocked: reject: unknown tables");
  });
});

describe("GuidedFlow", () => {
  it("shows pending steps before any question is run", () => {
    render(<GuidedFlow response={null} demoMode={true} />);
    expect(screen.getAllByText("Run a question to see this step.")).toHaveLength(5);
    expect(screen.getByText(/Demo data: student grades/)).toBeInTheDocument();
  });

  it("names the user's own database when demo mode is off", () => {
    render(<GuidedFlow response={RESPONSE} demoMode={false} />);
    expect(screen.getByText(/Your own database/)).toBeInTheDocument();
    expect(screen.getByText("Ran it")).toBeInTheDocument();
  });
});

describe("buildSteps source", () => {
  it("says when a saved example or reused answer skipped the model", () => {
    const example = buildSteps({ ...RESPONSE, telemetry: { ...RESPONSE.telemetry!, source: "example" } });
    expect(example[2].detail).toContain("saved example query");
    const cached = buildSteps({ ...RESPONSE, telemetry: { ...RESPONSE.telemetry!, source: "cache" } });
    expect(cached[2].detail).toContain("Reused an earlier answer");
  });
});

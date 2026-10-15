import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SQLEditor } from "@/components/SQLEditor";
import { DiffView } from "@/components/DiffView";
import { TelemetryStrip } from "@/components/TelemetryStrip";
import { ActionCards } from "@/components/ActionCards";
import { ExecutionPanel, type ExecTab } from "@/components/ExecutionPanel";
import type { QueryResponse } from "@/lib/api-client";

const RESPONSE: QueryResponse = {
  question: "q",
  sql_query: "SELECT name FROM grades",
  result: "[('Aman',)]",
  timestamp: "t",
  success: true,
  execution_time: 0.1,
  request_id: "req-9",
  telemetry: {
    request_id: "req-9",
    intent: "filter",
    tables: ["grades"],
    columns_kept: ["name"],
    tokens_full_est: 40,
    tokens_pruned_est: 10,
    reduction_pct: 75,
    latency_ms: { total: 300, router: 1, prune: 2, llm: 280, db: 9 },
    ast_verdict: "pass",
    attempts: 1,
  },
  actions: null,
};

function withClient(ui: React.ReactElement) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

describe("SQLEditor", () => {
  it("shows an empty state, then the SQL with a copy button", () => {
    const { rerender } = render(<SQLEditor sql={null} />);
    expect(screen.getByText(/Run a question to see the generated SQL/)).toBeInTheDocument();
    rerender(<SQLEditor sql="SELECT 1" />);
    expect(screen.getByLabelText(/generated sql/i)).toHaveTextContent("SELECT 1");
    expect(screen.getByRole("button", { name: /copy sql/i })).toBeInTheDocument();
  });
});

describe("DiffView", () => {
  it("explains when there is nothing to compare yet", () => {
    render(<DiffView before={null} after="SELECT 1" />);
    expect(screen.getByText(/Run a second question/)).toBeInTheDocument();
  });

  it("marks added and removed lines with text as well as colour", () => {
    render(<DiffView before={"SELECT a"} after={"SELECT b"} />);
    expect(screen.getByText("Changed since the previous run")).toBeInTheDocument();
    expect(screen.getByText("+")).toBeInTheDocument();
    expect(screen.getByText("−")).toBeInTheDocument();
  });
});

describe("TelemetryStrip", () => {
  it("shows an empty state without telemetry", () => {
    render(<TelemetryStrip telemetry={null} />);
    expect(screen.getByText(/appear after a run/)).toBeInTheDocument();
  });

  it("shows the reduction, safety verdict and stage timings", () => {
    render(<TelemetryStrip telemetry={RESPONSE.telemetry} />);
    expect(screen.getByText("75% smaller")).toBeInTheDocument();
    expect(screen.getByText("pass")).toBeInTheDocument();
    expect(screen.getByRole("list", { name: /latency by stage/i })).toHaveTextContent("LLM");
  });
});

describe("ActionCards", () => {
  it("renders nothing when there are no suggested actions", () => {
    const { container } = render(withClient(<ActionCards requestId="req-9" actions={null} />));
    expect(container).toBeEmptyDOMElement();
  });

  it("shows an approval row per suggestion and records the decision", () => {
    render(
      withClient(
        <ActionCards
          requestId="req-9"
          actions={{ email_draft: null, cs_tags: ["billing"], gtm_triggers: [] }}
        />,
      ),
    );
    expect(screen.getByText("billing")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Reject" })).toBeEnabled();
  });
});

describe("ExecutionPanel", () => {
  function Harness() {
    const [tab, setTab] = useState<ExecTab>("steps");
    return <ExecutionPanel response={RESPONSE} previousSql={null} tab={tab} onTabChange={setTab} demoMode={true} />;
  }

  it("opens on the Steps tab and switches to SQL on click", async () => {
    render(withClient(<Harness />));
    expect(screen.getByText("Understood the question")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: /sql/i }));
    // The new view mounts after the exit animation, so wait for it.
    expect(await screen.findByLabelText(/generated sql/i)).toHaveTextContent("SELECT name FROM grades");
  });
});

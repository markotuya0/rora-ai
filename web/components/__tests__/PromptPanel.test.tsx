import { fireEvent, render, screen } from "@testing-library/react";
import { PromptPanel } from "@/components/PromptPanel";

function setup(overrides: Partial<Parameters<typeof PromptPanel>[0]> = {}) {
  const props = {
    value: "",
    onChange: vi.fn(),
    onRun: vi.fn(),
    onCancel: vi.fn(),
    running: false,
    ...overrides,
  };
  render(<PromptPanel {...props} />);
  return props;
}

describe("PromptPanel", () => {
  it("disables Run while the question is empty", () => {
    setup({ value: "   " });
    expect(screen.getByRole("button", { name: /run query/i })).toBeDisabled();
  });

  it("runs on Cmd+Enter when there is a question", () => {
    const props = setup({ value: "How many orders?" });
    fireEvent.keyDown(screen.getByRole("textbox"), { key: "Enter", metaKey: true });
    expect(props.onRun).toHaveBeenCalledTimes(1);
  });

  it("does not run on Cmd+Enter while a query is in flight", () => {
    const props = setup({ value: "How many orders?", running: true });
    fireEvent.keyDown(screen.getByRole("textbox"), { key: "Enter", ctrlKey: true });
    expect(props.onRun).not.toHaveBeenCalled();
  });

  it("swaps Run for Stop while running and calls onCancel", () => {
    const props = setup({ value: "x", running: true });
    fireEvent.click(screen.getByRole("button", { name: /stop/i }));
    expect(props.onCancel).toHaveBeenCalledTimes(1);
  });

  it("reports the intent badge when provided", () => {
    setup({ value: "x", intent: "aggregate" });
    expect(screen.getByTestId("intent-badge")).toHaveTextContent("aggregate");
  });
});

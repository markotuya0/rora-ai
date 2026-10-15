import { act, fireEvent, render, screen } from "@testing-library/react";
import { PromptPanel, EXAMPLE_QUESTIONS } from "@/components/PromptPanel";

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

describe("PromptPanel example questions", () => {
  it("shows example chips when the prompt is empty and fills it on click", () => {
    const props = setup({ value: "" });
    const chip = screen.getByRole("button", { name: EXAMPLE_QUESTIONS[1] });
    fireEvent.click(chip);
    expect(props.onChange).toHaveBeenCalledWith(EXAMPLE_QUESTIONS[1]);
  });

  it("hides example chips once the prompt has text", () => {
    setup({ value: "anything" });
    expect(screen.queryByRole("list", { name: /example questions/i })).not.toBeInTheDocument();
  });
});

describe("PromptPanel elapsed status", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("counts seconds while running and adds a slow-model hint after 10s", () => {
    setup({ value: "x", running: true });
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("Running… 0s");

    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(status).toHaveTextContent("Running… 3s");
    expect(status).not.toHaveTextContent("slow");

    act(() => {
      vi.advanceTimersByTime(8000);
    });
    expect(status).toHaveTextContent(/Running… 11s.*slow/);
  });
});

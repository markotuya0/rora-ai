import { fireEvent, render, screen, within } from "@testing-library/react";
import { DataTable } from "@/components/DataTable";

const RESULT = "[(1, 'Ada', 10), (2, 'Grace', None), (3, 'Linus', 7)]";

describe("DataTable", () => {
  it("renders parsed rows with NULL for None", () => {
    render(<DataTable result={RESULT} />);
    const table = screen.getByRole("table");
    expect(within(table).getByText("Grace")).toBeInTheDocument();
    expect(within(table).getByText("NULL")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("3 of 3 rows");
  });

  it("filters rows by any cell", () => {
    render(<DataTable result={RESULT} />);
    fireEvent.change(screen.getByRole("searchbox", { name: /filter rows/i }), { target: { value: "linus" } });
    expect(screen.getByRole("status")).toHaveTextContent("1 of 3 rows");
  });

  it("sorts numerically ascending, then descending, then back to source order", () => {
    render(<DataTable result={RESULT} />);
    const header = screen.getByRole("button", { name: /col 3/i });
    fireEvent.click(header);
    let bodyRows = within(screen.getByRole("table")).getAllByRole("row").slice(1);
    expect(bodyRows[0]).toHaveTextContent("Linus");

    fireEvent.click(header);
    bodyRows = within(screen.getByRole("table")).getAllByRole("row").slice(1);
    expect(bodyRows[0]).toHaveTextContent("Ada");
  });

  it("falls back to raw text when the result is not a plain table", () => {
    render(<DataTable result="[(Decimal('1.00'),)]" />);
    expect(screen.getByText(/not a plain table/i)).toBeInTheDocument();
    expect(screen.getByText("[(Decimal('1.00'),)]")).toBeInTheDocument();
  });
});

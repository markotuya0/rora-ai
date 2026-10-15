import { render, screen, within } from "@testing-library/react";
import { DataSample } from "@/components/DataSample";
import type { DataSample as DataSampleData } from "@/lib/api-client";

const DATA: DataSampleData = {
  demo_mode: true,
  tables: [
    {
      name: "grades",
      rows: 6,
      columns: ["id", "subject", "score"],
      sample_columns: ["id", "subject", "score"],
      sample: [[1, "Math", 95], [2, null, 78]],
      stats: [
        { column: "score", kind: "numeric", min: 65, max: 95, avg: 83.83 },
        { column: "subject", kind: "text", distinct: 3, top: [["Math", 3], ["History", 2]] },
      ],
    },
  ],
};

describe("DataSample", () => {
  it("shows row counts, sample rows and column stats for each table", () => {
    render(<DataSample data={DATA} loading={false} failed={false} />);
    expect(screen.getByRole("heading", { name: "grades" })).toBeInTheDocument();
    expect(screen.getByText(/6 rows/)).toBeInTheDocument();
    const sample = screen.getByRole("table", { name: /sample rows from grades/i });
    expect(within(sample).getByText("NULL")).toBeInTheDocument();
    expect(screen.getByText(/min 65 · max 95 · avg 83.83/)).toBeInTheDocument();
    expect(screen.getByText(/3 distinct values/)).toBeInTheDocument();
    expect(screen.getByText("Math · 3")).toBeInTheDocument();
  });

  it("explains an empty database and a failed profile", () => {
    const { rerender } = render(<DataSample data={{ demo_mode: false, tables: [] }} loading={false} failed={false} />);
    expect(screen.getByText("No tables found in this database.")).toBeInTheDocument();
    rerender(<DataSample data={undefined} loading={false} failed={true} />);
    expect(screen.getByText(/Couldn't profile the database/)).toBeInTheDocument();
  });
});

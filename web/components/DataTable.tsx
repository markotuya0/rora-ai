"use client";

import { useMemo, useState } from "react";
import { parseResultRepr, type Cell } from "@/lib/parse-result";

interface DataTableProps {
  result: string | null;
  question?: string;
}

const ROW_CAP = 200;

type SortState = { col: number; dir: "asc" | "desc" } | null;

// NULLs always sort last, whichever direction is active.
function compareCells(a: Cell, b: Cell, dir: "asc" | "desc"): number {
  if (a === null || b === null) return a === b ? 0 : a === null ? 1 : -1;
  const c = typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b), undefined, { numeric: true });
  return dir === "asc" ? c : -c;
}

function toCsv(rows: Cell[][]): string {
  const esc = (v: Cell) => {
    if (v === null) return "";
    const s = String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return rows.map((r) => r.map(esc).join(",")).join("\n");
}

export function DataTable({ result, question }: DataTableProps) {
  const [filter, setFilter] = useState("");
  const [sort, setSort] = useState<SortState>(null);
  const parsed = useMemo(() => (result ? parseResultRepr(result) : null), [result]);

  const visible = useMemo(() => {
    if (!parsed) return [];
    const needle = filter.trim().toLowerCase();
    let rows = needle ? parsed.filter((r) => r.some((c) => String(c ?? "").toLowerCase().includes(needle))) : parsed;
    if (sort) {
      const { col, dir } = sort;
      rows = [...rows].sort((a, b) => compareCells(a[col], b[col], dir));
    }
    return rows;
  }, [parsed, filter, sort]);

  if (!result) {
    return <p className="text-sm text-muted">Rows appear here after a run.</p>;
  }

  if (!parsed) {
    return (
      <div className="flex flex-col gap-2">
        <p className="text-xs text-muted">This result is not a plain table, so it is shown as returned.</p>
        <pre className="sql-mono overflow-x-auto whitespace-pre-wrap rounded-panel border border-edge bg-code p-3">{result}</pre>
      </div>
    );
  }

  const width = parsed[0]?.length ?? 0;
  const capped = visible.slice(0, ROW_CAP);

  function toggleSort(col: number) {
    setSort((prev) => {
      if (!prev || prev.col !== col) return { col, dir: "asc" };
      return prev.dir === "asc" ? { col, dir: "desc" } : null;
    });
  }

  function exportCsv() {
    const blob = new Blob([toCsv(visible)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(question ?? "result").slice(0, 40).replace(/\W+/g, "-") || "result"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor="rows-filter" className="sr-only">
          Filter rows
        </label>
        <input
          id="rows-filter"
          type="search"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter rows"
          className="min-h-11 flex-1 rounded-panel border border-edge bg-surface px-3 text-sm md:min-h-0 md:py-1.5"
        />
        <button type="button" onClick={exportCsv} disabled={visible.length === 0} className="min-h-11 rounded border border-edge px-3 text-xs disabled:opacity-40 md:min-h-0 md:py-1.5">
          Export CSV
        </button>
      </div>

      <p className="text-xs text-muted tnum" role="status">
        {visible.length} of {parsed.length} rows
        {visible.length > ROW_CAP && ` · showing first ${ROW_CAP}`}
      </p>

      <div className="overflow-x-auto rounded-panel border border-edge">
        <table className="w-full text-left text-sm tnum">
          <thead className="bg-surface text-xs text-muted">
            <tr>
              {Array.from({ length: width }, (_, col) => (
                <th key={col} scope="col" className="px-3 py-2 font-medium" aria-sort={sort?.col === col ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}>
                  <button type="button" onClick={() => toggleSort(col)} className="min-h-11 md:min-h-0">
                    Col {col + 1}
                    {sort?.col === col ? (sort.dir === "asc" ? " ▲" : " ▼") : ""}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {capped.map((row, rIdx) => (
              <tr key={rIdx} className="border-t border-edge">
                {row.map((cell, cIdx) => (
                  <td key={cIdx} className="px-3 py-2 align-top">
                    {cell === null ? <span className="text-muted">NULL</span> : String(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

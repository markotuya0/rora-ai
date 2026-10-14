"use client";

import type { DataSample as DataSampleData, TableProfile } from "@/lib/api-client";

/** What is in the connected database right now. Read-only; swaps automatically when the database changes. */
export function DataSample({ data, loading, failed }: { data: DataSampleData | undefined; loading: boolean; failed: boolean }) {
  if (failed) {
    return <p className="text-sm text-muted">Couldn&apos;t profile the database. Check that the API is running.</p>;
  }
  if (loading || !data) {
    return <p className="text-sm text-muted">Profiling your data…</p>;
  }
  if (data.tables.length === 0) {
    return <p className="text-sm text-muted">No tables found in this database.</p>;
  }
  return (
    <div className="flex flex-col gap-4">
      {data.tables.map((table) => (
        <TableCard key={table.name} table={table} />
      ))}
    </div>
  );
}

function TableCard({ table }: { table: TableProfile }) {
  return (
    <article className="flex min-w-0 flex-col gap-3 rounded-panel border border-edge bg-surface p-3">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="sql-mono text-sm font-semibold">{table.name}</h3>
        <span className="tnum text-xs text-muted">
          {table.rows.toLocaleString()} row{table.rows === 1 ? "" : "s"} · {table.columns.length} column{table.columns.length === 1 ? "" : "s"}
        </span>
      </header>

      {table.sample.length > 0 && (
        <div className="overflow-x-auto rounded border border-edge">
          <table className="w-full text-left text-xs tnum">
            <caption className="sr-only">Sample rows from {table.name}</caption>
            <thead className="bg-panel text-muted">
              <tr>
                {table.sample_columns.map((c) => (
                  <th key={c} scope="col" className="px-2 py-1 font-medium">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.sample.map((row, i) => (
                <tr key={i} className="border-t border-edge">
                  {row.map((cell, j) => (
                    <td key={j} className="px-2 py-1">
                      {cell === null ? <span className="text-muted">NULL</span> : String(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ul className="flex flex-col gap-2 text-xs">
        {table.stats.map((s) => (
          <li key={s.column} className="flex flex-col gap-1">
            <span className="font-medium">{s.column}</span>
            {s.kind === "numeric" ? (
              <span className="tnum text-muted">
                min {String(s.min ?? "—")} · max {String(s.max ?? "—")} · avg {s.avg ?? "—"}
              </span>
            ) : (
              <>
                <span className="tnum text-muted">
                  {s.distinct} distinct value{s.distinct === 1 ? "" : "s"}
                </span>
                <span className="flex flex-wrap gap-1">
                  {s.top.map(([value, count]) => (
                    <span key={String(value)} className="rounded-full bg-accent-soft px-2 py-0.5 text-accent">
                      {value === null ? "NULL" : String(value)} · {count}
                    </span>
                  ))}
                </span>
              </>
            )}
          </li>
        ))}
      </ul>
    </article>
  );
}

import { diffLines } from "@/lib/diff";

describe("diffLines", () => {
  it("marks no changes when inputs match", () => {
    const out = diffLines("SELECT 1", "SELECT 1");
    expect(out).toEqual([{ kind: "same", text: "SELECT 1" }]);
  });

  it("reports added and removed lines in order", () => {
    const before = "SELECT id\nFROM users\nLIMIT 10";
    const after = "SELECT id, name\nFROM users\nWHERE active\nLIMIT 10";
    expect(diffLines(before, after)).toEqual([
      { kind: "del", text: "SELECT id" },
      { kind: "add", text: "SELECT id, name" },
      { kind: "same", text: "FROM users" },
      { kind: "add", text: "WHERE active" },
      { kind: "same", text: "LIMIT 10" },
    ]);
  });

  it("handles an empty before side", () => {
    expect(diffLines("", "A")).toEqual([
      { kind: "del", text: "" },
      { kind: "add", text: "A" },
    ]);
  });
});

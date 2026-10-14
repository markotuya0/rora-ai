import { parseResultRepr } from "@/lib/parse-result";

describe("parseResultRepr", () => {
  it("parses tuples of strings, numbers, and None", () => {
    expect(parseResultRepr("[(1, 'Ada'), (2, None)]")).toEqual([
      [1, "Ada"],
      [2, null],
    ]);
  });

  it("handles booleans, floats, negatives and escaped quotes", () => {
    expect(parseResultRepr("[(-3.5, True, 'it\\'s'), (0, False, \"say \\\"hi\\\"\")]")).toEqual([
      [-3.5, true, "it's"],
      [0, false, 'say "hi"'],
    ]);
  });

  it("returns an empty array for an empty result", () => {
    expect(parseResultRepr("[]")).toEqual([]);
  });

  it("returns null for values it does not model, so callers fall back to raw text", () => {
    expect(parseResultRepr("[(Decimal('1.00'),)]")).toBeNull();
    expect(parseResultRepr("[(datetime.date(2024, 1, 1),)]")).toBeNull();
  });

  it("returns null for input that is not a list", () => {
    expect(parseResultRepr("not a result")).toBeNull();
    expect(parseResultRepr("(1, 2)")).toBeNull();
  });

  it("returns null for trailing garbage", () => {
    expect(parseResultRepr("[(1,)] extra")).toBeNull();
  });
});

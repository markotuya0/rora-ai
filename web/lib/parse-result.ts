/**
 * The API returns `result` as a Python repr of a list of tuples, e.g.
 * "[(1, 'Ada'), (2, None)]". This parses the subset we can display safely
 * (strings, numbers, None/True/False, nested tuples/lists). Anything else
 * (Decimal(...), datetime.date(...)) returns null so the caller can fall
 * back to the raw text instead of guessing.
 */

export type Cell = string | number | boolean | null;

class ReprParser {
  private i = 0;
  constructor(private readonly src: string) {}

  done(): boolean {
    this.skipWs();
    return this.i >= this.src.length;
  }

  skipWs() {
    while (this.i < this.src.length && /\s/.test(this.src[this.i])) this.i++;
  }

  parseValue(): unknown {
    this.skipWs();
    const ch = this.src[this.i];
    if (ch === "[" || ch === "(") return this.parseSeq(ch === "[" ? "]" : ")");
    if (ch === "'" || ch === '"') return this.parseString(ch);
    const word = /^[A-Za-z_]\w*/.exec(this.src.slice(this.i));
    if (word) {
      this.i += word[0].length;
      if (word[0] === "None") return null;
      if (word[0] === "True") return true;
      if (word[0] === "False") return false;
      throw new Error(`unsupported token ${word[0]}`);
    }
    const num = /^-?\d+(\.\d+)?([eE][+-]?\d+)?/.exec(this.src.slice(this.i));
    if (num) {
      this.i += num[0].length;
      return Number(num[0]);
    }
    throw new Error(`unexpected character at ${this.i}`);
  }

  private parseSeq(close: string): unknown[] {
    this.i++; // opening bracket
    const out: unknown[] = [];
    for (;;) {
      this.skipWs();
      if (this.src[this.i] === close) {
        this.i++;
        return out;
      }
      out.push(this.parseValue());
      this.skipWs();
      if (this.src[this.i] === ",") {
        this.i++;
        continue;
      }
      if (this.src[this.i] === close) continue;
      throw new Error(`expected , or ${close} at ${this.i}`);
    }
  }

  private parseString(quote: string): string {
    this.i++;
    let out = "";
    while (this.i < this.src.length) {
      const ch = this.src[this.i++];
      if (ch === quote) return out;
      if (ch === "\\") {
        const next = this.src[this.i++];
        const escapes: Record<string, string> = { n: "\n", t: "\t", r: "\r" };
        out += escapes[next] ?? next;
      } else {
        out += ch;
      }
    }
    throw new Error("unterminated string");
  }
}

/** Returns rows as arrays of cells, or null when the text is not a plain tuple list. */
export function parseResultRepr(input: string): Cell[][] | null {
  const trimmed = input.trim();
  // db.run always returns a list of rows; a bare tuple is not a result set.
  if (!trimmed.startsWith("[")) return null;
  const parser = new ReprParser(trimmed);
  try {
    const value = parser.parseValue();
    if (!parser.done() || !Array.isArray(value)) return null;
    return value.map((row) => {
      if (!Array.isArray(row)) return [row as Cell];
      return row.map((cell) => {
        if (cell === null || typeof cell === "string" || typeof cell === "number" || typeof cell === "boolean") {
          return cell;
        }
        throw new Error("nested structure in cell");
      });
    });
  } catch {
    return null;
  }
}

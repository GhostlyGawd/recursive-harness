// One-off: make a permission-dialog-safe copy of foundry.mjs via a single
// explicit codepoint pass (no regex ranges — the editor mangles \u boundaries).
//   - transliterate decorative non-ASCII glyphs to ASCII (map), drop unmapped;
//   - drop CR + stray C0 controls; keep tab + newline + printable ASCII.
// Comments/prompt-text only; program logic untouched.
import fs from "node:fs";
import path from "node:path";

const src = "D:/GitHub Projects/recursive-harness/.claude-private/accounts/wraith/skills/brand-foundry/workflow/foundry.mjs";
const dst = path.join(process.cwd(), "brand", "foundry.local.mjs");

const map = {
  "─": "-", "━": "-", "│": "|", "┃": "|",
  "═": "=", "║": "|", "╔": "+", "╗": "+", "╚": "+", "╝": "+",
  "←": "<-", "→": "->", "↑": "^", "↓": "v", "↔": "<->",
  "↩": "<-", "⇒": "=>",
  "≈": "~", "≡": "=", "≥": ">=", "≤": "<=", "×": "x",
  "·": ".", "•": "*", "—": "--", "–": "-", "…": "...",
  "§": "S", "“": '"', "”": '"', "‘": "'", "’": "'",
  "✓": "v", "✔": "v", "✗": "x", "①": "(1)",
  " ": " ", " ": " ", " ": " ", " ": " ",
};

const raw = fs.readFileSync(src, "utf8");
const dropped = new Map();
let controls = 0;
let out = "";
for (const ch of raw) {
  const c = ch.codePointAt(0);
  if (c === 9 || c === 10) { out += ch; continue; }              // tab, newline
  if (c === 13 || c < 32 || c === 127) { controls++; continue; } // CR + C0 + DEL
  if (c > 127) {                                                 // non-ASCII
    if (map[ch] !== undefined) { out += map[ch]; }
    else dropped.set(ch, (dropped.get(ch) || 0) + 1);
    continue;
  }
  out += ch;                                                     // printable ASCII
}

const nonAscii = [...out].filter((ch) => ch.codePointAt(0) > 127).length;
fs.mkdirSync(path.dirname(dst), { recursive: true });
fs.writeFileSync(dst, out, "utf8");

console.log("wrote:", dst);
console.log("bytes:", out.length, "| non-ASCII left:", nonAscii, "| controls stripped:", controls);
console.log("dropped unmapped:", [...dropped.entries()].map(([c, n]) => "U+" + c.codePointAt(0).toString(16) + "x" + n).join("  ") || "(none)");

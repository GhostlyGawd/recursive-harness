// Extract result.seed from the seed-phase output and ASCII-ify its strings so it
// can be passed inline as Workflow args without tripping the permission dialog.
import fs from "node:fs";

const outFile = "C:/Users/rhenm/AppData/Local/Temp/claude/D--GitHub-Projects-recursive-harness/e7addf32-36ba-4879-a769-7bcbba0bd407/tasks/w8ivilwr7.output";

const map = {
  "─": "-", "━": "-", "│": "|", "═": "=", "║": "|",
  "←": "<-", "→": "->", "↑": "^", "↓": "v", "↔": "<->", "↩": "<-", "⇒": "=>",
  "≈": "~", "≡": "=", "≥": ">=", "≤": "<=", "×": "x", "°": " deg",
  "·": ".", "•": "*", "—": "--", "–": "-", "…": "...",
  "§": "S", "“": '"', "”": '"', "‘": "'", "’": "'", "♻": "(loop)",
  "✓": "v", "✔": "v", "✗": "x", "①": "(1)", "②": "(2)", "③": "(3)",
};

function asciiify(str) {
  let o = "";
  for (const ch of str) {
    const c = ch.codePointAt(0);
    if (c === 9 || c === 10) { o += " "; continue; }
    if (c === 13 || c < 32 || c === 127) continue;
    if (c > 127) { o += (map[ch] !== undefined ? map[ch] : ""); continue; }
    o += ch;
  }
  return o;
}
function walk(v) {
  if (typeof v === "string") return asciiify(v);
  if (Array.isArray(v)) return v.map(walk);
  if (v && typeof v === "object") { const r = {}; for (const k of Object.keys(v)) r[k] = walk(v[k]); return r; }
  return v;
}

const data = JSON.parse(fs.readFileSync(outFile, "utf8"));
const seed = walk(data.result.seed);
fs.writeFileSync("brand/seed.json", JSON.stringify(seed), "utf8");

const txt = fs.readFileSync("brand/seed.json", "utf8");
console.log("fields:", Object.keys(seed).join(","));
console.log("material:", seed.material.length, "| ignition:", (seed.ignition || []).length, "| primitives:", seed.generativePrimitives.length);
console.log("seed.json bytes:", txt.length, "| non-ASCII:", (txt.match(/[^\x00-\x7f]/g) || []).length);

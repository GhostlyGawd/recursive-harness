// Build the develop-phase `chosen` object from the KEPT synthesize direction
// (append-only-strata), ASCII-sanitized, so it can be baked into the script.
import fs from "node:fs";

const outFile = "C:/Users/rhenm/AppData/Local/Temp/claude/D--GitHub-Projects-recursive-harness/e7addf32-36ba-4879-a769-7bcbba0bd407/tasks/wsvl8w45y.output";
const KEY = "append-only-strata";

const map = {
  "─": "-", "━": "-", "│": "|", "═": "=", "║": "|",
  "←": "<-", "→": "->", "↑": "^", "↓": "v", "↔": "<->", "↩": "<-", "⇒": "=>",
  "≈": "~", "≡": "=", "≥": ">=", "≤": "<=", "×": "x", "°": " deg",
  "·": ".", "•": "*", "—": "--", "–": "-", "…": "...",
  "§": "S", "“": '"', "”": '"', "‘": "'", "’": "'", "♻": "(loop)",
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

const data = JSON.parse(fs.readFileSync(outFile, "utf8"));
const d = data.result.directions.find((x) => x.key === KEY);
if (!d) throw new Error("direction not found: " + KEY);

// synthesizeToDevelop (contracts.mjs): name, look<-inventedLanguage, structure, concept derived from the two soul fields.
const chosen = {
  name: asciiify(d.name),
  look: asciiify(d.inventedLanguage),
  structure: asciiify(d.structure),
  concept: asciiify(`A ${d.seedFacet} language, grown from ${d.generativePrimitive}.`),
};
fs.writeFileSync("brand/chosen.json", JSON.stringify(chosen), "utf8");
const txt = fs.readFileSync("brand/chosen.json", "utf8");
console.log("chosen:", chosen.name, "| bytes:", txt.length, "| non-ASCII:", (txt.match(/[^\x00-\x7f]/g) || []).length);

// Bake the (ASCII) seed + the landing-page content into a copy of foundry.local.mjs
// as constants, so Workflow args stay tiny and the script stays pure-ASCII/LF
// (the permission dialog rejects control chars / we keep it clean).
// Run: node brand/build-phase-script.mjs  ->  brand/foundry.seeded.mjs
import fs from "node:fs";

const foundry = fs.readFileSync("brand/foundry.local.mjs", "utf8");
const seedJson = fs.readFileSync("brand/seed.json", "utf8").trim(); // compact ASCII JSON
let chosenInject = "";
try {
  const chosenJson = fs.readFileSync("brand/chosen.json", "utf8").trim();
  chosenInject = "const BAKED_CHOSEN = " + chosenJson + ";\nif (!A.chosen) A.chosen = BAKED_CHOSEN;\n";
} catch { /* chosen.json optional — only needed for the develop phase */ }

// Outsider-legible LANDING PAGE for Recursive Harness. Same content renders in
// every direction; the real soul-material (calibration + hit/hollow marks + the
// three loops + the diff/provenance) is the hero proof. Pure ASCII.
const CONTENT = [
  "THE PRODUCT - a LANDING PAGE for Recursive Harness. A developer who has never seen it must understand it in ~5 seconds. The SAME underlying content renders in every direction; frame it in YOUR direction's own invented language.",
  "",
  "- IDENTITY: the product name 'Recursive Harness' + a small mark.",
  "- HERO HEADLINE (the promise): 'Your AI coding agent, getting measurably better at YOUR work - and able to prove it.'",
  "- SUBHEAD: 'The model's weights never change. Its repository becomes the learnable layer: every prediction is scored against reality, and every lesson is filed as a permanent, reviewed change.'",
  "",
  "- THE HERO PROOF (a real, signature widget - this is the soul; show it prominently). A calibration readout:",
  "    scored 176    hit-rate 80%    brier 0.16",
  "    claimed 0.70  ->  actual 0.76   (slightly underconfident)",
  "  and a short stack of recent predictions, each marked as a FILLED dot (hit) or a HOLLOW dot (miss), with ONE still PENDING (a hollow, dashed mark = 'unscored = debt'):",
  "    (hit)      resolve flaky test          confidence 0.80",
  "    (hit)      refactor the auth flow       confidence 0.65",
  "    (miss)     migrate the schema           confidence 0.90",
  "    (pending)  rewrite the cache layer      confidence 0.70",
  "",
  "- THREE FEATURE POINTS (the three nested loops / cadences):",
  "    1. Every task: predict -> act -> score. A stated claim, checked against what actually happened.",
  "    2. Every session: the gaps become reviewed changes - new procedures, guardrails, calibration.",
  "    3. Every month: audit, prune, and earn more autonomy - measured, never assumed.",
  "",
  "- ONE HONESTY PULL-QUOTE: 'Unscored predictions show up as debt. Anything unverifiable counts as a miss. The agent can never quietly weaken the rules that measure it.'",
  "- A PRIMARY call-to-action button ('Start the loop') and a secondary link ('See how it works').",
  "- Keep it focused: no unrelated chrome, no notification noise, no stock imagery, no emoji icons.",
].join("\n");

const anchor = 'const which = A.phase ?? "__diagnostic__";';
if (!foundry.includes(anchor)) throw new Error("anchor line not found in foundry.local.mjs");

const inject =
  "const BAKED_SEED = " + seedJson + ";\n" +
  "const BAKED_CONTENT = " + JSON.stringify(CONTENT) + ";\n" +
  chosenInject +
  "if (!A.seed) A.seed = BAKED_SEED;\n" +
  "if (!A.content) A.content = BAKED_CONTENT;\n" +
  anchor;

const out = foundry.replace(anchor, inject);

const nonAscii = (out.match(/[^\x00-\x7f]/g) || []).length;
let controls = 0;
for (const ch of out) { const c = ch.codePointAt(0); if (c === 13 || (c !== 9 && c !== 10 && (c < 32 || c === 127))) controls++; }
fs.writeFileSync("brand/foundry.seeded.mjs", out, "utf8");
console.log("wrote brand/foundry.seeded.mjs | bytes:", out.length, "| non-ASCII:", nonAscii, "| controls:", controls, "| hasBaked:", out.includes("BAKED_SEED") && out.includes("BAKED_CONTENT"));

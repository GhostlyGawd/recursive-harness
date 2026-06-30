export const meta = {
  name: "brand-foundry",
  description: "Run one autonomous phase of the brand-creation arc. The main loop chains phases across human taste-gates (a Workflow cannot prompt the user, so gates live in the main loop, not here).",
  phases: [
    { title: "seed", detail: "soul extraction BEFORE any visual: a material-cartographer maps the product's OWN material (the soil) + a references-scout WebSearches world-class craft as IGNITION (not a menu), then a soul-diviner runs the coincidence method (function-truth x material artifact -> the soulFinding) -> the generative DNA the brand grows from. The human approves/redirects the SEED before 4 expensive builds" },
    { title: "synthesize", detail: "INVENT, don't apply: a synthesis-planner spreads N (~4) ORIGINAL languages, each grown from a DIFFERENT facet of the SEED via sourceArtifact->transform->primitive -- recognizable named styles BANNED, costumes BANNED; iterable/focusable/graftable; N screen-builders each load huashu and build a REAL app screen" },
    { title: "develop", detail: "refinement-only: dial in the ONE chosen design (type/palette/density/hierarchy) -- never a new design or a new skeleton" },
    { title: "lock", detail: "token-extractor + language-codifier read the CHOSEN screens -> LANGUAGE.md + tokens.json" },
    { title: "package", detail: "brand book + identity, built from the locked LANGUAGE.md + tokens" },
    { title: "applications", detail: "one builder per surface; the brand applied across many surfaces" },
  ],
};

// -- Invoked once per autonomous phase by the main loop, with args: -----------
//   { phase: 'seed'|'synthesize'|'develop'|'lock'|'package'|'applications',
//     brief: '<one-line product brief>',
//     ...phase-specific args (see each block) }
// `seed` extracts the product's generative DNA BEFORE any visual (the soul-finding
// via the coincidence method); the main loop SHOWS the SEED to the human
// (approve/redirect), then passes it to `synthesize` as args.seed. `synthesize`
// INVENTS N original languages grown from the SEED (never selects a style).
// The human taste-gate runs in the MAIN LOOP between invocations (a Workflow
// cannot prompt the user). The SPINE (the chosen aesthetic) is the OUTPUT of this
// funnel, not an input: it EMERGES from what the human picks across synthesize
// rounds, then is recorded at `lock` (the SEED is product truth, discovered; the
// SPINE is aesthetic, chosen -- see SYNTHESIS-ENGINE.md S2). Nothing here is
// brand-specific -- every value comes from `args`; the worked examples (Cairn,
// Velm) live only under examples/, never in this code.
// -----------------------------------------------------------------------------

// args may arrive as an object OR a JSON string (harness-dependent) -- normalize.
const A = typeof args === "string"
  ? (() => { try { return JSON.parse(args); } catch { return {}; } })()
  : (args ?? {});
const brief = A.brief ?? "a product (pass a real one-line brief via args.brief)";
// Fail SAFE: a missing/unrecognized phase runs a cheap diagnostic, NEVER an
// expensive pipeline by accident.
const BAKED_SEED = {"nameReading":"\"Recursive Harness\" is NOT bland -- it hands over a real, intrinsic metaphor, but its surface is also a costume trap. HARNESS = a rig strapped around a power it cannot change (the frozen model weights, the \"engine\") that channels that force and constrains where it may not go (the write-locked enforcement layer). RECURSIVE = the rig retightens its own straps each loop by feeding its outcomes back as input. Distrust the literal costume: leather/buckles/horse-tack is the surface, NOT the soul. The soul is not the strap -- it is what the strap is for: a fixed engine made to fit your work better each pass by recording exactly where it slipped.","essence":"Recursive Harness is the only learnable layer wrapped around a frozen engine -- a rig that turns every lived task into a stated claim scored against reality, files the measured gap between prediction and outcome as a permanent, reviewed diff, and so makes an unchanging model verifiably better at your work without ever retraining it.","material":[{"artifact":"The scored prediction row in state/predictions.jsonl (the predict->act->score unit)","looksLike":"One flat JSON object per line, e.g. {\"id\":\"f6a4741d\",\"ts\":\"2026-06-13T19:14:34+00:00\",\"task\":\"...\",\"expect\":\"...\",\"confidence\":0.7,\"result\":\"hit\",\"notes\":\"...\"}. The load-bearing token is a probability scalar (confidence: 0.00-1.00) welded to a binary verdict (result: \"hit\" | \"miss\"). IDs are 8-char hexadecimal (58a82535, f6a4741d); timestamps are ISO-8601 UTC ending in +00:00. Unscored rows carry result: null -- visible debt.","whyItMatters":"This is the atomic honesty unit and the most ownable token in the whole product. A stated probability fused to a yes/no outcome gives a natural two-state mark -- filled vs hollow, hit vs miss -- plus a 0-1 confidence scale and a monospace hex-id stamp. The null/pending state literally renders 'unscored = debt', a core brand claim."},{"artifact":"The `harness stats` calibration report -- claimed-vs-actual with Brier number","looksLike":"Fixed-column monospace terminal output: `scored: 75  hit-rate: 84%  brier: 0.159  pending: 3`, then confidence buckets `low <0.6 / mid 0.6-0.85 / high >0.85`, each printing `claimed 53% actual 76%` with a trailing drift flag `<-- OVERCONFIDENT` or `<-- underconfident`. The signal IS the gap between claimed and actual; a perfectly honest agent sits on the claimed==actual diagonal.","whyItMatters":"The 45 deg diagonal of perfect calibration (claimed equals actual) is a literal, ownable geometry -- a reliability diagram with dots sitting above or below the line. The Brier scalar (0.000 best -> 1.000 worst) is a precise quality dial, and the `<--` drift arrow plus OVERCONFIDENT/underconfident labels are native notation the brand can quote verbatim."},{"artifact":"The append-only JSONL ledgers themselves (predictions / corrections / approvals / sessions / skill_usage)","looksLike":"Newline-delimited JSON -- every event is exactly one line, never edited, only appended, so the file grows strictly downward (predictions.jsonl is 183 KB, followups.jsonl 88 KB, corrections.jsonl 40 KB). Texture is a left-flush stack of `{`-opening rows with a ragged right edge of uneven line lengths; timestamps increase monotonically top-to-bottom. Sealed, equal-weight horizontal records.","whyItMatters":"Append-only accretion = time as vertical sediment -- strata, tree-rings, a paper tape that only ever lengthens. This anchors the 'versioned ledger, never prose memory' pillar and a layered-strata texture: stacked horizontal bands where age maps to depth and nothing is ever overwritten, only added below."},{"artifact":"cartograph/ATLAS.md -- the self-generated Mermaid map of the harness","looksLike":"A typed node/edge census: `Nodes 139 (adr=9, agent=4, cli=14, command=14, hook=18, skill=21, state=7)` and `Edges 303 (born_in=56, cites=44, fires_on=21, invokes=41, nudges=64, references=29, spawns=18, touches=13, wires=17)`, rendered as a Mermaid flowchart of labeled boxes joined by directed, verb-typed arrows. Narrated in biological language -- genome, immune system, lifecycle membranes, autophagic self-audit -- with a build stamp `generated 2026-06-27 from extract.py @ 21d6ff4`.","whyItMatters":"A directed graph of categorized nodes and verb-typed edges is the system's literal self-portrait. The edge vocabulary (born_in, fires_on, nudges, invokes, spawns) and the count-census table anchor a node-and-arrow motif with a precise, data-driven feel; the genome/immune-system framing supplies an organic counter-texture to the machine grid."},{"artifact":"The three nested self-improvement loops (inner / middle / outer)","looksLike":"In the Atlas: `INNER predict->act->score  ->  MIDDLE /retro: correct->route->PR  ->  OUTER /meta-retro: audit->prune->autonomy`, tagged with the (loop) recycle glyph. Three return-cycles running at three cadences -- every task, every session, every month -- each loop's output feeding the next loop outward. Concentric, each an arrow that closes on itself at a larger scale.","whyItMatters":"Three concentric return-arrows is the product's truest shape: recursion made geometric, straight from the name. This is the strongest logo-grade motif -- nested rings where each ring is an arrow biting its own tail, at three sizes -- and the task/session/month cadence gives a built-in three-tier rhythm for spacing, scale, and hierarchy."},{"artifact":"The git diff + PR as 'the literal unit of learning' (branches, ADRs, provenance footers)","looksLike":"Unified-diff hunks with a +/- gutter (added lines green, removed lines red), dated branch slugs like `retro/2026-06-28-acquire-tools` and `proposal/2026-06-28-atlas-autosync`, numbered decision records `ADR 0001 / ADR 0003`, short git SHAs (21d6ff4, 03beb05), and provenance one-liners stamped into every artifact: `provenance: 2026-06-21, session f36989d6 -- follow-up 99ee20, routed via /harness-pr`.","whyItMatters":"The green-add / red-remove diff gutter is the most quotable visual in the product -- improvement that you can literally see as a +/- change. Dated branch slugs, 7-char SHAs, and 'provenance:' footers are native typographic tokens that model the 'evidence-dated, reviewed, never magic' honesty stance."},{"artifact":"The write-lock guard rejection (hooks/guard_enforcement_layer.py PreToolUse block)","looksLike":"Red stderr text `BLOCKED by harness guard: '<path>' is enforcement-layer ... Self-modification of the layer that measures you requires human review`, exit code 2, and a single physical unlock -- a file literally named `HUMAN_APPROVED` that only a human may `touch`. Framed throughout as a membrane / immune barrier the agent cannot cross on its own.","whyItMatters":"A visible STOP -- the agent forbidden from quietly weakening the rules that grade it. This anchors the 'honest by construction' pillar with a real artifact: a barrier/seal glyph, a locked state, the human-gated HUMAN_APPROVED token, and red as the system's single alarm colour against an otherwise calm, neutral palette."},{"artifact":"The trigger-loaded skill file (skills/*/SKILL.md) and its escalation ladder","looksLike":"A `---` fenced YAML header (`name:` and a `description:` written as explicit trigger conditions) sitting atop a markdown procedure. Bodies are built as numbered escalation ladders -- `Strike 1 (a failure) -> Strike 2 -- same failure class: STOP -> Strike 3: ESCALATE`. The skill stays dormant until its trigger fires, then loads.","whyItMatters":"The `---` frontmatter fence and the numbered Strike-1/2/3 rungs are recurring structural notation across the whole skill library. They anchor a dormant-vs-active duality (loaded only on trigger) and a rung/ladder motif for any stepwise procedure -- a clean way to depict 'a procedure that fires exactly when its condition is met'."}],"ignition":[{"name":"Metaculus -- Track Record / Calibration curves","url":"https://www.metaculus.com/questions/track-record/","whatToSteal":"The move: plot a forecaster's OWN history as stated-probability vs. actual-resolved-frequency against the line of perfect calibration, so over/under-confidence shows up as geometric deviation from the diagonal -- not a claim you can argue with. Migrate the principle that the honesty metric is rendered as deviation from an ideal reference line, making 'I was miscalibrated' unhideable. Maps directly to Brier-scored predictions and 'unscored predictions show up as debt.' Steal the structural device (track-record-as-deviation), not Metaculus's chrome or palette."},{"name":"Edward Tufte -- Sparklines & Small Multiples","url":"https://www.edwardtufte.com/notebook/sparkline-theory-and-practice-edward-tufte/","whatToSteal":"Two distinct moves. (1) The sparkline: a word-sized, frameless, data-ink=1.0 graphic that lives INLINE inside a sentence -- so a prediction's hit/miss streak can sit in running prose without breaking the line. (2) Small multiples: a grid of identically-framed mini-charts so version N vs N+1 vs N+2 are compared by eye in one glance. Migrate the density-and-comparison logic for the JSONL ledger and the regression corpus, not any specific chart styling."},{"name":"Stripe -- API documentation (synced prose + live code)","url":"https://docs.stripe.com/api","whatToSteal":"The move: lock explanatory prose to a parallel, live, runnable code column that scroll-syncs and injects the reader's own context (test keys) -- the explanation and the executable artifact are never separated, and the code is the real thing, not a screenshot. Migrate this 'rationale welded to the literal artifact, kept in sync' pattern to 'git diff as the unit of learning': show the diff and the why side-by-side, co-scrolling. Steal the synced-twin-column structure, not Stripe's typography or brand color."},{"name":"Our World in Data -- Grapher","url":"https://ourworldindata.org/redesigning-our-interactive-data-visualizations","whatToSteal":"The move: every chart frame carries its own provenance -- title, subtitle, exact source line, date, and a built-in data/download toggle baked INTO the artifact -- so a chart screenshotted out of context still cites itself and dates itself. Migrate this 'every artifact is self-describing and evidence-stamped' discipline to the evidence-dated memory and the 'anything unverifiable counts as a miss' invariant. Steal the self-citing artifact frame, not OWID's specific layout or color ramp."},{"name":"Graphite -- Stacked diffs / stack view","url":"https://graphite.com/guides/stacked-diffs","whatToSteal":"The move (inherited from Phabricator/Critique): render the dependency TOPOLOGY of changes as a first-class, navigable stack -- a chain you can step through, where each diff knows what it sits on top of and what depends on it. Migrate this 'changes as a legible dependency structure you traverse' to the three nested loops and the lineage of learnings (which correction produced which guardrail produced which eval). Steal the topology-as-navigable-structure move, not Graphite's UI skin."},{"name":"Rauno Freiberg -- Devouring Details / Interface craft (Vercel)","url":"https://rauno.me/","whatToSteal":"The move: make every state transition LEGIBLE -- a system changing state earns an intentional, observable micro-transition (origin, easing, settle) instead of a silent snap, so the user feels the boundary being crossed. Migrate this to the lifecycle guardrail hooks that fire at session boundaries: a hook firing should be a felt, observable event, not invisible plumbing. Steal the 'state changes are narrated by motion' principle, never a specific animation or the dark-mode aesthetic."}],"generativePrimitives":["THE TWO-STATE MARK -- a single glyph that is FILLED (hit) or HOLLOW (miss), with a third HOLLOW-PENDING (result:null) state that literally renders the brand claim 'unscored = debt.' Traceable to artifact 1, the scored prediction row (confidence welded to hit|miss).","DEVIATION FROM THE LINE -- the 45 deg diagonal where claim==reality, every point placed at its measured distance ABOVE (overconfident) or BELOW (underconfident) the line; layout's unit is 'distance from the diagonal,' honesty made unarguable geometry. Traceable to artifact 2, the harness stats calibration report (Brier, claimed-vs-actual, the <-- drift arrow); ignition: Metaculus track-record-as-deviation.","THE +/- GUTTER -- improvement you can SEE as a literal added/removed change: green-add over red-remove in a left-hand gutter, the git diff as the visible unit of learning, each hunk stamped with a 'provenance:' date+session+SHA footer so it cites itself out of context. Traceable to artifact 6 (diff/PR/provenance) + ignition OWID self-citing frame.","APPEND-ONLY STRATA -- equal-weight horizontal bands stacking strictly DOWNWARD with a ragged right edge, age mapping to depth, nothing ever overwritten; time rendered as sediment / tree-ring accretion. Traceable to artifact 3, the JSONL ledgers ({-opening rows, monotonic timestamps).","THREE CONCENTRIC RETURN-ARROWS -- nested rings, each an arrow that closes on its own tail, at three sizes for the three cadences (task / session / month); recursion made geometric, the logo-grade seed straight from the name. Traceable to artifact 5, the inner/middle/outer loops ((loop)).","THE SINGLE RED ALARM -- red reserved for exactly ONE meaning against an otherwise calm neutral palette: a miss, or the BLOCKED guard; paired with a barrier/seal glyph and the human-only HUMAN_APPROVED unlock. Traceable to artifact 7, the write-lock guard (exit 2, the membrane the agent cannot cross alone).","THE VERB-TYPED NODE-AND-ARROW SELF-PORTRAIT -- labeled boxes joined by directed arrows whose TYPE is a verb (born_in, fires_on, nudges, invokes, spawns), the system drawing its own census. Traceable to artifact 4, ATLAS.md (139 nodes / 303 edges)."],"soulFinding":"The soul of Recursive Harness is the RECORDED GAP between a stated claim and its scored outcome: what the product DOES (hold every prediction accountable to reality and file the difference as a permanent change) and what its world LOOKS LIKE (a confidence number sitting at a measured distance from the line where claim equals result, marked filled or hollow) are the SAME act -- so every form in the brand is a visible distance closing on a line of truth, written into a ledger that can only grow and never be edited; improvement is that gap shrinking in plain sight, and honesty is the gap being impossible to hide.","coreMetaphor":"A self-tightening harness around a frozen engine. The model weights never change (the engine); the repository is the only learnable layer (the rig); \"recursive\" is the rig measuring its own slippage each loop and pulling itself a notch truer -- never by retraining the engine, only by recording, in a ledger it can never erase, the exact distance between what it predicted and what happened."};
const BAKED_CONTENT = "THE PRODUCT - a LANDING PAGE for Recursive Harness. A developer who has never seen it must understand it in ~5 seconds. The SAME underlying content renders in every direction; frame it in YOUR direction's own invented language.\n\n- IDENTITY: the product name 'Recursive Harness' + a small mark.\n- HERO HEADLINE (the promise): 'Your AI coding agent, getting measurably better at YOUR work - and able to prove it.'\n- SUBHEAD: 'The model's weights never change. Its repository becomes the learnable layer: every prediction is scored against reality, and every lesson is filed as a permanent, reviewed change.'\n\n- THE HERO PROOF (a real, signature widget - this is the soul; show it prominently). A calibration readout:\n    scored 176    hit-rate 80%    brier 0.16\n    claimed 0.70  ->  actual 0.76   (slightly underconfident)\n  and a short stack of recent predictions, each marked as a FILLED dot (hit) or a HOLLOW dot (miss), with ONE still PENDING (a hollow, dashed mark = 'unscored = debt'):\n    (hit)      resolve flaky test          confidence 0.80\n    (hit)      refactor the auth flow       confidence 0.65\n    (miss)     migrate the schema           confidence 0.90\n    (pending)  rewrite the cache layer      confidence 0.70\n\n- THREE FEATURE POINTS (the three nested loops / cadences):\n    1. Every task: predict -> act -> score. A stated claim, checked against what actually happened.\n    2. Every session: the gaps become reviewed changes - new procedures, guardrails, calibration.\n    3. Every month: audit, prune, and earn more autonomy - measured, never assumed.\n\n- ONE HONESTY PULL-QUOTE: 'Unscored predictions show up as debt. Anything unverifiable counts as a miss. The agent can never quietly weaken the rules that measure it.'\n- A PRIMARY call-to-action button ('Start the loop') and a secondary link ('See how it works').\n- Keep it focused: no unrelated chrome, no notification noise, no stock imagery, no emoji icons.";
const BAKED_CHOSEN = {"name":"Append-Only Strata","look":"Every form derives from the stratum band. FORM: the unit is a full-width record whose ragged right edge (from real uneven JSON lengths) becomes the texture; a small filled/hollow tab at each band's left carries its hit/miss verdict. GRID: a tall vertical core-sample -- a single 'now' seam at the top admits each new band; everything below is older and immovable; a fixed left rail runs monotonic ISO-8601 `+00:00` timestamps as the ruled margin. PALETTE derives from accretion, not mood: depth IS the palette, an excavation gradient from pale-recent at the seam to deep-buried near-black at the base. TYPE: monospace rows, 8-char hex IDs and timestamps as the recurring grain.","structure":"A tall scrolling stratigraphic core; fixed left timestamp rail; a thin bright 'now' seam at the very top where new bands enter; ragged right edge throughout; oldest strata compressed and darkened at the base; no floating elements, every block load-bearing on the one below.","concept":"A time rendered as downward sediment in a file that can only ever grow language, grown from The stratum band -- a left-flush, ragged-right horizontal record that can only be appended beneath, never overwritten, darkening one tonal step with every increment of age.."};
if (!A.chosen) A.chosen = BAKED_CHOSEN;
if (!A.seed) A.seed = BAKED_SEED;
if (!A.content) A.content = BAKED_CONTENT;
const which = A.phase ?? "__diagnostic__";

if (which === "__diagnostic__") {
  log("DIAGNOSTIC -- typeof args=" + (typeof args) + "  parsed.phase=" + (A.phase ?? "(none)"));
  log("DIAGNOSTIC -- raw args=" + JSON.stringify(args));
  return { phase: "__diagnostic__", argsType: typeof args, parsedPhase: A.phase ?? null, rawArgs: args ?? null };
}

// A schema shared by every screen/board/surface builder: the pitch the human reacts to.
const SCREEN_SCHEMA = {
  type: "object",
  required: ["key", "title", "anchor", "pitch", "distinct", "htmlPath"],
  properties: {
    key: { type: "string" }, title: { type: "string" }, anchor: { type: "string" },
    pitch: { type: "string" }, distinct: { type: "string" }, htmlPath: { type: "string" },
  },
};

// Geometry instrumentation: every builder tags its structural elements so the
// geometry linter (tools/lint-geometry.mjs) can ASSERT placement instead of the
// operator eyeballing a PNG (the few-px lockup drift that slipped through on Velm).
const GEOM = `GEOMETRY TAGS (so layout can be machine-checked): add data-geom="frame" to the fixed-size outer frame; and wherever a logo lockup appears, tag its mark data-geom="mark" and its wordmark data-geom="wordmark" (they must share a vertical centre). These attributes are invisible; add them, don't restyle around them.`;

// ===== seed (soul extraction -- replaces ground) ==============================
// SYNTHESIS-ENGINE.md S3.1. Produce the generative DNA the whole brand grows
// from, BEFORE any visual. This IS lathe's gate-03 research-grounded reset,
// promoted to the DEFAULT entry point (not a rejection fallback). Two scouts
// gather the soil (the product's OWN material) + ignition (world-class craft to
// LEARN from, never a menu to pick) in PARALLEL; the soul-diviner then
// SYNTHESIZES the SEED via the coincidence method -- where a function-truth and a
// material artifact COINCIDE is the soulFinding, the generative truth no library
// contains. The main loop SHOWS the SEED to the human (approve/redirect) before
// the four expensive synthesize builds. A hard reject downstream routes back here
// with `resetDeeper` + the rejection `signal`: re-interrogate the soul DEEPER
// (never re-roll synthesize -- the Tripwire anti-pattern).
if (which === "seed") {
  phase("seed");
  const resetNote = A.resetDeeper
    ? `\n\nRESET-DEEPER: an earlier synthesize round was HARD-REJECTED${A.signal ? ` -- the human said: "${A.signal}"` : ""}. The previous soul was too SHALLOW (a rejection means the seed wasn't deep enough, never that research was skipped). Do NOT repeat the previous soul-finding: question it, widen the material, and find a LESS obvious coincidence further from the name's surface reading.\n`
    : "";
  log(`[brand-foundry] seed phase -- brief="${brief}"${A.resetDeeper ? "  (reset-deeper)" : ""}`);

  const MATERIAL_SCHEMA = {
    type: "object", required: ["material"],
    properties: {
      material: {
        type: "array", minItems: 4, maxItems: 10,
        items: {
          type: "object", required: ["artifact", "looksLike", "whyItMatters"],
          properties: {
            artifact: { type: "string" }, looksLike: { type: "string" }, whyItMatters: { type: "string" },
          },
        },
      },
    },
  };
  const IGNITION_SCHEMA = {
    type: "object", required: ["ignition"],
    properties: {
      ignition: {
        type: "array", minItems: 3, maxItems: 8,
        items: {
          type: "object", required: ["name", "whatToSteal"],
          properties: {
            name: { type: "string" }, url: { type: "string" }, whatToSteal: { type: "string" },
          },
        },
      },
    },
  };
  // The soul-diviner synthesizes only the GENERATIVE fields; the phase assembles
  // the full SEED (merging in the scouts' material + ignition) below.
  const SOUL_SCHEMA = {
    type: "object", required: ["nameReading", "essence", "generativePrimitives", "soulFinding"],
    properties: {
      nameReading: { type: "string" }, coreMetaphor: { type: "string" }, essence: { type: "string" },
      generativePrimitives: { type: "array", minItems: 1, items: { type: "string" } },
      soulFinding: { type: "string" },
    },
  };

  // Soil + ignition in parallel; the cartographer is the load-bearing one (a
  // bland name's soul comes from FUNCTION + MATERIAL, not the name -- S4).
  const [mat, refs] = await parallel([
    () => agent(
      `You are the material-cartographer for a brand foundry, seeding a brand for this product:\n\n  "${brief}"\n\n` +
      `huashu's first rule: design FROM context, never from a void. BEFORE anyone invents a look, MAP the product's OWN visual material -- the real artifacts, textures, shapes, notation and language that already belong to THIS product's world and could only belong to it. Think hard and specifically about what the work of THIS product actually LOOKS LIKE in reality: its data, its outputs, its tools, its notation, the shapes and structures a practitioner already recognises. This is the SOIL the brand is GROWN from, never a costume borrowed from an unrelated world. Use WebSearch if you need to see the real artifacts.\n\n` +
      `Return via the schema: material[] each { artifact (the real thing -- name it precisely), looksLike (its concrete visual form -- shape, colour, notation, texture), whyItMatters (what it could anchor in the design) }. At least 4, specific to THIS product -- nothing generic.`,
      { label: "material-cartographer", phase: "seed", schema: MATERIAL_SCHEMA }
    ),
    () => agent(
      `You are the references-scout for a brand foundry, seeding a brand for this product:\n\n  "${brief}"\n\n` +
      `Find the REAL, world-class design we should LEARN CRAFT FROM -- this is IGNITION, never a catalog to pick a look from. Using WebSearch, find the BEST real, verified, genuinely-excellent designs (ideally award-winning -- Awwwards / CSS Design Awards / FWA / Apple Design Award -- or acknowledged best-in-class) RELEVANT to THIS product's domain and the craft traditions it belongs to. For each, confirm it exists (WebSearch), then name the concrete craft MOVE worth migrating -- never the style. CRITICAL: a reference is ignition only; it may NEVER become a direction's identity (that would be selection, the failure this engine exists to fix).\n\n` +
      `Return via the schema: ignition[] each { name, url (if found), whatToSteal (the concrete MOVE to migrate, never the style) }. At least 3. No generic "modern minimal SaaS" -- name real, specific, verifiable work.`,
      { label: "references-scout", phase: "seed", schema: IGNITION_SCHEMA }
    ),
  ]);

  // The soul-diviner -- the load-bearing NEW agent. The coincidence method makes
  // the seed un-selectable: it begins from the product's own function + material.
  const soul = await agent(
    `You are the soul-diviner for a brand foundry -- the most important step. Synthesize the product's SOUL into a single generative truth, for:\n\n  "${brief}"\n\n` +
    `You are given the product's OWN material (the soil) and world-class craft as ignition:\n\n` +
    `THE PRODUCT'S MATERIAL (from the cartographer):\n${mat.material.map((m, i) => `  ${i + 1}. ${m.artifact} -- ${m.looksLike}${m.whyItMatters ? ` (matters: ${m.whyItMatters})` : ""}`).join("\n")}\n\n` +
    `IGNITION -- craft to learn from (the MOVE, never the style):\n${refs.ignition.map((r, i) => `  ${i + 1}. ${r.name} -- steal: ${r.whatToSteal}`).join("\n")}\n` +
    resetNote + "\n" +
    `THE COINCIDENCE METHOD (follow it exactly -- this is what makes the seed un-selectable):\n` +
    `1. List the product's FUNCTION-TRUTHS -- what it actually DOES, in plain terms (e.g. for a machine tool: "turns raw stock into proven, fabricated form").\n` +
    `2. List its MATERIAL ARTIFACTS (from the material above) -- the concrete things its world looks like.\n` +
    `3. Find where a FUNCTION-TRUTH and a MATERIAL ARTIFACT COINCIDE -- the single point where what the product DOES and what its world LOOKS LIKE are the SAME thing. Named in one sentence, that coincidence is the soulFinding. It is generative precisely because it is a TRUTH, not a taste -- no competitor can borrow it and no style library contains it.\n` +
    `4. Derive generativePrimitives[] -- the VISUAL FORM of that coincidence (candidate recurring devices), each traceable to a NAMED material artifact above.\n\n` +
    `IMPORTANT -- bland/abstract name: if the name hands over no metaphor (e.g. a coined or generic name), say so in nameReading ("name hands over nothing; soul comes from function") and dig the soul out of FUNCTION + MATERIAL. The name's surface reading is the COSTUME TRAP -- actively distrust it.\n\n` +
    `Return via the schema:\n` +
    `- nameReading -- what the name evokes, OR the bland-name note above.\n` +
    `- coreMetaphor -- INTRINSIC only (grows from name/function); omit if none is honest.\n` +
    `- essence -- one deep sentence: what it fundamentally IS.\n` +
    `- generativePrimitives -- the candidate recurring devices grown from the coincidence (each traceable to a named material artifact).\n` +
    `- soulFinding -- THE output: the non-obvious generative truth, in one sentence. (the most important field)`,
    { label: "soul-diviner", phase: "seed", schema: SOUL_SCHEMA }
  );

  // ASSEMBLE the full SEED (SYNTHESIS-ENGINE.md S3.1 output / contracts.SEED_SCHEMA):
  // the diviner's synthesis + the scouts' soil & ignition. coreMetaphor is added
  // only when present (the schema makes it optional; an undefined key would fail).
  const seed = {
    nameReading: soul.nameReading,
    essence: soul.essence,
    material: mat.material,
    ignition: refs.ignition,
    generativePrimitives: soul.generativePrimitives,
    soulFinding: soul.soulFinding,
  };
  if (soul.coreMetaphor) seed.coreMetaphor = soul.coreMetaphor;

  log(`seed: soulFinding="${seed.soulFinding}" . ${seed.material.length} material . ${seed.ignition.length} ignition . ${seed.generativePrimitives.length} primitives`);
  return { phase: "seed", stub: false, brief, seed };
}

// ===== synthesize (INVENT, don't apply -- replaces explore) ===================
// SYNTHESIS-ENGINE.md S3.2. The crux of the engine. Generate N ORIGINAL visual
// languages, each grown from a DIFFERENT facet of the SEED, each a real 1440x900
// app screen. A synthesis-planner controls the spread (enforces divergence BY
// SEED FACET -- NOT a style menu), then N screen-builders each commit MATERIAL-
// FIRST: sourceArtifact -> transform -> primitive -> invented language. The ORDER is
// the anti-selection guarantee -- there is no point at which a style is picked.
// Recognizable named styles BANNED; imported costumes BANNED. The SPINE is NOT an
// input; it crystallizes later (at `lock`) from what the human converges on.
// ITERABLE via `mode`: open (round 1) . focus (re-diverge around liked picks) .
// graft (fuse liked elements across directions into NEW syntheses).
if (which === "synthesize") {
  phase("synthesize");
  const synthesizeDir = A.synthesizeDir ?? A.exploreDir; // operator output dir for the round
  const huashuDir = A.huashuDir;
  const n = A.n ?? 4; // default 4 -- fits an AskUserQuestion multi-select gate (caps at 4)
  const mode = A.mode ?? "open";
  const note = A.note ? `\n\nROUND STEER (from the human's reactions so far): ${A.note}\n` : "";
  const seed = A.seed || {};
  const material = Array.isArray(seed.material) ? seed.material : [];
  const focus = Array.isArray(A.focus) ? A.focus : (A.focus ? [A.focus] : []);
  const focusNames = focus.map((f) => (typeof f === "string" ? f : f.name)).filter(Boolean);
  const graftSources = Array.isArray(A.graftSources) ? A.graftSources : (A.graftSources ? [A.graftSources] : []);
  // fine-grained sub-element targets from the review app's annotations (M5 graft (1) . S11.2):
  // [{key, element, note?}] -- which specific elements of which directions to fuse / push further.
  const graftTargets = Array.isArray(A.graftTargets) ? A.graftTargets : [];
  const focusTargets = Array.isArray(A.focusTargets) ? A.focusTargets : [];
  const fmtTargets = (ts) => ts.map((t) => `${t.key} -> ${t.element}${t.note ? ` (${t.note})` : ""}`).join("; ");
  log(`[brand-foundry] synthesize phase -- brief="${brief}"  N=${n}  mode=${mode}${focusNames.length ? `  focus=[${focusNames.join(", ")}]` : ""}${graftSources.length ? `  graft=[${graftSources.join(", ")}]` : ""}`);

  const DIRECTIONS_SCHEMA = {
    type: "object", required: ["directions"],
    properties: {
      directions: {
        type: "array", minItems: n, maxItems: n,
        items: {
          // matches workflow/contracts.mjs DIRECTION_SCHEMA -- the test cross-checks
          // this output against the M1 contract, so the two can never drift.
          type: "object",
          required: ["key", "name", "seedFacet", "sourceArtifact", "transform", "generativePrimitive", "inventedLanguage", "structure", "originalityClaim", "distinct"],
          properties: {
            key: { type: "string" }, name: { type: "string" }, seedFacet: { type: "string" },
            sourceArtifact: { type: "string" }, transform: { type: "string" }, generativePrimitive: { type: "string" },
            inventedLanguage: { type: "string" }, structure: { type: "string" }, originalityClaim: { type: "string" }, distinct: { type: "string" },
          },
        },
      },
    },
  };

  // The SEED block -- every direction grows FROM this, never from a style. Each
  // direction's sourceArtifact MUST be one of the named material artifacts here.
  const seedBlock =
    `THE SEED -- the product's generative DNA (discovered + approved before any visual). Grow every direction FROM this, never from a style:\n` +
    `  soul-finding (the generative truth): ${seed.soulFinding ?? "(none passed -- the main loop must pass args.seed from the seed phase)"}\n` +
    `  essence: ${seed.essence ?? "(none)"}\n` +
    (seed.coreMetaphor ? `  core metaphor (intrinsic): ${seed.coreMetaphor}\n` : "") +
    `  candidate generative primitives: ${(seed.generativePrimitives || []).join(" . ") || "(none)"}\n` +
    `  the product's OWN material -- each direction's sourceArtifact MUST be ONE of these, by its EXACT name:\n` +
    (material.length ? material.map((m, i) => `   ${i + 1}. ${m.artifact} -- ${m.looksLike}${m.whyItMatters ? ` (anchors: ${m.whyItMatters})` : ""}`).join("\n") : "   (no material passed)") + "\n";

  // ONE planner controls the whole spread so it can ENFORCE divergence (by SEED
  // FACET). Mode picks the round shape; all three keep real divergence.
  const openBlock =
    `Nothing about the aesthetic is decided -- no palette, type, mood, or structure is locked (that SPINE emerges later from the human's reactions). INVENT EXACTLY ${n} genuinely DIFFERENT, ORIGINAL visual languages, each grown from a DIFFERENT facet of the SEED above. Each will be built as a real app screen for the human to REACT to -- so make them maximally different from one another, NOT ${n} flavours of one look.\n`;
  const focusBlock =
    `An earlier synthesize round already happened. The human LIKED these and wants to keep inventing in their spirit:\n${focusNames.map((nm, i) => `  ${i + 1}. ${nm}${(focus[i] && focus[i].why) ? ` -- why: ${focus[i].why}` : ""}`).join("\n")}\n\n` +
    (focusTargets.length ? `They pointed at these SPECIFIC regions to push further (key -> element): ${fmtTargets(focusTargets)}.\n\n` : "") +
    `Re-open synthesis ANCHORED to what they liked: keep the strengths and the spirit they responded to, but INVENT EXACTLY ${n} genuinely DIFFERENT, MORE-creative alternatives that push further into that lineage. Still real divergence over SEED FACETS -- NOT ${n} cosmetic reskins or palette swaps. Each must teach the human something new.\n`;
  const graftBlock =
    `GRAFT mode -- FUSE the strongest liked elements from these directions into NEW syntheses (the "Hybrid = Deck x Roundel" move -- combine best-of-both into a new thing, never a side-by-side paste): ${graftSources.join(", ")}\n\n` +
    (graftTargets.length ? `The human pointed at these SPECIFIC sub-elements to fuse (key -> element): ${fmtTargets(graftTargets)}. Center each fusion on these named elements.\n\n` : "") +
    `Invent EXACTLY ${n} NEW original languages, each a genuine SYNTHESIS that fuses elements of the named directions + the SEED into one coherent invented language. Each must STILL trace to a named SEED sourceArtifact via a stated transform.\n`;
  const roundBlock = mode === "graft" ? graftBlock : (mode === "focus" && focusNames.length ? focusBlock : openBlock);

  const plan = await agent(
    `You are the synthesis-planner for a brand foundry. The product brief is the fixed input:\n\n  "${brief}"\n\n` +
    seedBlock + "\n" +
    roundBlock +
    `\nDIVERGE BY SEED FACET -- this is SYNTHESIS, not selection. Each of the ${n} directions must grow from a DIFFERENT facet of the SEED (a different function-truth, a different generative primitive, or a different material lead). This REPLACES style-selection: you may NOT diverge by selecting a style, by imitating a specific named designer's signature, or by assigning an emotional register / mood (those produce the same archetype spread for every product -- the exact failure this engine exists to fix).\n\n` +
    `For EACH direction you MUST make the generative chain AUDITABLE, with these fields:\n` +
    `- seedFacet -- the facet of the SEED this grows from. Write it as a NOUN PHRASE (e.g. "the woven-thread mesh", NOT a clause like "because the threads interlock") so it reads cleanly downstream. DIFFERENT per direction.\n` +
    `- sourceArtifact -- ONE named real artifact from the SEED's material list above, by its EXACT name. This is the soil; it is NOT a style or a mood. DIFFERENT per direction.\n` +
    `- transform -- the concrete MECHANICAL move from that artifact to a visual primitive (abstract it . repeat it . invert it . make it the grid . make it the mark). It must be auditable -- someone can check the move.\n` +
    `- generativePrimitive -- the recurring device the transform yields (it will become the mark, the layout grid, the rule weights, the type feel, the palette logic).\n` +
    `- inventedLanguage -- how form + structure + palette + type all DERIVE from that primitive, described in the product's OWN terms, NOT as a named style.\n` +
    `- structure -- the screen skeleton.\n` +
    `- originalityClaim -- one sentence: why this is no recognizable named style; what makes it un-nameable / could-only-be-this-product.\n` +
    `- distinct -- what makes it unlike the other directions.\n` +
    `- key (kebab-case), name (<=5 words).\n\n` +
    `Make the ${n} maximally DIFFERENT (different facet + sourceArtifact + transform + structure; span light/dark, classic/modern) -- but every one must be GROWN from THIS product's material, never a generic archetype that would fit any tool.${note}\n` +
    `Return via the schema.`,
    { label: "synthesis-planner", phase: "synthesize", schema: DIRECTIONS_SCHEMA }
  );
  log(`directions: ${plan.directions.map((d) => d.name).join("  .  ")}`);

  // The shared, concrete screen content. The operator SHOULD pass A.content (the
  // product's real sample data -- the whole point is showing real content). This
  // fallback is a brand-NEUTRAL placeholder so the foundry never bakes in any one
  // product; it is intentionally generic.
  const CONTENT = A.content ?? (
    `THE PRODUCT -- main view. The SAME underlying data renders in every direction (only the design changes); you MAY re-label/frame it in your direction's own language.\n` +
    `- An identity zone: the product name + a small mark.\n` +
    `- A list of the user's recent items (each a short title + a date):\n` +
    `   1. "First recent item" -- 2026-06-14\n   2. "Second recent item" -- 2026-06-11\n   3. "Third recent item" -- 2026-06-09\n   4. "Fourth recent item" -- 2026-06-05\n   5. "Fifth recent item" -- 2026-05-30\n   6. "Sixth recent item" -- 2026-05-22\n` +
    `- ONE ITEM OPEN in focus (#1): a title, a metadata line (date . category . 2-3 tags), and a short 2-3 sentence body; plus links to 2 related items.\n` +
    `- A way to return to a previous item, and a way to create a new one.\n` +
    `- Keep it focused: no unrelated chrome, no notification noise.`
  );

  const screens = (await parallel(
    plan.directions.map((d) => () =>
      agent(
        `You are a screen-builder for a brand foundry. Build ONE real, fully-branded product SCREEN for "${brief}" by INVENTING an ORIGINAL visual language -- committing FULLY to your assigned direction.\n\n` +
        `STEP 1 -- LOAD HUASHU (mandatory). Read:\n  ${huashuDir}/SKILL.md\n  ${huashuDir}/references/design-styles.md\n` +
        `Work from its doctrine: design FROM context (never a void), reject AI slop (no purple-gradient / emoji-icons / generic-SaaS / GitHub-dark clich), real type not system defaults, one detail at 120%, honest placeholder over bad implementation, commit hard (NO safe middle). Treat its style library + any references as IGNITION ONLY -- never the destination.\n\n` +
        `YOUR DIRECTION -- ${d.name}:\n  seedFacet: ${d.seedFacet}\n  sourceArtifact (the real product artifact you grow from): ${d.sourceArtifact}\n  transform (artifact -> primitive): ${d.transform}\n  generativePrimitive: ${d.generativePrimitive}\n  inventedLanguage: ${d.inventedLanguage}\n  structure: ${d.structure}\n\n` +
        `MATERIAL-FIRST PROCEDURE -- the ORDER is the guarantee that this is synthesis, not selection. Do it in this exact order:\n` +
        `1. START at the sourceArtifact "${d.sourceArtifact}" -- a real artifact of THIS product, never a style and never a mood.\n` +
        `2. Apply the transform "${d.transform}" to turn that artifact into the generativePrimitive "${d.generativePrimitive}".\n` +
        `3. PROPAGATE the primitive: let the SAME geometry become the mark, the layout grid, the rule weights, the type feel, and the palette logic.\n` +
        `4. ONLY THEN pick concrete values (hex, faces) to SERVE the primitive -- chosen to serve it, never borrowed.\n` +
        `If you cannot trace every element of the screen back to the sourceArtifact via the transform, you have SELECTED A STYLE -- STOP and start over from the material.\n\n` +
        `NAMED-STYLE BAN: do NOT apply Bauhaus / Swiss / International / Memphis / brutalist / editorial / cyberpunk / Material / iOS / generic-SaaS / GitHub-dark -- or any recognizable movement or product look. If a viewer can NAME THE STYLE, you failed.\n` +
        `ANTI-COSTUME: no metaphor imported from an unrelated world (a courtroom, a bomb squad, a friendly steward ...). A metaphor is allowed ONLY if it is INTRINSIC -- it grows from a real artifact of this product.\n\n` +
        `You are ONE of ${n} maximally-different ORIGINAL languages: do NOT drift toward a generic app, and do NOT resemble the other directions. A safe, middle-of-the-road result is a failure.\n\n` +
        `SCREEN CONTENT (same underlying data across all directions; frame it in YOUR language):\n${CONTENT}\n\n` +
        `DELIVERABLE -- a single self-contained HTML app screen (a REAL product UI, not a brand board):\n` +
        `- EXACTLY 1440px wide x 900px tall; fixed frame, overflow hidden; grid-snapped; nothing clips or overlaps.\n` +
        `- Inline CSS only; real free fonts via a Google Fonts <link>; your own SVG marks; no external assets; no required JS.\n` +
        `- Apply huashu anti-slop. Commit to a specific, confident, ORIGINAL look that could only be THIS direction.\n` +
        `- ${GEOM}\n\n` +
        `STEP 2 -- WRITE the HTML with the Write tool to EXACTLY:\n  ${synthesizeDir}/${d.key}.html\n\n` +
        `STEP 3 -- Return via the schema: key="${d.key}", title (<=5 words), anchor (your seedFacet + sourceArtifact), pitch (2-3 sentences for the human), distinct (1 sentence -- what sets it apart from the others), htmlPath.`,
        { label: `screen:${d.key}`, phase: "synthesize", schema: SCREEN_SCHEMA }
      )
    )
  )).filter(Boolean);
  log(`screens returned: ${screens.length}/${plan.directions.length} (divergence + originality guards run in the main loop after render)`);

  return { phase: "synthesize", stub: false, brief, mode, focus: focusNames, directions: plan.directions, screens };
}

// ===== develop (REFINEMENT only -- dial in the ONE chosen design) =============
// NOT a second divergence. The won design is fixed; this phase produces N
// REFINEMENTS of it (type scale . palette finish . density . hierarchy . the one
// signature detail) -- each keeping the SAME concept and the SAME skeleton. New
// designs and new structures belong in `explore` (iterate it), never here. (The
// scoped-divergence engine that used to live here moved to explore's `focus`.)
if (which === "develop") {
  phase("develop");
  const developDir = A.developDir;
  const huashuDir = A.huashuDir;
  const n = A.n ?? 3;
  const chosen = A.chosen || {}; // { name, concept, look, structure }
  const basePaths = A.basePaths || (A.basePath ? [A.basePath] : []);
  const chosenDesc =
    `THE CHOSEN DESIGN (fixed -- every refinement keeps its concept AND its skeleton):\n` +
    `  name: ${chosen.name}\n  concept: ${chosen.concept}\n  look: ${chosen.look}\n  structure: ${chosen.structure}\n`;

  // Refinements: operator-prescribed (A.variants) OR proposed by a REFINEMENT-planner.
  // The planner dials in finish ONLY -- it must never propose a new design or a new
  // layout (that would be the "develop drifted into new designs" failure).
  let variants = A.variants;
  if (!variants || !variants.length) {
    const REFINE_SCHEMA = {
      type: "object", required: ["refinements"],
      properties: {
        refinements: {
          type: "array", minItems: n, maxItems: n,
          items: {
            type: "object", required: ["key", "name", "refinement", "emphasis"],
            properties: {
              key: { type: "string" }, name: { type: "string" },
              refinement: { type: "string" }, emphasis: { type: "string" },
            },
          },
        },
      },
    };
    const plan = await agent(
      `You are the refinement-planner for a brand foundry, in the DEVELOP phase. The design is already chosen and FIXED -- your job is to dial it in, NOT to redesign it.\n\n` +
      chosenDesc + "\n" +
      `Propose EXACTLY ${n} REFINEMENTS of this one design. Each refinement keeps the SAME concept and the SAME screen skeleton/structure; it only dials in FINISH -- e.g. the type scale + face pairing, the palette finish (the exact hues/contrast), spacing + density, the hierarchy + rule weights, or pushing the ONE signature detail to 120%. Each refinement should test a different finish question so the human learns which dial-in they prefer. Do NOT propose a new design, a new metaphor, or a new layout -- that belongs in explore, not here.\n\n` +
      `For each of ${n}: key (kebab-case), name (<=5 words), refinement (what you dial in -- 1-2 sentences, finish only), emphasis (the ONE detail pushed to 120%). Return via the schema.`,
      { label: "refinement-planner", phase: "develop", schema: REFINE_SCHEMA }
    );
    variants = plan.refinements;
    log(`refinement-planner proposed ${variants.length}: ${variants.map((v) => v.name).join("  .  ")}`);
  }
  log(`[brand-foundry] develop phase -- ${variants.length} refinements of "${chosen.name}"`);

  const screens = (await parallel(
    variants.map((v) => () =>
      agent(
        `You are a screen-builder for a brand foundry, in the DEVELOP phase -- REFINEMENT, not redesign. ${chosen.name ? `The chosen design is "${chosen.name}".` : ""}\n\n` +
        `STEP 1 -- LOAD HUASHU (mandatory): read\n  ${huashuDir}/SKILL.md\n  ${huashuDir}/references/design-styles.md\nApply its doctrine: design FROM context, reject AI slop, real type, one detail at 120%, honest placeholder over bad implementation, commit hard.\n\n` +
        `STEP 2 -- STUDY THE CHOSEN DESIGN (read each HTML; internalise its layout, content, palette and type -- you are refining THIS, not starting over):\n${(basePaths || []).map((p) => "  " + p).join("\n") || "  (no base path provided -- work from the description below)"}\n\n` +
        chosenDesc + "\n" +
        `YOUR REFINEMENT -- ${v.name}:\n  dial in: ${v.refinement}\n  push to 120%: ${v.emphasis}\n\n` +
        `Refine the chosen design: keep the SAME skeleton/structure and the SAME concept and the SAME content; apply ONLY this refinement to resolve and polish the finish. Do NOT create a new design, do NOT change the structure or the navigation model, do NOT invent a new metaphor. The result must read as the SAME design, dialled in -- more resolved than the base, with the one signature detail at 120%.\n\n` +
        `DELIVERABLE -- a single self-contained HTML app screen (real product UI):\n` +
        `- EXACTLY 1440px x 900px; fixed frame, overflow hidden; grid-snapped; nothing clips or overlaps.\n` +
        `- Inline CSS; real free fonts via a Google Fonts <link>; your own SVG marks; no external assets; no required JS.\n` +
        `- Huashu anti-slop. Keep the SAME content as the base (same items + same open item in focus).\n` +
        `- ${GEOM}\n\n` +
        `STEP 3 -- WRITE the HTML with the Write tool to EXACTLY:\n  ${developDir}/${v.key}.html\n\n` +
        `STEP 4 -- Return via the schema: key="${v.key}", title (<=5 words), anchor (the chosen design + this refinement), pitch (2-3 sentences for the human -- what the dial-in changed), distinct (1 sentence -- the finish question this refinement answers), htmlPath.`,
        { label: `dev:${v.key}`, phase: "develop", schema: SCREEN_SCHEMA }
      )
    )
  )).filter(Boolean);
  log(`develop screens returned: ${screens.length}/${variants.length}`);
  return { phase: "develop", stub: false, brief, chosen, refinements: variants, screens };
}

// ===== lock (crystallize the spine from the chosen screens) ==================
// The payoff of the inverted flow: the spine is RECORDED from what the human
// converged on across rounds, not synthesized up front. token-extractor pulls the
// real values from the chosen screens; language-codifier writes the brand book.
if (which === "lock") {
  phase("lock");
  const chosen = A.chosen || []; // [{ view, htmlPath }]
  const huashuDir = A.huashuDir;
  // The converged identity, in words -- passed from the main loop (what the human
  // landed on across the explore cycle). NEVER hardcode a specific product's spine.
  const spine = A.spine ?? "(the chosen design's identity -- derive it faithfully from the screens)";
  log(`[brand-foundry] lock phase -- crystallizing spine from ${chosen.length} chosen screen(s)`);

  const TOKENS_SCHEMA = {
    type: "object", required: ["groups"],
    properties: {
      groups: {
        type: "array",
        items: {
          type: "object", required: ["group", "tokens"],
          properties: {
            group: { type: "string" },
            tokens: {
              type: "array",
              items: {
                type: "object", required: ["name", "value", "meaning"],
                properties: { name: { type: "string" }, value: { type: "string" }, meaning: { type: "string" } },
              },
            },
          },
        },
      },
    },
  };

  const tokens = await agent(
    `You are the token-extractor for a brand foundry. Read these chosen, human-approved app screen(s) for "${brief}" and extract the REAL design values actually used (verbatim hex, font families, sizes, spacing, radii):\n${chosen.map((c) => `  ${c.view}: ${c.htmlPath}`).join("\n")}\n\n` +
    `THE CHOSEN IDENTITY (what you are RECORDING, not inventing):\n${spine}\n\n` +
    `Extract the token system into sensible semantic GROUPS that fit THIS design -- e.g. Surfaces/background . Ink/text . Accent(s) . any secondary/section colours . Hairlines/rules/grid . Typography (faces + roles + the size scale) . Geometry/spacing/radii . Motion (if any). Use the ACTUAL values from the HTML; never invent values that are not present. If more than one screen is given, extract the SHARED system and, where they differ, take the most-resolved value and say so in the meaning. Each token: name (semantic, e.g. --paper / --ink / --accent), value, meaning. Return via the schema.`,
    { label: "token-extractor", phase: "lock", schema: TOKENS_SCHEMA }
  );
  log(`extracted ${tokens.groups.reduce((n, g) => n + g.tokens.length, 0)} tokens across ${tokens.groups.length} groups`);

  const LANG_SCHEMA = {
    type: "object", required: ["languageMd", "sectionTitles"],
    properties: { languageMd: { type: "string" }, sectionTitles: { type: "array", items: { type: "string" } } },
  };
  const lang = await agent(
    `You are the language-codifier for a brand foundry. Write "LANGUAGE.md" -- the single source of truth for how "${brief}" looks, feels and reads. The brand was DISCOVERED through an explore cycle the human reacted to; you are RECORDING the converged result, not inventing it.\n\n` +
    `THE CHOSEN IDENTITY / SPINE (honor it exactly -- this is the brand):\n${spine}\n\n` +
    `STUDY the chosen screen(s) (the brand made real):\n${chosen.map((c) => `  ${c.view}: ${c.htmlPath}`).join("\n")}\n` +
    `and the extracted tokens:\n${JSON.stringify(tokens, null, 2)}\n\n` +
    `Load huashu's anti-slop doctrine for the checklist: ${huashuDir}/SKILL.md (S6).\n\n` +
    `Write LANGUAGE.md in these 11 sections, SPECIFIC to "${brief}" (never generic), with the rigor of a premium brand book. Derive EVERY section from the spine + the screens + the tokens -- use the REAL hex/faces from the tokens, semantic names, and the product's own motif + voice:\n` +
    `1 Positioning / soul -- the spine's positioning, in the product's own terms.\n` +
    `2 The logomark -- the product's mark; describe it from the screen, and if the screen implies but does not fully resolve a mark, specify its construction.\n` +
    `3 The wordmark -- the product name set in its display face; treatment + usage.\n` +
    `4 Secondary marks / texture -- the design's recurring devices (rules, motif, signature elements actually present in the screens).\n` +
    `5 Color -- the palette ladder from the tokens (REAL hex, semantic names) + the accent rule the design follows.\n` +
    `6 Typography -- the faces (role-bound) + the size scale, from the tokens.\n` +
    `7 Surface & structure -- the screen's skeleton + structural rules + how hierarchy/depth is achieved; state plainly what is FORBIDDEN (e.g. no drop-shadow) if the design avoids it.\n` +
    `8 Motion -- state it plainly (minimal if the design is essentially static).\n` +
    `9 Voice & nomenclature -- the product's voice register with REAL sample lines + the naming of its key actions; the no-hype / no-emoji / no-badges rules if they apply.\n` +
    `10 Anti-slop checklist -- product-specific pass/fail derived from huashu S6 + what THESE screens got right (the things that would make this brand read generic).\n` +
    `11 Provenance -- discovered via the brand-foundry explore cycle; which design was chosen and why; tokens extracted from the chosen screen(s).\n\n` +
    `Write tight, specific, and TRUE to the screens. Return via the schema: languageMd (full markdown), sectionTitles (the section titles).`,
    { label: "language-codifier", phase: "lock", schema: LANG_SCHEMA }
  );
  log(`LANGUAGE.md drafted -- ${lang.languageMd.length} chars, ${lang.sectionTitles.length} sections`);

  return { phase: "lock", stub: false, brief, tokens, languageMd: lang.languageMd, sectionTitles: lang.sectionTitles };
}

// ===== package (build the brand out from the locked spine) ===================
if (which === "package") {
  phase("package");
  const langPath = A.langPath;
  const tokensPath = A.tokensPath;
  const bookDir = A.bookDir;
  const identityDir = A.identityDir;
  const huashuDir = A.huashuDir;
  const screens = A.screens || []; // [{ view, pngRel }]
  const spine = A.spine ?? "(the brand -- honor LANGUAGE.md + tokens.json exactly)";
  log(`[brand-foundry] package phase -- brand book + identity`);

  const ART_SCHEMA = {
    type: "object", required: ["files", "note"],
    properties: { files: { type: "array", items: { type: "string" } }, note: { type: "string" } },
  };

  const out = (await parallel([
    () => agent(
      `You are the brand-book builder for a brand foundry. Build a single cohesive brand-guidelines page for "${brief}" that EXEMPLIFIES the brand it documents (it must LOOK like the brand, not a generic doc).\n\n` +
      `STEP 1 -- Read the law + tokens and obey them verbatim:\n  ${langPath}\n  ${tokensPath}\n` +
      `STEP 2 -- Load huashu for craft + anti-slop: ${huashuDir}/SKILL.md\n\n` +
      `THE BRAND (honor it; never substitute a different look):\n${spine}\n\n` +
      `Build a 1440px-wide scrolling brand-guidelines page SET IN the brand -- use the brand's OWN palette, faces, rules and motifs from the law/tokens (never a generic doc theme). Sections, each clearly titled:\n` +
      `- Cover -- the wordmark + the logomark (drawn as SVG exactly per LANGUAGE.md S2) + the positioning line.\n` +
      `- Logomark -- the mark with clear-space + min-size notes (from S2).\n` +
      `- Colour -- swatches for the token groups in tokens.json, each with hex + token name (verbatim) + the accent rule (S5).\n` +
      `- Typography -- the brand's faces with specimens + the size scale (from the tokens, S6).\n` +
      `- The surface(s) -- EMBED the real product screen(s) as <img>: ${screens.map((s) => `${s.pngRel} (${s.view})`).join(", ") || "(none provided)"}, captioned, noting they are the brand made real.\n` +
      `- Voice & nomenclature -- the brand's voice register with real sample lines (S9).\n` +
      `- Anti-slop checklist -- the S10 pass/fail list from LANGUAGE.md.\n\n` +
      `Inline the :root tokens (verbatim values); real free fonts via Google Fonts (the brand's faces, named in S6); self-contained except the embedded screen PNG(s) + fonts. Grid-snapped, nothing clips, honest and restrained -- and unmistakably THIS brand.\n\n` +
      `WRITE to: ${bookDir}/index.html. Return via the schema: files (paths written), note (one line).`,
      { label: "brand-book", phase: "package", schema: ART_SCHEMA }
    ),
    () => agent(
      `You are the identity builder for a brand foundry. Produce the core identity assets for "${brief}".\n\n` +
      `Read ${langPath} (S2 logomark, S3 wordmark, S5 colour) and ${tokensPath}. Load huashu craft: ${huashuDir}/SKILL.md.\n\n` +
      `THE BRAND (honor it):\n${spine}\n\n` +
      `Draw the LOGOMARK as clean SVG EXACTLY as specified in LANGUAGE.md S2 -- its construction, its geometry, and the brand palette from the tokens. It must be the brand's real, specified mark, never a generic shape. Produce:\n` +
      `- ${identityDir}/mark.svg        (idle logomark, ~64px artboard)\n` +
      `- ${identityDir}/mark-mono.svg   (one-colour knockout)\n` +
      `- ${identityDir}/favicon.svg     (simplified mark that holds at 16-32px)\n` +
      `- ${identityDir}/index.html      (identity sheet: the mark at several sizes, the wordmark lockup, clear-space, the favicon on light + on a brand-coloured tab -- all set in the brand)\n\n` +
      `Real token values; Google Fonts for the wordmark face (named in S3/S6). COMPOSE the shared component layer: \`<link rel="stylesheet" href="../dist/brand.css">\` and use its \`.bf-<role>\` type classes + \`.bf-lockup\` + \`.bf-rule*\` -- do NOT re-derive the type scale, lockup gap, or rule weights by hand (that is the cross-surface SIZE DRIFT the layer exists to kill); inline only surface-local colour/position. Otherwise self-contained.\n${GEOM} (The identity sheet's wordmark lockup is exactly where this matters -- keep the mark and the wordmark on one vertical centre; \`.bf-lockup\` does this.)\nReturn via the schema: files (paths written), note (one line).`,
      { label: "identity", phase: "package", schema: ART_SCHEMA }
    ),
  ])).filter(Boolean);

  log(`package built: ${out.length}/2 artifact sets`);
  return { phase: "package", stub: false, brief, artifacts: out };
}

// ===== applications (the brand applied across many surfaces) ==================
// One builder per surface; each loads huashu, reads the law + tokens + the real
// app screen(s), and produces ONE polished, on-brand artifact at its own size.
// Brand-NEUTRAL: every brand value (faces, palette, voice, motif, depth rules)
// comes from the locked LANGUAGE.md + tokens + spine -- never hardcoded here.
if (which === "applications") {
  phase("applications");
  const langPath = A.langPath;
  const tokensPath = A.tokensPath;
  const huashuDir = A.huashuDir;
  const outDir = A.outDir;
  const screens = A.screens || []; // [{ pngRel }]
  const surfaces = A.surfaces || []; // [{ key, name, w, h, spec }]
  const spine = A.spine ?? "(the brand -- honor LANGUAGE.md + tokens.json exactly)";
  log(`[brand-foundry] applications phase -- ${surfaces.length} surfaces`);

  const ART_SCHEMA = {
    type: "object", required: ["key", "title", "pitch", "htmlPath"],
    properties: { key: { type: "string" }, title: { type: "string" }, pitch: { type: "string" }, htmlPath: { type: "string" } },
  };

  const built = (await parallel(
    surfaces.map((s) => () =>
      agent(
        `You are a surface-builder for a brand foundry, building ONE polished, fully-resolved application of an EXISTING locked brand. The product is "${brief}". This must match the craft bar of a premium brand build (Pentagram / Collins level), not a quick mock.\n\n` +
        `STEP 1 -- LOAD HUASHU (mandatory): read ${huashuDir}/SKILL.md and ${huashuDir}/references/design-styles.md; apply its doctrine (design FROM context, reject AI slop, real type, one detail at 120%, commit hard, no filler).\n` +
        `STEP 2 -- Read the LOCKED law + tokens and obey them verbatim:\n  ${langPath}\n  ${tokensPath}\n` +
        `THE BRAND (honor it):\n${spine}\n\n` +
        (screens.length ? `STEP 3 -- Study the real app screen(s) for the established craft/voice (reference, do not copy their layout):\n${screens.map((s) => "  " + s.pngRel).join("\n")}\n\n` : "") +
        `BUILD THIS SURFACE -- ${s.name}:\n${s.spec}\n\n` +
        `Requirements:\n` +
        `- EXACTLY ${s.w}px x ${s.h}px; fixed frame; overflow hidden; grid-snapped; NOTHING clips or overlaps; text never collides.\n` +
        `- Use the locked colour tokens verbatim (inline :root from tokens.json) for surface-local colour. Use the brand's OWN type faces (named in LANGUAGE.md S6) via Google Fonts. Draw your own SVG marks per S2. COMPOSE the shared component layer for the SCALE: \`<link rel="stylesheet" href="<relative>/dist/brand.css">\` and use its \`.bf-<role>\` type classes + \`.bf-lockup\` + \`.bf-rule*\` -- do NOT re-type font sizes / line-heights / the lockup gap / rule weights (re-deriving the scale per surface is the cross-surface DRIFT this layer kills). Otherwise self-contained (embedded screen PNGs allowed via the given relative paths). No required JS.\n` +
        `- Obey the brand's palette + accent rule (S5), its surface & depth rules (S7 -- including any 'no drop-shadow' / warm-ground rule it states), its voice & nomenclature (S9), and its anti-slop checklist (S10). No emoji, no hype, no badges/streaks unless S9/S10 sanction them.\n` +
        `- Earn every element; density with restraint; one signature detail at 120%. This is a finished artifact, not a wireframe.\n` +
        `- ${GEOM}\n\n` +
        `WRITE the HTML with the Write tool to EXACTLY:\n  ${outDir}/${s.key}.html\n\n` +
        `Return via the schema: key="${s.key}", title (<=6 words), pitch (2-3 sentences on the surface + its one signature move), htmlPath.`,
        { label: `app:${s.key}`, phase: "applications", schema: ART_SCHEMA }
      )
    )
  )).filter(Boolean);

  log(`applications built: ${built.length}/${surfaces.length}`);
  return { phase: "applications", stub: false, brief, built };
}

// ===== fail-safe: any unknown / stripped phase -> cheap diagnostic ============
// The arc is seed . synthesize . develop . lock . package . applications. Anything
// else (including the retired ground/explore/research/boards/screens/refine
// phases) lands here and returns a placeholder instead of running expensive work
// by accident.
phase(which);
log(`[brand-foundry] unknown/retired phase="${which}"  brief="${brief}" -- no work run (the arc is explore.develop.lock.package.applications)`);
return { phase: which, stub: true, error: "unknown phase" };

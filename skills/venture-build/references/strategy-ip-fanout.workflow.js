// Reusable workflow: fan out a venture's strategy / research / GTM / security /
// compliance written-IP suite in parallel. Each analyst writes ONE Markdown doc to
// disk and returns a structured summary.
//
// Invoke from the venture-build skill:
//   Workflow({ scriptPath: "<this file>", args: { brief, basePath, docs } })
//   - brief:    REQUIRED. Shared venture context prepended to every analyst prompt.
//   - basePath: docs root, e.g. "products/<slug>/docs" (used only by the default plan).
//   - docs:     OPTIONAL [{ phase, label, path, task }]. Omit to use the default 13-doc plan.
//
// provenance: 2026-06-13 · session 406040c3 · trigger: distilled from the AgentOps Trust OS venture build into the venture-build skill.

export const meta = {
  name: 'strategy-ip-fanout',
  description: 'Fan out a venture strategy / research / GTM / security / compliance IP suite in parallel; each analyst writes one Markdown doc.',
  phases: [{ title: 'Business & GTM' }, { title: 'Product' }, { title: 'Security & Compliance' }],
}

if (!args || !args.brief) throw new Error('strategy-ip-fanout: pass args.brief (shared venture context).')
const BASE = args.basePath || 'products/CHANGE-ME/docs'
const docs = (args.docs && args.docs.length) ? args.docs : defaultDocs(BASE)

const DOC_SCHEMA = {
  type: 'object', required: ['path', 'title', 'words', 'summary'], additionalProperties: false,
  properties: {
    path: { type: 'string' }, title: { type: 'string' }, words: { type: 'number' },
    summary: { type: 'string', description: '2-3 sentence conclusion' },
    openQuestions: { type: 'array', items: { type: 'string' } },
  },
}

log(`Spawning ${docs.length} strategy/research analysts in parallel...`)
const results = await parallel(docs.map((d) => () =>
  agent(
    `${args.brief}\n\n## YOUR ASSIGNMENT\n${d.task}\n\n## OUTPUT\nWrite the COMPLETE Markdown document to this absolute path using the Write tool:\n${d.path}\nThen return the structured summary. Do not return the document body in your message — it must be written to the file. Label any invented specifics "(Illustrative — validate before relying.)".`,
    { label: d.label, phase: d.phase || 'Business & GTM', schema: DOC_SCHEMA }
  ).then((r) => ({ ...r, label: d.label }))
))
const ok = results.filter(Boolean)
log(`Strategy IP complete: ${ok.length}/${docs.length} docs written.`)
return {
  written: ok.map((r) => ({ label: r.label, path: r.path, title: r.title, words: r.words })),
  summaries: ok.map((r) => ({ label: r.label, summary: r.summary, openQuestions: r.openQuestions || [] })),
}

function defaultDocs(base) {
  const B = `${base}/business`, P = `${base}/product`, S = `${base}/security`, C = `${base}/compliance`
  return [
    { phase: 'Business & GTM', label: 'market-map', path: `${B}/01-market-map.md`, task: 'MARKET MAP: definition + adjacent markets; TAM/SAM/SOM with explicit assumptions (label illustrative); segments by use case + which are urgent now; budget owners; buyer language; demand drivers / why-now; timing risks. Tables.' },
    { phase: 'Business & GTM', label: 'competitor-map', path: `${B}/02-competitor-map.md`, task: 'COMPETITOR MAP: name the real incumbents + emerging players; per competitor strengths, pricing if known, and where they FALL SHORT for this wedge; a capability matrix; end with our differentiation + the gaps we exploit.' },
    { phase: 'Business & GTM', label: 'icp', path: `${B}/03-icp.md`, task: 'ICP: firmographics; segmentation tiers (ideal/good/poor/anti); buyer personas (goals/pains/triggers/objections); user personas (JTBD); qualifying questions + disqualifiers; the single sharpest beachhead and why.' },
    { phase: 'Business & GTM', label: 'customer-discovery', path: `${B}/04-customer-discovery.md`, task: 'CUSTOMER DISCOVERY (DESK-RESEARCH; label all names/quotes/lists illustrative): ~100-target list segmented; ~50 contact roles; a 12-question non-leading script; 5 outbound angles with copy; ~12 simulated interviews with varied pains; ranked pain patterns; the top-3 most-expensive failure workflows.' },
    { phase: 'Business & GTM', label: 'pricing', path: `${B}/05-pricing.md`, task: 'PRICING: value metric + rationale; packaging tiers (free → dev → team → enterprise + usage/add-ons); willingness-to-pay tied to value; competitor pricing; discount/pilot/annual logic; expansion/NRR; risks. Tables.' },
    { phase: 'Business & GTM', label: 'sales-pipeline', path: `${B}/06-sales-pipeline.md`, task: 'SALES: founder-led + PLG motion; pipeline stages + exit criteria; illustrative lead list; 4-touch outbound sequences for 2 personas; a 30-day pilot offer + pilot→paid playbook; objection handling; sales metrics.' },
    { phase: 'Business & GTM', label: 'acquirer-map', path: `${B}/07-acquirer-map.md`, task: 'ACQUIRER MAP: per strategic acquirer the rationale, what makes us valuable to THEM, comparables + valuation logic, integration thesis; ranked shortlist; build-vs-buy-vs-partner; metrics that maximize strategic value; a diligence data-room outline.' },
    { phase: 'Business & GTM', label: 'positioning-landing', path: `${B}/08-positioning-and-landing.md`, task: 'POSITIONING: a positioning statement; messaging house (promise / 3 pillars / proof); 5 ranked headlines; FULL landing copy for the top 3; a technical-explainer outline; a launch-post draft.' },
    { phase: 'Product', label: 'roadmap', path: `${P}/roadmap.md`, task: 'ROADMAP V1–V5: per version theme, features, why-now, the buyer it unlocks, a success metric, explicit non-goals/kill criteria; a now/next/later view; dependencies; tie each feature to the assumption it tests.' },
    { phase: 'Product', label: 'mvp-spec', path: `${P}/mvp-spec.md`, task: 'MVP TECHNICAL SPEC: the canonical data model; the public SDK/API surface; the dashboard/UX; required integrations; engineering principles; MVP success criteria; explicit non-goals. Keep consistent with the code being built in parallel.' },
    { phase: 'Security & Compliance', label: 'threat-model', path: `${S}/threat-model.md`, task: 'THREAT MODEL (STRIDE + LINDDUN): trust boundaries + data-flow; assets; actors; per-boundary threats with likelihood/impact + mitigations; the scariest product-specific risks; abuse cases; residual-risk register.' },
    { phase: 'Security & Compliance', label: 'security-model', path: `${S}/security-model.md`, task: 'SECURITY MODEL: authn; RBAC + tenant isolation; encryption in transit/at rest/field; secret handling + edge redaction; retention/residency; audit-log integrity; PII detection; key management; control-level mapping to SOC 2 / ISO 42001 / NIST AI RMF; note MVP vs roadmap.' },
    { phase: 'Security & Compliance', label: 'controls-matrix', path: `${C}/controls-matrix.md`, task: 'COMPLIANCE CONTROLS MATRIX: map product controls to SOC 2 TSC, ISO/IEC 42001, NIST AI RMF (note EU AI Act touchpoints); then specify the contents of each exportable evidence pack. Heavy on tables.' },
  ]
}

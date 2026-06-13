// Reusable workflow: adversarially review a codebase by subsystem, then
// independently verify each finding. Returns only CONFIRMED defects, severity-sorted.
// Catches the bugs the test suite does not — edge cases, security holes, integrity
// bypasses, cross-surface parity drift.
//
// Invoke from the venture-build skill:
//   Workflow({ scriptPath: "<this file>", args: { context, areas } })
//   - context: short description of the system + what's already covered by tests.
//   - areas:   REQUIRED [{ key, files: [absolute paths], focus }] — one reviewer each.
//
// provenance: 2026-06-13 · session 406040c3 · trigger: distilled from the AgentOps Trust OS venture build into the venture-build skill.

export const meta = {
  name: 'adversarial-review',
  description: 'Adversarially review a codebase by subsystem, then independently verify each finding; returns confirmed defects.',
  phases: [{ title: 'Review' }, { title: 'Verify' }],
}

if (!args || !Array.isArray(args.areas) || !args.areas.length) {
  throw new Error('adversarial-review: pass args.areas = [{ key, files:[...], focus }].')
}
const CONTEXT = args.context || 'Review this codebase for real correctness/security/integrity bugs the tests do not cover. Report only defects you can justify from the code.'

const FINDINGS_SCHEMA = {
  type: 'object', required: ['findings'], additionalProperties: false,
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['severity', 'file', 'title', 'detail', 'suggested_fix', 'confidence'],
        additionalProperties: false,
        properties: {
          severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low'] },
          file: { type: 'string' }, line: { type: 'number' }, title: { type: 'string' },
          detail: { type: 'string' }, suggested_fix: { type: 'string' }, confidence: { type: 'number' },
        },
      },
    },
  },
}
const VERDICT_SCHEMA = {
  type: 'object', required: ['is_real', 'severity', 'rationale'], additionalProperties: false,
  properties: {
    is_real: { type: 'boolean' },
    severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low'] },
    rationale: { type: 'string' },
  },
}

const reviews = await parallel(args.areas.map((a) => () =>
  agent(
    `${CONTEXT}\n\nYou are reviewing the **${a.key}** subsystem. Read these files in full:\n${(a.files || []).join('\n')}\n\nFocus: ${a.focus || 'correctness, security, integrity, cross-surface parity'}\n\nReport every REAL defect you can justify from the code, with exact file path, line number, a crisp title, the concrete failure scenario, and a specific fix. No style nits. Empty findings is fine if the code is sound.`,
    { label: `review:${a.key}`, phase: 'Review', schema: FINDINGS_SCHEMA }
  ).then((r) => (r?.findings || []).map((f) => ({ ...f, area: a.key })))
))
const all = reviews.filter(Boolean).flat()
log(`Found ${all.length} candidate findings; adversarially verifying each...`)

const verified = await parallel(all.map((f) => () =>
  agent(
    `${CONTEXT}\n\nAdversarially VERIFY this claimed defect. Read the cited file and decide if it is a REAL bug that can actually manifest, or a false positive. Default to is_real=false unless you can construct the concrete failing path.\n\nCLAIM [${f.severity}] ${f.file}:${f.line || '?'} — ${f.title}\n${f.detail}\nProposed fix: ${f.suggested_fix}`,
    { label: `verify:${f.area}`, phase: 'Verify', schema: VERDICT_SCHEMA }
  ).then((v) => ({ ...f, verdict: v }))
))
const order = { critical: 0, high: 1, medium: 2, low: 3 }
const confirmed = verified.filter(Boolean).filter((f) => f.verdict && f.verdict.is_real)
  .sort((a, b) => order[a.severity] - order[b.severity])
log(`Confirmed ${confirmed.length} real defects of ${all.length} candidates.`)
return {
  candidates: all.length,
  confirmed: confirmed.map((f) => ({ severity: f.severity, area: f.area, file: f.file, line: f.line,
    title: f.title, detail: f.detail, suggested_fix: f.suggested_fix, verdict: f.verdict.rationale })),
}

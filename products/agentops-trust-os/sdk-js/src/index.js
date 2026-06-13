// AgentOps — Agent Flight Recorder SDK for JavaScript / TypeScript (Node 18+).
// Zero dependencies. Records tasks + events, redacts sensitive data at the edge,
// evaluates policy locally, and ships events to the AgentOps ingestion API.
// Event field names mirror the Python SDK exactly so both write the same schema.

const SCHEMA_VERSION = "0.1.0";

// ---- redaction (mirror of the Python Redactor) ----
const SENSITIVE_KEYS = new Set([
  "password", "passwd", "secret", "api_key", "apikey", "token", "access_token",
  "refresh_token", "authorization", "auth", "private_key", "client_secret",
  "session", "cookie", "ssn", "credit_card", "card_number",
]);
const PATTERNS = [
  ["openai_key", /sk-[A-Za-z0-9_-]{20,}/g],
  ["anthropic_key", /sk-ant-[A-Za-z0-9_-]{20,}/g],
  ["aws_key", /AKIA[0-9A-Z]{16}/g],
  ["github_token", /gh[pousr]_[A-Za-z0-9]{20,}/g],
  ["bearer", /Bearer\s+[A-Za-z0-9._-]{16,}/g],
  ["private_key_block", /-----BEGIN [A-Z ]*PRIVATE KEY-----/g],
  ["jwt", /eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/g],
];
const MASK = "***REDACTED***";

export function redact(value, found = new Set(), key = null) {
  if (key !== null && typeof key === "string" && SENSITIVE_KEYS.has(key.toLowerCase())) {
    if (value !== null && value !== "" && value !== undefined) {
      found.add(`key:${key.toLowerCase()}`);
      return MASK;
    }
  }
  if (Array.isArray(value)) return value.map((v) => redact(v, found, null));
  if (value && typeof value === "object") {
    const out = {};
    for (const [k, v] of Object.entries(value)) out[k] = redact(v, found, k);
    return out;
  }
  if (typeof value === "string") {
    let s = value;
    for (const [tag, re] of PATTERNS) {
      if (re.test(s)) { found.add(`pattern:${tag}`); s = s.replace(re, MASK); }
      re.lastIndex = 0;
    }
    return s;
  }
  return value;
}

// ---- cost (mirror subset of the Python price table) ----
const PRICES = {
  "anthropic/claude-opus-4": [0.015, 0.075],
  "anthropic/claude-sonnet-4": [0.003, 0.015],
  "openai/gpt-4o": [0.005, 0.015],
  "openai/gpt-4o-mini": [0.00015, 0.0006],
  "google/gemini-2.5-pro": [0.00125, 0.005],
  "mock/mock-fast": [0.0005, 0.0015],
  "mock/mock-smart": [0.003, 0.015],
};
const DEFAULT_RATE = [0.002, 0.008];
export function computeCost(provider, model, tokensIn = 0, tokensOut = 0) {
  const [ri, ro] = PRICES[`${(provider || "").toLowerCase()}/${model}`] || DEFAULT_RATE;
  return Math.round(((tokensIn / 1000) * ri + (tokensOut / 1000) * ro) * 1e6) / 1e6;
}

// ---- policy engine (mirror of the Python evaluator) ----
const PREC = { deny: 3, require_approval: 2, allow: 1 };
export function evaluatePolicy(rules, ctx) {
  let best = null;
  for (const rule of rules || []) {
    if (!matches(rule.match || {}, ctx)) continue;
    if (!triggered(rule, ctx)) continue;
    const cand = { effect: rule.effect || "allow", reason: rule.reason || "", rule_id: rule.id };
    if (!best || PREC[cand.effect] > PREC[best.effect]) best = cand;
  }
  return best || { effect: "allow", reason: "no matching policy rule" };
}
function matches(match, ctx) {
  for (const key of ["tool", "action", "type", "actor"]) {
    const want = match[key];
    if (want === undefined || want === "*") continue;
    const got = ctx[key];
    if (Array.isArray(want)) { if (!want.includes(got)) return false; }
    else if (got !== want) return false;
  }
  return true;
}
function triggered(rule, ctx) {
  const conds = ["max_cost_usd", "task_budget_usd", "deny_data_tags"].filter((k) => k in rule);
  if (!conds.length) return true;
  if ("max_cost_usd" in rule && (ctx.cost_usd || 0) > rule.max_cost_usd) return true;
  if ("task_budget_usd" in rule && (ctx.task_cost_usd || 0) > rule.task_budget_usd) return true;
  if ("deny_data_tags" in rule) {
    const tags = new Set(ctx.data_tags || []);
    if (rule.deny_data_tags.some((t) => tags.has(t))) return true;
  }
  return false;
}

export function defaultPolicy() {
  return [
    { id: "deny-destructive", match: { tool: ["shell:rm-rf", "filesystem:delete_all"] }, effect: "deny",
      reason: "Destructive operations are blocked outright" },
    { id: "approve-prod", match: { action: ["merge_pull_request", "deploy", "delete_resource", "send_external_email"] },
      effect: "require_approval", reason: "Production-affecting actions require a human approver" },
    { id: "budget", match: {}, effect: "require_approval", task_budget_usd: 5.0, reason: "Task budget exceeded" },
  ];
}

function newId(prefix) {
  return `${prefix}_${Math.abs(hashStr(prefix + SCHEMA_VERSION + Math.floor(performance.now() * 1000))).toString(16)}${Date.now().toString(16)}`;
}
function hashStr(s) { let h = 0; s = String(s); for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return h; }

// ---- default transport: POST events to the ingestion API ----
function fetchTransport(apiUrl, apiKey) {
  return async (events) => {
    const res = await fetch(`${apiUrl}/v1/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
      body: JSON.stringify({ events }),
    });
    if (!res.ok) throw new Error(`ingest failed: ${res.status} ${await res.text()}`);
    return res.json();
  };
}

class TaskHandle {
  constructor(client, task) {
    this.client = client;
    this.task = task;
    this.cost_usd = 0;
    this._seq = 0;
    this._ended = false;
  }
  get id() { return this.task.task_id; }

  _emit(type, fields = {}) {
    const found = new Set();
    const input = redact(fields.input ?? null, found);
    const output = redact(fields.output ?? null, found);
    const attributes = redact(fields.attributes ?? {}, found);
    const ev = {
      type, task_id: this.id, event_id: newId("evt"), seq: this._seq++,
      ts: Date.now(), actor: fields.actor ?? this.client.agent, name: fields.name ?? "",
      status: fields.status ?? "ok", input, output, model: fields.model ?? null,
      provider: fields.provider ?? null, cost_usd: fields.cost_usd ?? 0,
      tokens_in: fields.tokens_in ?? 0, tokens_out: fields.tokens_out ?? 0,
      latency_ms: fields.latency_ms ?? 0, error: fields.error ?? null,
      attributes, redactions: [...found].sort(),
    };
    this.cost_usd += ev.cost_usd;
    this.client._buffer.push(ev);
    return ev;
  }

  log(message, level = "info") { return this._emit("log", { name: level, output: message, attributes: { level } }); }
  decision(summary, rationale = "") { return this._emit("decision", { name: summary, attributes: { rationale } }); }
  fileTouch(path, operation = "read", bytes = 0) { return this._emit("file_touch", { name: path, attributes: { operation, bytes } }); }
  modelCall(provider, model, prompt, response, { tokensIn = 0, tokensOut = 0, latencyMs = 0 } = {}) {
    return this._emit("model_call", { name: model, provider, model, input: prompt, output: response,
      cost_usd: computeCost(provider, model, tokensIn, tokensOut), tokens_in: tokensIn, tokens_out: tokensOut, latency_ms: latencyMs });
  }
  toolCall(name, { input = null, output = null, status = "ok", latencyMs = 0, error = null } = {}) {
    return this._emit("tool_call", { name, input, output, status, latency_ms: latencyMs, error });
  }
  async tool(name, fn, input = null) {
    const start = performance.now();
    try {
      const out = await fn();
      this.toolCall(name, { input, output: out, latencyMs: Math.round(performance.now() - start) });
      return out;
    } catch (e) {
      this.toolCall(name, { input, status: "error", error: `${e.name}: ${e.message}`, latencyMs: Math.round(performance.now() - start) });
      throw e;
    }
  }
  guard(action, { tool = null, payload = null, costUsd = 0, dataTags = null } = {}) {
    const ctx = { type: "tool_call", tool, action, actor: this.client.agent, cost_usd: costUsd,
      task_cost_usd: this.cost_usd, data_tags: dataTags || [] };
    const d = evaluatePolicy(this.client.policy, ctx);
    if (d.effect === "allow") {
      this._emit("policy_check", { name: action, status: "ok", attributes: { effect: d.effect, reason: d.reason, tool } });
      return { allowed: true, effect: d.effect, reason: d.reason };
    }
    if (d.effect === "deny") {
      this._emit("policy_check", { name: action, status: "blocked", error: d.reason, attributes: { effect: d.effect, reason: d.reason, tool } });
      return { allowed: false, effect: d.effect, reason: d.reason };
    }
    const ev = this._emit("policy_check", { name: action, status: "pending", attributes: { effect: d.effect, reason: d.reason, tool } });
    return { allowed: false, pending: true, effect: d.effect, reason: d.reason, approvalId: ev.event_id };
  }

  async succeed(output = null) { return this._finish("succeeded", { output, success: true }); }
  async fail(reason, output = null) { return this._finish("failed", { output, success: false, failure_reason: reason }); }
  async _finish(status, extra) {
    if (this._ended) return;
    this._ended = true;
    Object.assign(this.task, { status, ended_at: Date.now() }, extra);
    if (extra.output != null) this.task.output = redact(extra.output);
    await this.client.flush();
  }
}

export class AgentOps {
  constructor({ apiUrl = "http://localhost:8000", apiKey = "demo-key", agent = "agent",
                project = "default", tenant = "default", policy = null, transport = null } = {}) {
    this.apiUrl = apiUrl; this.apiKey = apiKey; this.agent = agent;
    this.project = project; this.tenant = tenant;
    this.policy = policy || [];
    this._transport = transport || fetchTransport(apiUrl, apiKey);
    this._buffer = [];
  }

  startTask(name, { input = null, tags = [], actor = null } = {}) {
    const found = new Set();
    const task = { task_id: newId("task"), name, actor: actor || this.agent, status: "running",
      project: this.project, tenant: this.tenant, started_at: Date.now(), input: redact(input, found), tags };
    return new TaskHandle(this, task);
  }

  // convenience: run an async fn as a task, auto-succeed/fail
  async task(name, fn, opts = {}) {
    const t = this.startTask(name, opts);
    try {
      const out = await fn(t);
      if (!t._ended) await t.succeed(out ?? null);
      return out;
    } catch (e) {
      if (!t._ended) await t.fail(`${e.name}: ${e.message}`);
      throw e;
    }
  }

  async flush() {
    if (!this._buffer.length) return { ingested: 0 };
    const batch = this._buffer.splice(0, this._buffer.length);
    return this._transport(batch);
  }
}

export default AgentOps;
export { SCHEMA_VERSION };

import { test } from "node:test";
import assert from "node:assert/strict";
import { AgentOps, redact, computeCost, evaluatePolicy, defaultPolicy } from "../src/index.js";

const SECRET = "sk-ABCDEFGHIJKLMNOPQRSTUVWX012345";

// Capturing sender mirrors the real API contract shape: { task, events }.
function capturingClient(opts = {}) {
  const events = [], tasks = [];
  const transport = async (payload) => {
    if (payload.task) tasks.push(payload.task);
    events.push(...(payload.events || []));
    return { ingested: (payload.events || []).length };
  };
  const client = new AgentOps({ transport, agent: "tester", policy: defaultPolicy(), ...opts });
  return { client, captured: events, tasks };
}

test("redact masks sensitive keys and secret patterns", () => {
  const found = new Set();
  const out = redact({ user: "alice", password: "hunter2", note: `key ${SECRET}` }, found);
  assert.equal(out.user, "alice");
  assert.equal(out.password, "***REDACTED***");
  assert.ok(!JSON.stringify(out).includes(SECRET));
  assert.ok([...found].some((t) => t.startsWith("pattern:")));
  assert.ok(found.has("key:password"));
});

test("email is redacted (parity with Python)", () => {
  const found = new Set();
  const out = redact("ping jane@example.com please", found);
  assert.ok(!out.includes("jane@example.com"));
  assert.ok(found.has("pattern:email"));
});

test("anthropic key is tagged anthropic_key, not openai_key", () => {
  const found = new Set();
  redact("sk-ant-ABCDEFGHIJKLMNOPQRSTUVWX012345", found);
  assert.ok(found.has("pattern:anthropic_key"));
  assert.ok(!found.has("pattern:openai_key"));
});

test("computeCost matches the documented rate and clamps negatives", () => {
  assert.equal(computeCost("openai", "gpt-4o", 1000, 1000), 0.02);
  assert.equal(computeCost("mock", "mock-fast", 0, 0), 0);
  assert.equal(computeCost("openai", "gpt-4o", -100, -100), 0); // negative tokens never reduce cost
});

test("policy: allow / deny / require_approval / budget", () => {
  const rules = defaultPolicy();
  assert.equal(evaluatePolicy(rules, { tool: "filesystem:delete_all", action: "x" }).effect, "deny");
  assert.equal(evaluatePolicy(rules, { action: "merge_pull_request" }).effect, "require_approval");
  assert.equal(evaluatePolicy(rules, { action: "read" }).effect, "allow");
  assert.equal(evaluatePolicy(rules, { action: "x", task_cost_usd: 6 }).effect, "require_approval");
  assert.equal(evaluatePolicy(rules, { action: "x", task_cost_usd: 2 }).effect, "allow");
});

test("defaultPolicy denies regulated PII tags — incl. a bare string (parity with Python)", () => {
  assert.equal(evaluatePolicy(defaultPolicy(), { action: "export", data_tags: ["ssn"] }).effect, "deny");
  assert.equal(evaluatePolicy(defaultPolicy(), { action: "export", data_tags: "ssn" }).effect, "deny");
});

test("a typo'd match key does not collapse a rule to match-everything", () => {
  const rules = [{ id: "narrow", match: { tols: "github" }, effect: "deny", reason: "x" }];
  assert.equal(evaluatePolicy(rules, { tool: "github", action: "anything" }).effect, "allow");
});

test("task records a full, well-formed event stream", async () => {
  const { client, captured } = capturingClient();
  await client.task("resolve issue #42", async (t) => {
    t.modelCall("openai", "gpt-4o", "fix it", "ok", { tokensIn: 1000, tokensOut: 1000 });
    const src = await t.tool("read_file", async () => "code", { path: "a.js" });
    assert.equal(src, "code");
    t.fileTouch("a.js", "edit", 12);
    const g = t.guard("merge_pull_request", { tool: "github", payload: { pr: 1 } });
    assert.equal(g.pending, true);
    await t.succeed("done");
  });
  assert.deepEqual(captured.map((e) => e.type), ["model_call", "tool_call", "file_touch", "policy_check"]);
  assert.equal(captured[0].cost_usd, 0.02);
  assert.equal(captured[3].status, "pending");
  assert.ok(captured.every((e) => e.task_id && e.event_id && typeof e.seq === "number" && e.ts > 0));
  assert.deepEqual(captured.map((e) => e.seq), [0, 1, 2, 3]);
});

test("task lifecycle is shipped: task created + terminal status sent", async () => {
  const { client, tasks } = capturingClient();
  await client.task("t", async (t) => { t.log("hi"); await t.succeed("done"); });
  const last = tasks[tasks.length - 1];
  assert.equal(last.status, "succeeded");
  assert.equal(last.output, "done");
  assert.ok(last.task_id.startsWith("task_"));
});

test("tool errors are recorded and rethrown", async () => {
  const { client, captured } = capturingClient();
  await assert.rejects(client.task("t", async (t) => {
    await t.tool("flaky", async () => { throw new Error("nope"); });
  }));
  const toolEv = captured.find((e) => e.type === "tool_call");
  assert.equal(toolEv.status, "error");
  assert.ok(toolEv.error.includes("nope"));
});

test("secrets in a model prompt are redacted before leaving the SDK", async () => {
  const { client, captured } = capturingClient();
  await client.task("t", async (t) => {
    t.modelCall("openai", "gpt-4o", `use ${SECRET} to auth`, "refused", {});
    await t.succeed();
  });
  const ev = captured.find((e) => e.type === "model_call");
  assert.ok(!JSON.stringify(ev.input).includes(SECRET));
  assert.ok(ev.redactions.length > 0);
});

test("denied action is blocked, not pending", async () => {
  const { client, captured } = capturingClient();
  await client.task("t", async (t) => {
    const g = t.guard("wipe", { tool: "filesystem:delete_all" });
    assert.equal(g.allowed, false);
    assert.equal(g.pending, undefined);
    await t.succeed();
  });
  assert.equal(captured.find((e) => e.type === "policy_check").status, "blocked");
});

test("flush re-enqueues events when the transport fails", async () => {
  let calls = 0;
  const transport = async () => { calls++; if (calls === 1) throw new Error("network down"); return { ingested: 1 }; };
  const client = new AgentOps({ transport, agent: "tester", policy: defaultPolicy() });
  const t = client.startTask("t");
  t.log("important");
  await assert.rejects(t.flush());      // first flush fails
  assert.equal(t._buffer.length, 1);    // event was re-enqueued, not dropped
  await t.flush();                      // retry succeeds
  assert.equal(t._buffer.length, 0);
});

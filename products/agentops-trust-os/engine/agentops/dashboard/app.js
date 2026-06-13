// AgentOps dashboard — vanilla JS, no build step. Talks to the FastAPI on the same origin.
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
let SELECTED = null;

function apiKey() { return $("#apikey").value.trim(); }
async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: { "X-API-Key": apiKey(), "Content-Type": "application/json", ...(opts.headers || {}) },
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}
function setStatus(msg, bad) { const s = $("#status"); s.textContent = msg; s.style.color = bad ? "var(--err)" : "var(--dim)"; }
const money = (n) => "$" + (Number(n) || 0).toFixed(4);
const pill = (s) => `<span class="pill s-${s}">${s}</span>`;
const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

// ---------------------------------------------------------------- navigation
$$(".tab").forEach((t) => t.addEventListener("click", () => {
  $$(".tab").forEach((x) => x.classList.remove("active"));
  $$(".view").forEach((x) => x.classList.remove("active"));
  t.classList.add("active");
  $("#" + t.dataset.view).classList.add("active");
  refresh();
}));
$("#refresh").addEventListener("click", refresh);
$("#apikey").addEventListener("change", () => { localStorage.setItem("agentops_key", apiKey()); refresh(); });
if (localStorage.getItem("agentops_key")) $("#apikey").value = localStorage.getItem("agentops_key");

function activeView() { return ($(".tab.active") || {}).dataset?.view || "overview"; }

async function refresh() {
  try {
    await loadApprovalBadge();
    const v = activeView();
    if (v === "overview") await loadOverview();
    else if (v === "tasks") await loadTasks();
    else if (v === "approvals") await loadApprovals();
    else if (v === "incidents") { /* on demand */ }
    setStatus("updated " + new Date().toLocaleTimeString());
  } catch (e) { setStatus(e.message, true); }
}

// ------------------------------------------------------------------ overview
async function loadOverview() {
  const m = await api("/v1/metrics");
  const cards = [
    ["Agent tasks", m.tasks, ""],
    ["Success rate", (m.success_rate * 100).toFixed(0) + "%", m.success_rate >= 0.8 ? "good" : "warn"],
    ["Total agent cost", money(m.cost_usd), ""],
    ["Tool calls", m.tool_calls, ""],
    ["Approvals", m.approvals, ""],
    ["Policy denials", m.policy_denials, m.policy_denials ? "warn" : ""],
    ["Incidents", m.incidents, m.incidents ? "bad" : "good"],
    ["Human-review rate", (m.human_intervention_rate * 100).toFixed(0) + "%", ""],
  ];
  $("#cards").innerHTML = cards.map(([lbl, num, cls]) =>
    `<div class="card"><div class="num ${cls}">${num}</div><div class="lbl">${lbl}</div></div>`).join("");
  $("#failure-modes").innerHTML = "<div class='empty'>Run a task replay and scan for incidents to populate failure modes.</div>";
}

// --------------------------------------------------------------------- tasks
async function loadTasks() {
  const tasks = await api("/v1/tasks");
  $("#task-count").textContent = `(${tasks.length})`;
  const tb = $("#task-table tbody");
  if (!tasks.length) { tb.innerHTML = `<tr><td colspan="5" class="empty">No tasks yet. Instrument an agent or run the demo.</td></tr>`; return; }
  tb.innerHTML = tasks.map((t) => `
    <tr data-id="${t.task_id}" class="${t.task_id === SELECTED ? "sel" : ""}">
      <td>${esc(t.name)}</td><td>${esc(t.actor)}</td><td>${pill(t.status)}</td>
      <td>${money(t.rollup.cost_usd)}</td><td>${t.rollup.events}</td>
    </tr>`).join("");
  tb.querySelectorAll("tr[data-id]").forEach((tr) =>
    tr.addEventListener("click", () => loadReplay(tr.dataset.id)));
  if (SELECTED && tasks.some((t) => t.task_id === SELECTED)) loadReplay(SELECTED);
}

async function loadReplay(taskId) {
  SELECTED = taskId;
  $$("#task-table tr").forEach((tr) => tr.classList.toggle("sel", tr.dataset.id === taskId));
  const [task, events, integ] = await Promise.all([
    api(`/v1/tasks/${taskId}`), api(`/v1/tasks/${taskId}/replay`), api(`/v1/tasks/${taskId}/verify`),
  ]);
  $("#detail-title").textContent = task.name;
  const r = task.rollup;
  $("#detail-meta").innerHTML =
    `<b>${esc(task.actor)}</b> · ${pill(task.status)} · cost <b>${money(r.cost_usd)}</b> · `
    + `${r.tokens_in + r.tokens_out} tokens · ${r.events} events · ${r.latency_ms}ms · `
    + `integrity ${integ.integrity_ok ? "<b style='color:var(--ok)'>VERIFIED ✓</b>" : "<b style='color:var(--err)'>BROKEN ✗</b>"}`;
  $("#detail-actions").innerHTML = `
    <button class="small" onclick="scanTask('${taskId}')">Scan for incidents</button>
    <button class="ghost" onclick="showAudit('${taskId}')">Audit report</button>`;
  $("#timeline").innerHTML = events.map(renderEvent).join("");
  $$("#timeline .event-head").forEach((h) =>
    h.addEventListener("click", () => h.nextElementSibling.classList.toggle("open")));
}

function renderEvent(e) {
  const sub = e.model ? `${e.provider}/${e.model}` : (e.attributes && e.attributes.tool) || e.type;
  const cost = e.cost_usd ? money(e.cost_usd) : (e.latency_ms ? e.latency_ms + "ms" : "");
  const redactions = (e.redactions && e.redactions.length) ? ` 🛡️ ${e.redactions.length} redacted` : "";
  const body = { input: e.input, output: e.output, attributes: e.attributes, error: e.error };
  return `<div class="event t-${e.type}">
    <div class="event-head">
      <span class="event-type">#${e.seq} ${e.type}</span>
      <span class="event-name">${esc(e.name || sub)} ${pill(e.status)}<span class="dim">${redactions}</span></span>
      <span class="event-cost">${cost}</span>
    </div>
    <div class="event-body"><pre>${esc(JSON.stringify(body, null, 2))}</pre></div>
  </div>`;
}

window.scanTask = async (taskId) => {
  const found = await api(`/v1/tasks/${taskId}/incidents/scan`, { method: "POST" });
  setStatus(`scanned: ${found.length} incident(s)`);
  if (found.length) { showView("incidents"); renderIncidents(found); }
  else setStatus("no incidents found ✓");
};
window.showAudit = async (taskId) => {
  const md = await api(`/v1/tasks/${taskId}/audit`);
  showView("evidence"); $("#evidence-out").textContent = md;
};

function showView(v) {
  $$(".tab").forEach((x) => x.classList.toggle("active", x.dataset.view === v));
  $$(".view").forEach((x) => x.classList.toggle("active", x.id === v));
}

// ----------------------------------------------------------------- approvals
async function loadApprovalBadge() {
  try { const a = await api("/v1/approvals?status=pending"); $("#apr-badge").textContent = a.length || ""; } catch {}
}
async function loadApprovals() {
  const list = await api("/v1/approvals?status=pending");
  const el = $("#approval-list");
  if (!list.length) { el.innerHTML = `<div class="empty">No pending approvals. The console is clear.</div>`; return; }
  el.innerHTML = list.map((a) => `
    <div class="approval" data-id="${a.approval_id}">
      <div class="a-head"><b>${esc(a.action)}</b> ${pill("pending")}</div>
      <div class="dim">${esc(a.reason || "")} · tool: ${esc(a.tool || "—")} · task ${a.task_id.slice(0, 14)}…</div>
      <pre class="report" style="max-height:120px">${esc(JSON.stringify(a.payload, null, 2))}</pre>
      <div class="actions">
        <button class="ok" onclick="decide('${a.approval_id}','approved')">Approve</button>
        <button class="danger" onclick="decide('${a.approval_id}','denied')">Deny</button>
        <button class="ghost" onclick="decide('${a.approval_id}','escalated')">Escalate</button>
      </div>
    </div>`).join("");
}
window.decide = async (id, decision) => {
  await api(`/v1/approvals/${id}/decide`, { method: "POST", body: JSON.stringify({ decision, by: "console-user" }) });
  setStatus(`approval ${decision}`);
  refresh();
};

// ----------------------------------------------------------------- incidents
$("#scan-all").addEventListener("click", async () => {
  const tasks = await api("/v1/tasks");
  let all = [];
  for (const t of tasks) all = all.concat(await api(`/v1/tasks/${t.task_id}/incidents/scan`, { method: "POST" }));
  renderIncidents(all);
  setStatus(`scanned ${tasks.length} tasks · ${all.length} incident(s)`);
});
function renderIncidents(list) {
  const el = $("#incident-list");
  if (!list.length) { el.innerHTML = `<div class="empty">No incidents detected. ✓</div>`; return; }
  el.innerHTML = list.map((i) => `
    <div class="incident sev-${i.severity}">
      <div class="i-head"><b>${esc(i.category)}</b> ${pill(i.severity === "critical" || i.severity === "high" ? "failed" : "pending")}<span class="dim">${i.severity}</span></div>
      <div>${esc(i.description)}</div>
      <div class="dim" style="margin-top:6px"><b>Root cause:</b> ${esc(i.root_cause || "—")}</div>
      <div class="dim"><b>Remediation:</b> ${esc(i.remediation || "—")}</div>
      <div class="dim"><b>Rollback:</b> ${esc(i.rollback_hint || "—")}</div>
    </div>`).join("");
}

// ------------------------------------------------------------------ evidence
$("#gen-evidence").addEventListener("click", async () => {
  const fw = $("#framework").value;
  try { $("#evidence-out").textContent = await api(`/v1/evidence/${fw}/report`); }
  catch (e) { $("#evidence-out").textContent = "Error: " + e.message; }
});

refresh();
setInterval(loadApprovalBadge, 8000);

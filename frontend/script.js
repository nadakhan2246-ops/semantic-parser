// Frontend logic: hash-routed views, talks to the Flask API with fetch() and renders results without page reloads.
"use strict";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const STAGE_INFO = {
  "User Input": "The raw sentence exactly as entered, before any change.",
  "Text Preprocessing": "Trim spaces, correct near-miss typos, lowercase and strip punctuation.",
  "Tokenization": "Split the sentence into individual word and punctuation tokens.",
  "Semantic Parsing": "Find the action verb, its object, the question word and prepositional relations.",
  "Entity Extraction": "Detect places (with roles), dates, objects and names using gazetteers and patterns.",
  "Intent Classification": "Score each intent's patterns. Weak matches are reported as UNKNOWN.",
  "Semantic Interpretation": "Combine the results into a meaning frame and a plain-English explanation.",
  "Structured Output": "Return the final JSON that another program can use.",
};
const ROUTES = ["home", "analyzer", "pipeline", "playground", "history"];
let busy = false, lastJson = "", pipelineNames = Object.keys(STAGE_INFO);

/* ---------- small UI helpers ---------- */
function toast(msg, isError) {
  const t = document.createElement("div");
  t.className = "toast" + (isError ? " err" : ""); t.textContent = msg;
  $("toasts").appendChild(t);
  setTimeout(() => { t.classList.add("out"); setTimeout(() => t.remove(), 350); }, 2600);
}
function showError(msg) { $("error").textContent = msg; $("error").hidden = !msg; }
function setStatus(state, text) { $("status").dataset.state = state; $("statusText").textContent = text; }

async function api(url, options) {
  let res, data;
  try { res = await fetch(url, options); } catch { throw new Error("Cannot reach the server. Is the Flask app running?"); }
  try { data = await res.json(); } catch { throw new Error("The server sent an unreadable response."); }
  if (!data.success) throw new Error(data.error || "Something went wrong.");
  return data;
}

/* ---------- router ---------- */
function currentRoute() {
  const m = location.hash.match(/^#\/([a-z]+)/);
  return m && ROUTES.includes(m[1]) ? m[1] : "home";
}
function route() {
  const name = currentRoute();
  document.querySelectorAll(".view").forEach((v) => { v.hidden = v.dataset.view !== name; });
  document.querySelectorAll("#navLinks a").forEach((a) => {
    const on = a.dataset.route === name;
    a.classList.toggle("active", on);
    if (on) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  const titles = { home: "Semantic Parser | Natural Language Understanding" };
  document.title = titles[name] || `${name[0].toUpperCase() + name.slice(1)} | Semantic Parser`;
  menu(false);
  window.scrollTo(0, 0);
  if (name === "history") loadHistory();
  if (name === "analyzer" && !busy) setTimeout(() => $("textInput").focus({ preventScroll: true }), 0);
}
function go(name) { if (currentRoute() === name && location.hash) route(); else location.hash = "#/" + name; }

/* ---------- pipeline ---------- */
function renderFlow(el, stages, animate) {
  el.innerHTML = stages.map((s) => `<li><b>${esc(s.name)}</b><small>${esc(s.detail)}</small></li>`).join("");
  [...el.children].forEach((li, i) => {
    if (animate && !reduceMotion) setTimeout(() => li.classList.add("done"), 90 * i); else li.classList.add("done");
  });
}
function renderPipelinePage(names) {
  $("pipeline").innerHTML = names.map((n) => `<li><b>${esc(n)}</b><span>${esc(STAGE_INFO[n] || "")}</span></li>`).join("");
  $("homeFlow").innerHTML = names.map((n) => `<li><b>${esc(n)}</b></li>`).join("");
}

/* ---------- results ---------- */
function node(label, value) { return `<div class="node"><small>${esc(label)}</small><b>${esc(value)}</b></div>`; }

function renderParse(r) {
  const p = r.parse;
  const nodes = [["Action", p.action], ["Subject", p.subject], ["Object", p.object], ["Topic", p.topic], ["Question word", p.question_word], ["Expresses want", p.wants ? "yes" : null]].filter((x) => x[1]);
  const rels = p.relations.filter((x) => x.dependent);
  if (!nodes.length && !rels.length) return '<p class="empty">No verb, object or relations were found in this sentence.</p>';
  const tree = `<div class="tree"><div class="root">${esc(r.original.trim())}</div><div class="stem"></div>` +
    `<div class="branches">${nodes.map(([k, v]) => node(k, v)).join("")}</div></div>`;
  const relHtml = rels.length ? `<div class="rels">${rels.map((x) =>
    `<div class="rel"><span class="w">${esc(x.head || "(start)")}</span><span class="a">&mdash;<em>${esc(x.relation)}</em>&rarr;</span><span class="w">${esc(x.dependent)}</span></div>`).join("")}</div>` : "";
  return tree + relHtml;
}

function renderEntities(e) {
  const rows = [];
  e.locations.forEach((l) => rows.push(["Place", `${esc(l.text)}<i>${esc(l.role)}</i>`]));
  e.dates.forEach((d) => rows.push(["Date", esc(d)]));
  e.objects.forEach((o) => rows.push(["Object", esc(o)]));
  e.people.forEach((n) => rows.push(["Name", esc(n)]));
  return rows.length ? rows.map(([k, v]) => `<div class="ent"><span class="k">${k}</span><span class="v">${v}</span></div>`).join("") : '<p class="empty">No entities found.</p>';
}

function renderIntent(i) {
  const pct = Math.round(i.confidence * 100);
  const scores = Object.entries(i.scores || {}).sort((a, b) => b[1] - a[1]);
  $("rIntent").innerHTML = `<div class="intent-name">${esc(i.intent)}</div><p>${esc(i.description)}</p>` +
    `<div class="meter" role="progressbar" aria-label="Confidence" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><i id="meterFill"></i></div><small>Confidence: ${pct}%</small>` +
    `<div class="scores">${scores.map(([k, v]) => `<div class="score${k === i.intent ? " top" : ""}"><span>${esc(k)}</span><span class="bar"><i style="width:${Math.round(v * 100)}%"></i></span><span>${Math.round(v * 100)}%</span></div>`).join("")}</div>`;
  requestAnimationFrame(() => { const f = $("meterFill"); if (f) f.style.width = pct + "%"; });
}

function render(r) {
  $("results").hidden = false;
  renderFlow($("liveFlow"), r.stages, true);
  $("resultMeta").textContent = `${r.tokens.length} tokens, ${r.intent.intent}, ${Math.round(r.intent.confidence * 100)}% confidence`;
  $("rOriginal").textContent = r.original;
  $("rPre").textContent = r.preprocessed || "(empty)";
  $("rFixes").innerHTML = (r.corrections || []).map((c) => `<span class="fix">${esc(c.from)} &rarr; ${esc(c.to)}</span>`).join(" ");
  $("rTokCount").textContent = `(${r.tokens.length})`;
  $("rTokens").innerHTML = r.tokens.length ? r.tokens.map((t) => `<span class="chip tok">${esc(t)}</span>`).join("") : '<p class="empty">No tokens.</p>';
  $("rEntities").innerHTML = renderEntities(r.entities);
  renderIntent(r.intent);
  $("rParse").innerHTML = renderParse(r);
  $("rInterp").textContent = r.interpretation;
  $("rNotes").innerHTML = r.notes.map((n) => `<li>${esc(n)}</li>`).join("");
  lastJson = JSON.stringify(r.semantic_frame, null, 2);
  $("rJson").textContent = lastJson;
  const g = document.querySelector("#results .grid"); g.classList.remove("reveal"); void g.offsetWidth; g.classList.add("reveal");
}

/* ---------- actions ---------- */
function setBusy(on) {
  busy = on;
  $("analyzeBtn").disabled = on; $("analyzeBtn").classList.toggle("busy", on);
  $("analyzeBtn").querySelector(".btn-label").textContent = on ? "Analyzing" : "Analyze Sentence";
  if (on) setStatus("busy", "Processing sentence");
}

async function analyze(text) {
  if (busy) return;
  showError("");
  if (!text.trim()) { showError("Please enter a sentence to analyze."); setStatus("error", "Input required"); $("textInput").focus(); return; }
  setBusy(true);
  try {
    const data = await api("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
    render(data.result);
    setStatus("done", "Analysis complete");
    if (data.warning) toast(data.warning, true);
    toast(data.result.intent.intent === "UNKNOWN" ? "Analysis finished: no supported intent found." : "Analysis complete: " + data.result.intent.intent);
    loadHistory();
    $("results").scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
  } catch (err) { showError(err.message); setStatus("error", "Analysis failed"); toast(err.message, true); }
  finally { setBusy(false); }
}

function fmtTime(s) {
  const d = new Date(String(s).replace(" ", "T") + "Z");
  return isNaN(d) ? "" : d.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

async function loadHistory() {
  try {
    const data = await api("/api/history");
    const total = data.total ?? data.history.length;
    $("statHistory").textContent = total;
    $("historyCount").textContent = `${total} ${total === 1 ? "analysis" : "analyses"}` + (total > data.history.length ? `, showing latest ${data.history.length}` : "");
    $("historyEmpty").hidden = data.history.length > 0;
    $("historyBody").innerHTML = data.history.map((h) =>
      `<tr><td class="num">${h.id}</td><td class="sent">${esc(h.sentence)}</td><td><span class="tag${h.intent === "UNKNOWN" ? " unknown" : ""}">${esc(h.intent)}</span></td>` +
      `<td class="time">${esc(fmtTime(h.created_at))}</td><td class="act"><button type="button" class="btn small ghost" data-id="${h.id}" aria-label="View analysis: ${esc(h.sentence)}">View Analysis</button></td></tr>`).join("");
  } catch (err) { toast(err.message, true); }
}

function resetInput() {
  $("textInput").value = ""; updateCount(); showError(""); $("results").hidden = true; setStatus("idle", "Ready");
}
function updateCount() { $("charCount").textContent = `${$("textInput").value.length} / 500`; }

function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
  return new Promise((ok, fail) => {                       // fallback for non-secure contexts
    const t = document.createElement("textarea"); t.value = text; t.style.position = "fixed"; t.style.opacity = "0";
    document.body.appendChild(t); t.select();
    try { document.execCommand("copy") ? ok() : fail(new Error("copy failed")); } catch (e) { fail(e); } finally { t.remove(); }
  });
}

function confirmClear() {
  return new Promise((resolve) => {
    const m = $("confirmModal"); m.hidden = false; $("confirmNo").focus();
    const done = (v) => { m.hidden = true; $("confirmYes").onclick = $("confirmNo").onclick = m.onclick = null; document.removeEventListener("keydown", onKey); resolve(v); };
    const onKey = (e) => { if (e.key === "Escape") done(false); };
    document.addEventListener("keydown", onKey);
    $("confirmYes").onclick = () => done(true); $("confirmNo").onclick = () => done(false);
    m.onclick = (e) => { if (e.target === m) done(false); };
  });
}

/* ---------- wiring ---------- */
$("analyzeBtn").onclick = () => analyze($("textInput").value);
$("clearBtn").onclick = () => { resetInput(); toast("Input cleared."); $("textInput").focus(); };
$("textInput").addEventListener("input", () => { updateCount(); if ($("error").textContent) showError(""); });
$("textInput").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); analyze($("textInput").value); } });
$("exampleChips").onclick = (e) => { const b = e.target.closest("[data-s]"); if (b) { $("textInput").value = b.dataset.s; updateCount(); showError(""); setStatus("idle", "Ready"); $("textInput").focus(); } };
$("playgroundGrid").onclick = (e) => {
  const b = e.target.closest("[data-s]"); if (!b) return;
  $("textInput").value = b.dataset.s; updateCount(); showError("");
  go("analyzer"); analyze(b.dataset.s);
};
$("historyBody").onclick = async (e) => {
  const b = e.target.closest("[data-id]"); if (!b) return;
  try {
    const d = await api("/api/history/" + b.dataset.id);
    $("textInput").value = d.result.original; updateCount(); showError(""); setStatus("idle", "Loaded from history");
    go("analyzer"); render(d.result); toast("Loaded a previous analysis.");
    setTimeout(() => $("results").scrollIntoView({ behavior: "auto", block: "start" }), 30);
  } catch (err) { toast(err.message, true); }
};
$("refreshHistoryBtn").onclick = () => loadHistory();
$("clearHistoryBtn").onclick = async () => {
  if (!(await confirmClear())) return;
  try { await api("/api/history", { method: "DELETE" }); await loadHistory(); toast("History cleared."); }
  catch (err) { toast(err.message, true); }
};
$("copyBtn").onclick = async () => {
  if (!lastJson) { toast("Nothing to copy yet.", true); return; }
  try { await copyText(lastJson); $("copyBtn").textContent = "Copied"; toast("JSON copied to clipboard."); setTimeout(() => ($("copyBtn").textContent = "Copy JSON"), 1500); }
  catch { toast("Copy failed. Select the JSON and copy it manually.", true); }
};
function menu(open) { $("navLinks").classList.toggle("open", open); $("menuBtn").setAttribute("aria-expanded", String(open)); }
$("menuBtn").onclick = () => menu(!$("navLinks").classList.contains("open"));
document.addEventListener("keydown", (e) => { if (e.key === "Escape") menu(false); });
window.addEventListener("resize", () => { if (window.innerWidth > 820) menu(false); });
window.addEventListener("hashchange", route);

async function init() {
  updateCount();
  renderPipelinePage(pipelineNames);
  route();
  const ex = await api("/api/examples");
  pipelineNames = ex.pipeline;
  renderPipelinePage(pipelineNames);
  $("exampleChips").innerHTML = ex.examples.slice(0, 4).map((s) => `<button type="button" class="chip" data-s="${esc(s)}">${esc(s)}</button>`).join("");
  $("playgroundGrid").innerHTML = ex.examples.map((s) => `<button type="button" class="play" data-s="${esc(s)}"><span class="tag-row">Example sentence</span><span>${esc(s)}</span><span class="go">Analyze this sentence</span></button>`).join("");
  await loadHistory();
}
init().catch((err) => { toast(err.message, true); });

"use strict";
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
let state = { sid: null, meta: null, subject: "", provider: "offline" };

async function api(path, opts = {}) {
  const r = await fetch(path, opts);
  return r.json();
}
function post(path, data) {
  return api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
}
function toast(msg) {
  const t = document.createElement("div"); t.className = "toast"; t.textContent = msg;
  document.body.appendChild(t); setTimeout(() => t.remove(), 2200);
}
function status(msg) { $("#statusBar").textContent = "● " + msg; }

function md(text) {
  return (text || "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/^### (.*)$/gm, "<h3>$1</h3>").replace(/^## (.*)$/gm, "<h3>$1</h3>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

async function init() {
  state.meta = await api("/api/meta");
  state.provider = state.meta.config.provider;
  // subject selects
  const opts = state.meta.subjects.map((s) => `<option value="${s}">${s}</option>`).join("");
  $("#subjectSelect").innerHTML = `<option value="">通用 / 不限学科</option>` + opts;
  $("#examSelect").innerHTML = state.meta.exams.map((e) => `<option value="${e.code}">${e.name} (${e.score})</option>`).join("");
  fillSettings(state.meta.config);
  await loadSessions();
  await loadBank();
  status("就绪 · " + providerName(state.provider));
}

function providerName(p) {
  return { offline: "离线导学", openai: "API 模式", ollama: "本地模型" }[p] || p;
}

// ---- tabs ----
$$(".tab").forEach((tab) => tab.addEventListener("click", () => {
  $$(".tab").forEach((t) => t.classList.remove("active"));
  $$(".view").forEach((v) => v.classList.remove("active"));
  tab.classList.add("active");
  $("#view-" + tab.dataset.tab).classList.add("active");
  if (tab.dataset.tab === "review") loadCards();
  if (tab.dataset.tab === "artifacts") loadArtifacts();
}));

// ---- sessions ----
async function loadSessions() {
  const list = await api("/api/sessions");
  const box = $("#sessionList");
  box.innerHTML = list.map((s) =>
    `<div class="sitem ${s.id === state.sid ? "active" : ""}" data-id="${s.id}">
       <span>💬 ${s.title || "会话"}</span><span class="del" data-del="${s.id}">✕</span></div>`).join("");
  $$(".sitem").forEach((el) => el.addEventListener("click", async (e) => {
    if (e.target.dataset.del) {
      await post("/api/session/delete", { sid: e.target.dataset.del });
      if (state.sid === e.target.dataset.del) state.sid = null;
      return loadSessions();
    }
    state.sid = el.dataset.id;
    const msgs = await api("/api/messages?sid=" + state.sid);
    renderChat(msgs); loadSessions();
  }));
}

$("#newSession").addEventListener("click", async () => {
  const subject = $("#subjectSelect").value;
  const r = await post("/api/session/new", { title: "新会话 " + new Date().toLocaleTimeString(), subject });
  state.sid = r.sid;
  $("#chatBox").innerHTML = `<div class="empty">新会话已建立,输入你的问题吧 👋</div>`;
  await loadSessions();
  $$(".tab").find((t) => t.dataset.tab === "chat").click();
  toast("新会话已建立");
});

function renderChat(msgs) {
  const box = $("#chatBox");
  box.innerHTML = "";
  msgs.forEach((m) => {
    const d = document.createElement("div");
    d.className = "msg " + m.role;
    d.innerHTML = md(m.content);
    box.appendChild(d);
  });
  box.scrollTop = box.scrollHeight;
}

async function send() {
  const input = $("#questionInput");
  const q = input.value.trim();
  if (!q) return;
  if (!state.sid) {
    const r = await post("/api/session/new", { title: q.slice(0, 16), subject: $("#subjectSelect").value });
    state.sid = r.sid; await loadSessions();
  }
  //  optimistic display
  const box = $("#chatBox");
  $("#chatEmpty")?.remove();
  const u = document.createElement("div"); u.className = "msg user"; u.textContent = q; box.appendChild(u);
  const wait = document.createElement("div"); wait.className = "msg assistant"; wait.textContent = "思考中…"; box.appendChild(wait);
  box.scrollTop = box.scrollHeight;
  input.value = "";
  status("正在生成…");
  const r = await post("/api/chat", { sid: state.sid, question: q, subject: $("#subjectSelect").value });
  wait.innerHTML = md(r.reply);
  box.scrollTop = box.scrollHeight;
  status("就绪 · " + providerName(state.provider));
}
$("#sendBtn").addEventListener("click", send);
$("#questionInput").addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.key === "Enter") send();
});

// ---- board ----
$("#boardBtn").addEventListener("click", async () => {
  const question = $("#boardQuestion").value.trim();
  const answer = $("#boardAnswer").value.trim();
  if (!question && !answer) { toast("请填题目或解答"); return; }
  status("生成板书…");
  const r = await post("/api/board", { question, answer });
  $("#boardOut").innerHTML = r.steps.map((s, i) =>
    `<div class="step"><h4>步骤 ${i + 1} · ${s.title}</h4><p>${md(s.body)}</p></div>`).join("");
  status("就绪");
});

// ---- review ----
async function loadCards() {
  const cards = await api("/api/cards?due=0");
  $("#cardList").innerHTML = cards.length ? cards.map((c) =>
    `<div class="card" data-id="${c.id}">
       <div class="q">${md(c.question)}</div>
       <div class="a">${md(c.answer)}</div>
       <div class="row">
         <button class="ghost act" data-q="1">忘了</button>
         <button class="ghost act" data-q="3">模糊</button>
         <button class="ghost act" data-q="5">记住了</button>
         <span class="meta">复习 ${c.reps} 次 · 间隔 ${c.interval} 天</span>
         <button class="ghost delc" data-id="${c.id}">删除</button>
       </div></div>`).join("") : `<div class="empty">还没有卡片。去「学习产物」生成抽认卡，或手动添加。</div>`;
  $$(".card .act").forEach((b) => b.addEventListener("click", async () => {
    const id = b.closest(".card").dataset.id;
    await post("/api/card/review", { id: Number(id), quality: Number(b.dataset.q) });
    toast("已记录,下次复习已排期"); loadCards();
  }));
  $$(".card .delc").forEach((b) => b.addEventListener("click", async () => {
    await post("/api/card/delete", { id: Number(b.dataset.id) }); loadCards();
  }));
}
$("#loadCards").addEventListener("click", loadCards);

// ---- artifacts ----
async function loadArtifacts() {
  if (!state.sid) { $("#artifactList").innerHTML = `<div class="empty">先建一个会话并对话,再生成产物。</div>`; return; }
  const list = await api("/api/artifacts?sid=" + state.sid);
  $("#artifactList").innerHTML = list.length ? list.map((a) =>
    `<div class="artifact"><h4>${a.title} · v${a.version}</h4><pre>${md(a.content)}</pre></div>`).join("")
    : `<div class="empty">还没有产物。点上方按钮生成。</div>`;
}
$$(".artifact-actions button").forEach((b) => b.addEventListener("click", async () => {
  if (!state.sid) { toast("请先建会话并对话"); return; }
  status("生成中…");
  await post("/api/artifact", { sid: state.sid, kind: b.dataset.kind, subject: $("#subjectSelect").value });
  await loadArtifacts(); toast("已生成"); status("就绪");
}));

// ---- exam bank ----
async function loadBank() {
  const code = $("#examSelect").value || "MATH";
  const qs = await post("/api/question/bank", { code });
  $("#questionBank").innerHTML = qs.length ? qs.map((x, i) =>
    `<div class="card"><div class="q">${i + 1}. ${md(x.q)}</div>
       <div class="a">提示：点对话页把这道题发给导师,让它一步步引导你。</div></div>`).join("")
    : `<div class="empty">该科目暂无示例题,可在 curriculum.py 里扩展。</div>`;
}
$("#examSelect").addEventListener("change", loadBank);

// ---- settings ----
function fillSettings(cfg) {
  $("#providerSelect").value = cfg.provider;
  $("#baseUrl").value = cfg.base_url || "";
  $("#apiKey").value = "";
  $("#apiKey").placeholder = cfg.api_key_set ? "已设置密钥（留空保留）" : "输入 API Key";
  $("#modelName").value = cfg.model || "";
  $("#ollamaUrl").value = cfg.ollama_base_url || "";
  $("#ollamaModel").value = cfg.ollama_model || "";
  toggleFields();
}
function toggleFields() {
  const p = $("#providerSelect").value;
  $("#apiFields").style.display = p === "openai" ? "block" : "none";
  $("#ollamaFields").style.display = p === "ollama" ? "block" : "none";
}
$("#providerSelect").addEventListener("change", toggleFields);
$("#saveConfig").addEventListener("click", async () => {
  const patch = {
    provider: $("#providerSelect").value,
    base_url: $("#baseUrl").value.trim(),
    api_key: $("#apiKey").value.trim(),
    model: $("#modelName").value.trim(),
    ollama_base_url: $("#ollamaUrl").value.trim(),
    ollama_model: $("#ollamaModel").value.trim(),
  };
  $("#configNote").textContent = "测试中…";
  const r = await post("/api/config", patch);
  state.provider = r.config.provider;
  $("#configNote").textContent = (r.ok ? "✅ " : "⚠️ ") + r.note;
  status("就绪 · " + providerName(state.provider));
  fillSettings(r.config);
});

init();

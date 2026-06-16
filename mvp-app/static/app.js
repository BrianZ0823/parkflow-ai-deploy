if (location.protocol === "file:") {
  location.replace("http://127.0.0.1:8765/");
  throw new Error("Please open ParkFlow through the local web server.");
}

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const API_BASE = String(window.PARKFLOW_API_BASE || "").replace(/\/$/, "");

function apiUrl(path) {
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

async function downloadFile(url, body, filename) {
  const resp = await fetch(apiUrl(url), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    let errMsg = `导出失败 (${resp.status})`;
    try {
      const err = await resp.json();
      if (err && err.error) errMsg = err.error;
    } catch (_) {}
    throw new Error(errMsg);
  }
  const contentType = resp.headers.get("Content-Type") || "";
  if (contentType.includes("application/json")) {
    const json = await resp.json();
    throw new Error(json.error || "导出服务返回异常");
  }
  const blob = await resp.blob();
  if (!blob || blob.size === 0) {
    throw new Error("导出的文件为空，请重试");
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

const ui = {
  homeView: $("#homeView"),
  agentWorkspace: $("#agentWorkspace"),
  homeForm: $("#homeForm"),
  homeInput: $("#homeInput"),
  recentThreads: $("#recentThreads"),
  openHistoryFromHome: $("#openHistoryFromHome"),
  form: $("#analysisForm"),
  input: $("#taskInput"),
  thread: $("#messageList"),
  threadScroll: $("#threadScroll"),
  brandHomeButton: $("#brandHomeButton"),
  currentProject: $("#currentProject"),
  corpusDetail: $("#corpusDetail"),
  health: $("#health"),
  agentStatus: $("#agentStatus"),
  commandChips: $("#commandChips"),
  historyButton: $("#historyButton"),
  historyClose: $("#historyClose"),
  historyDrawer: $("#historyDrawer"),
  drawerOverlay: $("#drawerOverlay"),
  historyList: $("#historyList"),
  newThreadButton: $("#newThreadButton"),
  goalUnderstanding: $("#goalUnderstanding"),
  sourceList: $("#sourceList"),
  criteriaList: $("#criteriaList"),
  activeCompany: $("#activeCompany"),
  riskList: $("#riskList"),
  nextActions: $("#nextActions"),
  dialog: $("#sourceDialog"),
  dialogClose: $("#dialogClose"),
  homeHint: $("#homeHint"),
  shelf: $("#shortlistShelf"),
  shelfTab: $("#shelfTab"),
  shelfCount: $("#shelfCount"),
  shelfList: $("#shelfList"),
  shelfCompare: $("#shelfCompare"),
  shelfBatchOutline: $("#shelfBatchOutline"),
};

const state = {
  threadId: createThreadId(),
  threads: [],
  persistTimer: null,
  currentGoal: "",
  selectedCompanyIndex: -1,
  lastSummary: "",
  report: null,
  context: null,
  sources: [],
  actions: [],
  candidates: [],
  shortlist: [],
  history: [],
  currentAgentMessage: null,
  lastMaterial: null,
  activityItems: [],
  streamingText: "",
  jsonBuffer: "",
  shelfSelection: new Set(),
  receivedTextDelta: false,
  debugMode: false,
  liveTimer: null,
  liveTick: 0,
  currentAbort: null,
  stopRequested: false,
  messageSeq: 0,
};

const ACTION_TYPES = {
  local: "local_state_action",
  light: "light_update_action",
  agent: "agent_generation_action",
};

const THREAD_STORAGE_KEY = "parkflow_threads_v1";
const THREAD_LIMIT = 24;

const FALLBACK_CRITERIA = ["产业匹配", "承载能力", "成长潜力", "风险可控"];

const activityMap = [
  [/理解|目标|任务|需求|意图/i, ["解析目标", "识别招商目标、数量要求与交付方向。"]],
  [/企业|候选|公司|线索|数据库|读取/i, ["发现企业线索", "从本地企业线索中筛选与目标匹配的对象。"]],
  [/政策|资源|抓手/i, ["匹配政策机会", "整理可用于推进的政策机会与园区资源。"]],
  [/排序|评分|筛选|匹配|租金|贡献|成长/i, ["形成优先级", "比较产业匹配、承载能力、成长性和稳定性。"]],
  [/风险|核验|风险等级/i, ["识别风险因素", "标出推进前需要复核的事项。"]],
  [/生成|分析|报告|结论|建议|材料/i, ["形成招商建议", "形成推荐企业、推荐理由和下一步推进建议。"]],
];

function createThreadId() {
  return `thread_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

function loadThreads() {
  try {
    const raw = localStorage.getItem(THREAD_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    state.threads = Array.isArray(parsed) ? parsed.filter((item) => item?.id).slice(0, THREAD_LIMIT) : [];
  } catch {
    state.threads = [];
  }
}

function saveThreads() {
  try {
    localStorage.setItem(THREAD_STORAGE_KEY, JSON.stringify(state.threads.slice(0, THREAD_LIMIT)));
  } catch {
    showToast("本地线程保存失败，请检查浏览器存储权限", "warn");
  }
}

function isThreadMeaningful() {
  return Boolean(
    state.currentGoal ||
    state.history.length ||
    state.candidates.length ||
    state.shortlist.length ||
    ui.thread?.innerHTML.trim()
  );
}

function snapshotThread() {
  if (!isThreadMeaningful()) return null;
  const title = compactText(state.currentGoal || state.history.find((item) => item.role === "user")?.content || "未命名招商任务", 42);
  return {
    id: state.threadId,
    title,
    currentGoal: state.currentGoal,
    updatedAt: Date.now(),
    createdAt: state.threads.find((item) => item.id === state.threadId)?.createdAt || Date.now(),
    messages: state.history,
    artifacts: {
      report: state.report,
      candidates: state.candidates,
      shortlist: state.shortlist,
      followupList: state.shortlist,
      sources: state.sources,
      actions: state.actions,
    },
    followupList: state.shortlist,
    selectedCompanyIndex: state.selectedCompanyIndex,
    lastSummary: state.lastSummary,
    context: state.context,
    threadHtml: ui.thread?.innerHTML || "",
  };
}

function persistCurrentThread() {
  const snapshot = snapshotThread();
  if (!snapshot) return;
  const next = state.threads.filter((item) => item.id !== snapshot.id);
  state.threads = [snapshot, ...next].slice(0, THREAD_LIMIT);
  saveThreads();
  renderRecentThreads();
  renderHistoryList();
}

function queuePersistThread() {
  window.clearTimeout(state.persistTimer);
  state.persistTimer = window.setTimeout(persistCurrentThread, 220);
}

function formatThreadTime(value) {
  if (!value) return "刚刚";
  const date = new Date(value);
  const now = Date.now();
  if (now - value < 60_000) return "刚刚";
  if (now - value < 86_400_000) {
    return date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false });
  }
  return date.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
}

function renderThreadCard(thread, compact = false) {
  const companies = thread.artifacts?.candidates?.length || 0;
  const shortlist = thread.artifacts?.shortlist?.length || 0;
  const summary = thread.lastSummary || thread.messages?.filter((item) => item.role === "assistant").at(-1)?.content || "已保存为可继续追问的招商线程。";
  return `
    <article class="${compact ? "recent-thread-card" : "history-thread-card"}" data-thread-id="${escapeHtml(thread.id)}">
      <button type="button" data-restore-thread="${escapeHtml(thread.id)}">
        <strong>${escapeHtml(thread.title || "未命名招商任务")}</strong>
        <span>${escapeHtml(compactText(summary, compact ? 72 : 110))}</span>
        <em>${escapeHtml(formatThreadTime(thread.updatedAt))} · ${companies} 家推荐 · ${shortlist} 家清单</em>
      </button>
      ${compact ? "" : `<button type="button" class="delete-thread" data-delete-thread="${escapeHtml(thread.id)}">删除</button>`}
    </article>
  `;
}

function renderRecentThreads() {
  if (!ui.recentThreads) return;
  const threads = state.threads.slice(0, 4);
  ui.recentThreads.innerHTML = threads.length
    ? threads.map((thread) => renderThreadCard(thread, true)).join("")
    : `
      <article class="empty-recent">
        <strong>还没有保存的招商线程</strong>
        <p>开始一个目标后，线程会自动保存，刷新页面也可以继续追问。</p>
      </article>
    `;
  bindThreadListActions(ui.recentThreads);
}

function renderHistoryList() {
  if (!ui.historyList) return;
  ui.historyList.innerHTML = state.threads.length
    ? state.threads.map((thread) => renderThreadCard(thread)).join("")
    : `<div class="history-empty"><strong>暂无历史任务</strong><p>新的招商目标会自动保存到这里。</p></div>`;
  bindThreadListActions(ui.historyList);
}

function bindThreadListActions(root) {
  root.querySelectorAll("[data-restore-thread]").forEach((button) => {
    button.addEventListener("click", () => restoreThread(button.dataset.restoreThread));
  });
  root.querySelectorAll("[data-delete-thread]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      deleteThread(button.dataset.deleteThread);
    });
  });
}

function showHomeView() {
  persistCurrentThread();
  document.body.dataset.view = "home";
  ui.homeView.hidden = false;
  ui.agentWorkspace.hidden = true;
  ui.currentProject.textContent = "当前任务：待开始";
  ui.agentStatus.textContent = "待命";
  setAgentState("idle");
  renderRecentThreads();
}

function showWorkspace() {
  document.body.dataset.view = "workspace";
  ui.homeView.hidden = true;
  ui.agentWorkspace.hidden = false;
  updateInsight();
  scrollThread();
}

function openHistoryDrawer() {
  renderHistoryList();
  ui.drawerOverlay.hidden = false;
  ui.historyDrawer.hidden = false;
  requestAnimationFrame(() => {
    ui.drawerOverlay.classList.add("visible");
    ui.historyDrawer.classList.add("open");
  });
}

function closeHistoryDrawer() {
  ui.drawerOverlay.classList.remove("visible");
  ui.historyDrawer.classList.remove("open");
  window.setTimeout(() => {
    ui.drawerOverlay.hidden = true;
    ui.historyDrawer.hidden = true;
  }, 180);
}

function restoreThread(threadId) {
  const thread = state.threads.find((item) => item.id === threadId);
  if (!thread) return;
  persistCurrentThread();
  stopLiveProgress(false);
  state.currentAbort?.abort();
  state.currentAbort = null;
  state.stopRequested = false;
  state.threadId = thread.id;
  state.currentGoal = thread.currentGoal || "";
  state.selectedCompanyIndex = Number.isFinite(thread.selectedCompanyIndex) ? thread.selectedCompanyIndex : -1;
  state.lastSummary = thread.lastSummary || "";
  state.report = thread.artifacts?.report || null;
  state.context = thread.context || null;
  state.sources = thread.artifacts?.sources || [];
  state.actions = thread.artifacts?.actions || [];
  state.candidates = thread.artifacts?.candidates || [];
  state.shortlist = thread.followupList || thread.artifacts?.followupList || thread.artifacts?.shortlist || [];
  state.history = Array.isArray(thread.messages) ? thread.messages : [];
  state.currentAgentMessage = null;
  state.activityItems = [];
  state.streamingText = "";
  ui.thread.innerHTML = thread.threadHtml || "";
  ui.thread.querySelectorAll(".message").forEach((item) => {
    if (!item.dataset.messageRole) item.dataset.messageRole = item.classList.contains("user") ? "user" : "agent";
    if (!item.dataset.messageRaw) item.dataset.messageRaw = item.querySelector(".message-content")?.innerText || "";
  });
  ui.thread.querySelectorAll(".message").forEach((item) => {
    const role = item.dataset.messageRole || (item.classList.contains("user") ? "user" : "agent");
    if (!item.querySelector("[data-message-action]")) {
      item.querySelector(".message-body")?.insertAdjacentHTML("beforeend", messageActionsHtml(role));
    }
  });
  bindMessageActions(ui.thread);
  bindArtifactActions(ui.thread);
  bindPromptButtons(ui.thread);
  bindCommandActions(ui.thread);
  updateInsight();
  showWorkspace();
  closeHistoryDrawer();
  showToast("已恢复历史任务");
}

function deleteThread(threadId) {
  state.threads = state.threads.filter((item) => item.id !== threadId);
  saveThreads();
  renderRecentThreads();
  renderHistoryList();
  if (state.threadId === threadId) {
    resetThread({ showHome: true, persist: false });
  }
  showToast("已删除历史任务");
}

function startThreadFromGoal(goal) {
  const task = String(goal || "").trim();
  if (!task) return;
  const missing = detectMissingPlaceholder(task);
  if (missing) {
    showHomeHint(missing);
    ui.homeInput.focus();
    return;
  }
  showHomeHint("");
  resetThread({ showHome: false });
  state.currentGoal = task;
  showWorkspace();
  runMission(task);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function compactText(value, max = 160) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.length > max ? `${text.slice(0, max)}...` : text;
}

function detectMissingPlaceholder(task) {
  const text = task || "";
  if (/【企业名称】/.test(text)) return "请将【企业名称】替换为具体企业名称，例如：分析垂直起降动力有限公司是否适合重点推进。";
  if (/【产业方向】/.test(text)) return "请将【产业方向】替换为目标产业，例如：围绕低空经济梳理可优先推进的招商机会。";
  if (/【.+?】/.test(text)) return "请将【……】替换为具体内容后再开始分析。";
  return "";
}

function showHomeHint(message) {
  const el = ui.homeHint;
  if (!el) return;
  if (!message) {
    el.classList.remove("visible");
    el.textContent = "";
    return;
  }
  el.innerHTML = `<span class="hint-icon">!</span> ${message}`;
  el.classList.add("visible");
  el.addEventListener("transitionend", () => {
    if (!message) el.innerHTML = "";
  }, { once: true });
}

function showToast(message, tone = "default") {
  let host = document.querySelector(".toast-host");
  if (!host) {
    host = document.createElement("div");
    host.className = "toast-host";
    document.body.appendChild(host);
  }
  const item = document.createElement("div");
  item.className = `toast ${tone}`;
  item.textContent = message;
  host.appendChild(item);
  window.setTimeout(() => item.classList.add("visible"), 20);
  window.setTimeout(() => {
    item.classList.remove("visible");
    window.setTimeout(() => item.remove(), 220);
  }, 2600);
}

function sanitizeAgentText(value = "") {
  return String(value || "")
    .replace(/```(?:tool_code|python|javascript|json|js)?[\s\S]*?```/gi, "")
    .replace(/^.*```(?:tool_code|python|javascript|json|js)?.*$/gim, "")
    .replace(/`{3,}/g, "")
    .replace(/^\s*tool_code\s*$/gim, "")
    .replace(/mcp_[a-z0-9_]+(?:\.[a-z0-9_]+)?\([^)]*\)/gi, "")
    .replace(/^.*mcp_[a-z0-9_]+.*$/gim, "")
    .replace(/\(数据返回确认[:：]?[\s\S]*?\)/g, "")
    .replace(/^.*数据返回确认.*$/gim, "")
    .replace(/\brequested_industry\b/gi, "目标赛道")
    .replace(/\brequested_count\b/gi, "目标数量")
    .replace(/\bcandidate_enterprises\b/gi, "候选企业")
    .replace(/\bdiscovery_mode\b/gi, "线索发现模式")
    .replace(/\bget_company_risk\b/gi, "风险核验")
    .replace(/OPC企业池/g, "本地企业线索库")
    .replace(/OPC/g, "本地企业线索库")
    .replace(/risk_score\s*=\s*(\d+)/gi, "风险评分 $1")
    .replace(/\b(company_name|limit|tool|function|arguments)\s*=\s*/gi, "")
    .replace(/[✅🏢📊⭐📝⚠️📌❓]/g, "")
    .replace(/�/g, "")
    .replace(/^\s*---+\s*$/gm, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function formatBlocks(text) {
  const lines = sanitizeAgentText(text)
    .replace(/\*\*/g, "")
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) return "<p></p>";

  const chunks = [];
  let listType = "";
  let listItems = [];
  const flushList = () => {
    if (!listType) return;
    chunks.push(`<${listType}>${listItems.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</${listType}>`);
    listType = "";
    listItems = [];
  };

  lines.forEach((line) => {
    const bullet = line.match(/^[-*•]\s*(.+)$/);
    const numbered = line.match(/^(?:\d+[.)、]|[①②③④⑤⑥⑦⑧⑨⑩])\s*(.+)$/);
    if (bullet) {
      if (listType && listType !== "ul") flushList();
      listType = "ul";
      listItems.push(bullet[1]);
      return;
    }
    if (numbered) {
      if (listType && listType !== "ol") flushList();
      listType = "ol";
      listItems.push(numbered[1]);
      return;
    }
    flushList();
    chunks.push(`<p>${escapeHtml(line)}</p>`);
  });
  flushList();
  return chunks.join("");
}

function publicAnswerText(text = "") {
  const cleaned = sanitizeAgentText(text);
  const lines = cleaned
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => !/^(#{1,6}|```|---)/.test(line))
    .filter((line) => !/(等待.*返回|工具返回|工具调用|执行中[:：]|现在开始查询|我将基于|我将按|首先，我将|接下来将)/.test(line));
  return lines.join("\n") || "我可以继续帮你推进招商任务。";
}

function setAgentState(value) {
  document.body.dataset.agentState = value;
}

function scrollThread() {
  requestAnimationFrame(() => {
    ui.threadScroll.scrollTop = ui.threadScroll.scrollHeight;
  });
}

async function requestJson(url, options = {}) {
  const response = await fetch(apiUrl(url), {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.ok === false) {
    const error = new Error(payload.message || payload.error || `HTTP ${response.status}`);
    error.payload = payload;
    throw error;
  }
  return payload;
}

function selectedCompany() {
  return state.selectedCompanyIndex >= 0 ? state.candidates[state.selectedCompanyIndex] || null : null;
}

function fallbackCompanyForReference(task) {
  const text = task || "";
  const firstCompany = state.candidates[0] || null;
  if (/第\s*1\s*家|第一家|首家|排名第一/.test(text)) return firstCompany;
  if (/第\s*2\s*家|第二家/.test(text)) return state.candidates[1] || null;
  if (/第\s*3\s*家|第三家/.test(text)) return state.candidates[2] || null;
  return null;
}

function activeCompanyNameFor(task) {
  if (isAlternativeRecommendationRequest(task) || !isContextualFollowup(task) || !needsSelectedCompany(task)) return "";
  return selectedCompany()?.name || fallbackCompanyForReference(task)?.name || "";
}

function needsSelectedCompany(task = "") {
  if (isAlternativeRecommendationRequest(task)) return false;
  return /这家|该企业|这家公司|这个企业|当前企业|它|第\s*\d+\s*家|第一家|第二家|第三家|为什么推荐|适配吗|值得推进吗|拜访|提纲|邀约|话术|邀请函|邮件/.test(task);
}

function isAlternativeRecommendationRequest(task = "") {
  return /(还有|其他|换一批|再推荐|继续推荐|别的|其它).*(推荐|企业|公司|名单|线索)|这家.*(聊过|看过|排除|不要|不看).*(其他|推荐|企业|公司)/.test(task || "");
}

function buildThreadContext() {
  const active = selectedCompany() || null;
  const companiesForContext = state.candidates.map((item) => ({
    name: item.name,
    score: item.score,
    industry: [item.industry, item.subIndustry].filter(Boolean).join(" / "),
    reason: item.reason,
    risk_level: item.riskLevel,
    next_step: item.nextStep,
    revenue: item.revenue,
    financing: item.financing,
    patents: item.patents,
    employees: item.employees,
    region: item.region,
  }));
  return {
    thread_id: state.threadId,
    current_goal: state.currentGoal,
    selected_company: active?.name || "",
    active_company: active?.name || "",
    selected_company_profile: active ? {
      name: active.name,
      score: active.score,
      industry: [active.industry, active.subIndustry].filter(Boolean).join(" / "),
      reason: active.reason,
      risk_level: active.riskLevel,
      next_step: active.nextStep,
      revenue: active.revenue,
      financing: active.financing,
      patents: active.patents,
      employees: active.employees,
      region: active.region,
    } : null,
    last_summary: state.lastSummary,
    last_recommendation_companies: state.candidates.map((item) => item.name).filter(Boolean),
    shortlist: state.shortlist.map((item) => ({
      name: item.name,
      score: item.score,
      industry: [item.industry, item.subIndustry].filter(Boolean).join(" / "),
      reason: item.reason,
      added_at: item.addedAt,
    })),
    candidates: companiesForContext,
    history: state.history.slice(-10),
  };
}

function contextForTask(task) {
  // Always send thread context when it exists, not just when the text looks contextual.
  // The backend uses thread context for routing multi-round follow-ups correctly.
  const hasMemory = Boolean(state.currentGoal || state.report || state.candidates.length || state.history.length);
  return hasMemory ? buildThreadContext() : {};
}

function isContextualFollowup(task) {
  const text = task || "";
  const contextualTerms = [
    "这家", "该企业", "这家公司", "这个企业", "当前企业", "它", "他们",
    "第 1 家", "第1家", "第一家", "第 2 家", "第2家", "第二家",
    "刚才", "上面", "上述", "当前推荐", "这批", "这份", "基于",
    "为什么推荐", "展开说明", "适配吗", "值得推进吗", "筛选逻辑", "推荐逻辑", "展开逻辑",
  ];
  const materialTerms = ["邀约", "话术", "拜访", "提纲", "邀请函", "汇报", "材料", "邮件", "摘要"];
  const shortlistTerms = ["清单", "加入", "已加入", "跟进池", "名单"];
  const vagueDiscoveryTerms = ["推荐", "找", "筛选", "匹配", "调研", "盘点"];
  const explicitDomainTerms = ["芯片", "半导体", "医药", "生物", "低空", "人工智能", "新能源", "材料", "制造", "家居", "文创", "产业"];
  const hasThreadMemory = Boolean(state.currentGoal || state.history.length || state.candidates.length);
  const vagueFollowupDiscovery = hasThreadMemory
    && vagueDiscoveryTerms.some((term) => text.includes(term))
    && !explicitDomainTerms.some((term) => text.includes(term));
  return contextualTerms.some((term) => text.includes(term))
    || materialTerms.some((term) => text.includes(term))
    || shortlistTerms.some((term) => text.includes(term))
    || vagueFollowupDiscovery;
}

function isMaterialRequest(task = "") {
  return /生成|整理|导出|写|出一份|转成|压缩|汇报|摘要|材料|话术|邀约|邀请函|拜访|提纲|邮件|计划/.test(task || "");
}

function materialTypeFromTask(task = "") {
  const text = task || "";
  if (/对比|比较/.test(text)) return "comparison";
  if (/汇报|摘要|领导|简报|纪要/.test(text)) return "briefing";
  if (/邀约|话术|微信|电话|触达/.test(text)) return "wechat";
  if (/邀请函|邮件|email/i.test(text)) return "invite";
  if (/计划|推进/.test(text)) return "plan";
  if (/风险|核验/.test(text)) return "risk";
  return "outline";
}

function isStandaloneMission(task) {
  const text = task || "";
  const asksForDiscovery = /推荐|找出|筛选|寻找|哪些|一批|一些|盘点/.test(text);
  const hasDomain = /芯片|半导体|医药|低空|人工智能|新能源|材料|制造|企业|公司|产业/.test(text);
  return asksForDiscovery && hasDomain && !isContextualFollowup(text);
}

function isMetaConversation(task = "") {
  const text = task.trim();
  return /^(你好|hi|hello|你是谁|你能做什么|怎么使用|如何使用|帮助|help)[？?！!\s]*$/i.test(text)
    || /介绍一下你|你可以做什么/.test(text);
}

function isSimpleQuestion(task = "") {
  const text = (task || "").trim();
  if (/^(你|你这边|帮我)?(算|计算|算一下|等于|是多少|结果)[：:\s]?/.test(text)) return true;
  if (/[+\-*/÷×][=＝]|\d+[+\-*/÷×]\d+/.test(text)) return true;
  if (/^(好的|可以|行|谢谢|ok|好的谢谢|知道了|明白|嗯|对)$/i.test(text)) return true;
  if (/什么是|是什么意思|怎么用|如何/.test(text) && !/企业|产业|招商|政策/.test(text)) return true;
  if (text.length <= 15 && !/企业|产业|招商|政策|公司|推荐|筛选|分析/.test(text)) return true;
  return false;
}

async function quickAnswerFallback(task) {
  const text = (task || "").trim();
  if (/^[\d\s+\-*/÷×()]+[=＝]?\s*$/.test(text)) return null;
  if (/[+\-*/÷×][=＝]|\d+[+\-*/÷×]\d+/.test(text)) {
    try {
      const expr = text.replace(/[=＝].*$/, "").replace(/×/g, "*").replace(/÷/g, "/").replace(/[^0-9+\-*/().]/g, "");
      if (expr && !/[a-zA-Z]/.test(expr)) {
        const result = Function(`"use strict"; return (${expr})`)();
        return Number.isFinite(result) ? `${text.replace(/[=＝].*$/, "").trim()} = ${result}` : null;
      }
    } catch (_) {}
    return null;
  }
  if (/^(好的|可以|行|谢谢|ok|知道了|明白|嗯|对|好的谢谢|好的好的|ok谢谢)[!！\s]*$/i.test(text)) {
    return "好的，有什么需要继续了解的随时告诉我。";
  }
  return null;
}

function taskStatusFor(task = "") {
  const text = task || "";
  if (isMetaConversation(text)) return { label: "正在回复", detail: "正在理解你的问题" };
  if (isSimpleQuestion(text)) return { label: "正在回复", detail: "正在回答" };
  if (/对比|比较/.test(text) && /企业|公司|两家/.test(text)) return { label: "正在对比分析", detail: "正在对比企业能力、风险和招商优先级" };
  if (/生成|写|起草|话术|邀约|邀请函|拜访提纲|汇报材料/.test(text)) return { label: "正在生成材料", detail: "正在引用企业与产业资料，生成可使用的招商材料" };
  if (/政策|补贴|抓手/.test(text)) return { label: "正在分析政策", detail: "正在识别政策要点，匹配适用企业与产业方向" };
  if (/分析|评估|研判/.test(text)) return { label: "正在分析", detail: "正在综合企业画像、政策匹配与风险信息" };
  if (/筛选|推荐|找出|寻找|候选/.test(text)) return { label: "正在筛选", detail: "正在检索企业线索、匹配政策与产业机会" };
  return { label: "正在分析", detail: "正在处理你的请求" };
}

function requestedCountFromTask(task) {
  const text = task || "";
  const digit = text.match(/(\d+)\s*家/);
  if (digit) return Number(digit[1]);
  const chineseMap = { 一: 1, 二: 2, 两: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9, 十: 10 };
  const match = text.match(/([一二两三四五六七八九十])家/);
  return match ? chineseMap[match[1]] : null;
}

function addHistory(role, content) {
  const clean = compactText(content, 700);
  if (!clean) return;
  state.history.push({ role, content: clean });
  state.history = state.history.slice(-14);
  queuePersistThread();
}

function logRequestPayload(message, payload) {
  console.log("[ParkFlow request payload]", {
    threadId: state.threadId,
    message,
    selectedCompany: payload.selectedCompany || payload.company || "",
    currentGoal: state.currentGoal || message,
    lastRecommendationCompanies: state.candidates.map((item) => item.name).filter(Boolean),
    shortlistCompanies: state.shortlist.map((item) => item.name),
    conversationHistoryLength: state.history.length,
  });
}

function buildRequestPayload(message) {
  const company = activeCompanyNameFor(message);
  const payload = {
    task: message,
    message,
    threadId: state.threadId,
    selectedCompany: company,
    currentGoal: state.currentGoal || message,
    company,
    thread_context: contextForTask(message),
  };
  logRequestPayload(message, payload);
  return payload;
}

function roleForHistory(role) {
  return role === "agent" ? "assistant" : role;
}

function messageActionsHtml(role) {
  const actions = role === "user"
    ? [
        ["copy", "复制"],
        ["share", "分享"],
        ["edit", "修改"],
        ["retry", "重试"],
        ["delete", "删除"],
      ]
    : [
        ["copy", "复制"],
        ["share", "分享"],
        ["retry", "重试"],
        ["delete", "删除"],
      ];
  return `
    <div class="message-actions" aria-label="消息操作">
      ${actions.map(([action, label]) => `
        <button type="button" data-message-action="${action}" title="${label}" aria-label="${label}">
          <span>${label}</span>
        </button>
      `).join("")}
    </div>
  `;
}

function ensureMessageMeta(item, role, content = "") {
  if (!item.dataset.messageId) {
    state.messageSeq += 1;
    item.dataset.messageId = `msg_${Date.now().toString(36)}_${state.messageSeq}`;
  }
  item.dataset.messageRole = role;
  item.dataset.messageRaw = content || "";
}

function getMessageText(item) {
  const raw = item.dataset.messageRaw || "";
  const body = item.querySelector(".message-content")?.innerText || "";
  const artifactSlot = item.querySelector(".artifact-slot");
  const artifactText = artifactSlot ? extractArtifactContent(artifactSlot) : "";
  const parts = [raw || body];
  if (artifactText && !parts.includes(artifactText)) parts.push(artifactText);
  return parts.filter(Boolean).join("\n\n").trim();
}

function extractArtifactContent(slot) {
  const clone = slot.cloneNode(true);
  clone.querySelectorAll(
    ".artifact-toolbar, .artifact-header .artifact-kicker, footer, " +
    "button, .message-actions, .card-actions, .evidence-tags, " +
    ".metric span, .compare-head, .profile-grid dt, .material-card span:first-child"
  ).forEach((el) => el.remove());
  clone.querySelectorAll("[data-company-index], .company-card").forEach((el) => {
    const name = el.querySelector("strong")?.textContent || "";
    const reason = el.querySelector(".company-judgment")?.textContent || "";
    el.replaceWith(`${name}：${reason}`);
  });
  clone.querySelectorAll("dt, .metric strong").forEach((el) => el.remove());
  return clone.innerText.replace(/\n{3,}/g, "\n\n").trim();
}

function setMessageText(item, text) {
  const oldText = getMessageText(item);
  item.dataset.messageRaw = text;
  const content = item.querySelector(".message-content");
  if (content) content.innerHTML = formatBlocks(text);
  updateHistoryMessage(item, oldText, text);
  queuePersistThread();
}

function updateHistoryMessage(item, oldText, newText) {
  const role = roleForHistory(item.dataset.messageRole || "");
  const index = state.history.findIndex((entry) => entry.role === role && entry.content === oldText);
  if (index >= 0) state.history[index] = { ...state.history[index], content: newText };
}

async function copyText(text) {
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }
  showToast("已复制到剪贴板");
}

async function shareText(text) {
  if (!text) return;
  const title = state.currentGoal || "ParkFlow 招商线程";
  if (navigator.share) {
    try {
      await navigator.share({ title, text });
      return;
    } catch (error) {
      if (error.name === "AbortError") return;
    }
  }
  await copyText(`${title}\n\n${text}`);
  showToast("当前浏览器不支持系统分享，已复制内容");
}

function removeHistoryMessage(item, text) {
  const role = roleForHistory(item.dataset.messageRole || "");
  const index = state.history.findIndex((entry) => entry.role === role && entry.content === text);
  if (index >= 0) state.history.splice(index, 1);
}

function resetWorkspaceState() {
  state.currentGoal = "";
  state.selectedCompanyIndex = -1;
  state.lastSummary = "";
  state.report = null;
  state.context = null;
  state.sources = [];
  state.actions = [];
  state.candidates = [];
  state.shortlist = [];
  state.lastMaterial = null;
  state.activityItems = [];
  state.streamingText = "";
  state.jsonBuffer = "";
  state.receivedTextDelta = false;
}

function initDebugPanel() {
  const panel = document.getElementById("debugPanel");
  if (!panel) return;
  if (window.location.search.includes("debug=1")) {
    state.debugMode = true;
    panel.hidden = false;
    const closeBtn = document.getElementById("debugClose");
    if (closeBtn) closeBtn.addEventListener("click", () => { panel.hidden = true; state.debugMode = false; });
  }
}

function truncateThreadAt(messageElement) {
  const messages = [...ui.thread.querySelectorAll(".message")];
  const idx = messages.indexOf(messageElement);
  if (idx < 0) return;
  for (let i = messages.length - 1; i >= idx; i--) {
    messages[i].remove();
  }
  const targetText = getMessageText(messageElement);
  const role = messageElement.dataset.messageRole || "";
  let historyIdx = -1;
  for (let i = state.history.length - 1; i >= 0; i--) {
    if (state.history[i].role === role && state.history[i].content === targetText) {
      historyIdx = i;
      break;
    }
  }
  if (historyIdx >= 0) {
    state.history = state.history.slice(0, historyIdx);
  }
  queuePersistThread();
}

function editMessage(item) {
  if ((item.dataset.messageRole || "") !== "user") return;
  const text = getMessageText(item);
  const body = item.querySelector(".message-body");
  if (!body || body.querySelector(".message-edit-box")) return;
  item.classList.add("editing");
  const editor = document.createElement("div");
  editor.className = "message-edit-box";
  editor.innerHTML = `
    <textarea rows="3">${escapeHtml(text)}</textarea>
    <div>
      <button type="button" data-message-edit="cancel">取消</button>
      <button type="button" data-message-edit="save">保存并重新发送</button>
    </div>
  `;
  body.appendChild(editor);
  const textarea = editor.querySelector("textarea");
  textarea.focus();
  textarea.setSelectionRange(textarea.value.length, textarea.value.length);
  editor.querySelector("[data-message-edit='cancel']").addEventListener("click", () => {
    editor.remove();
    item.classList.remove("editing");
  });
  editor.querySelector("[data-message-edit='save']").addEventListener("click", () => {
    const next = textarea.value.trim();
    if (!next) return;
    editor.remove();
    item.classList.remove("editing");
    resetWorkspaceState();
    truncateThreadAt(item);
    runMission(next);
  });
}

function deleteMessage(item) {
  const text = getMessageText(item);
  removeHistoryMessage(item, text);
  item.remove();
  queuePersistThread();
  showToast("消息已删除");
}

function retryMessage(item) {
  let text = getMessageText(item);
  let target = item;
  if ((item.dataset.messageRole || "") === "agent") {
    const messages = [...ui.thread.querySelectorAll(".message")];
    const index = messages.indexOf(item);
    const previousUser = messages.slice(0, index).reverse().find((node) => node.dataset.messageRole === "user");
    if (previousUser) {
      text = getMessageText(previousUser);
      target = previousUser;
    }
  }
  if (!text) return;
  resetWorkspaceState();
  truncateThreadAt(target);
  ui.input.value = "";
  runMission(text);
}


function bindMessageActions(root = document) {
  root.querySelectorAll("[data-message-action]").forEach((button) => {
    if (button.dataset.bound === "true") return;
    button.dataset.bound = "true";
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const item = button.closest(".message");
      if (!item) return;
      const text = getMessageText(item);
      const action = button.dataset.messageAction;
      if (action === "copy") copyText(text);
      if (action === "share") shareText(text);
      if (action === "edit") editMessage(item);
      if (action === "retry") retryMessage(item);
      if (action === "delete") deleteMessage(item);
    });
  });
}

function addMessage(role, content = "") {
  const item = document.createElement("article");
  item.className = `message ${role}`;
  ensureMessageMeta(item, role, content);
  item.innerHTML = `
    <div class="avatar ${role === "user" ? "user-avatar" : "agent-avatar"}">${role === "user" ? "你" : ""}</div>
    <div class="message-body">
      <div class="message-meta">${role === "user" ? "你" : "ParkFlow"}<span>${role === "user" ? "已提交" : "正在协作"}</span></div>
      <div class="message-content">${formatBlocks(content)}</div>
    </div>
  `;
  item.querySelector(".message-body")?.insertAdjacentHTML("beforeend", messageActionsHtml(role));
  ui.thread.appendChild(item);
  bindMessageActions(item);
  scrollThread();
  return item;
}

function createAgentMessage() {
  const item = addMessage("agent", "");
  const body = item.querySelector(".message-body");
  body.innerHTML = `
    <div class="message-meta">ParkFlow<span>正在回复</span></div>
    <div class="live-status"><i aria-hidden="true"></i><span>正在处理</span></div>
    <div class="message-content agent-text"></div>
    <div class="artifact-slot"></div>
    ${messageActionsHtml("agent")}
  `;
  state.currentAgentMessage = item;
  bindMessageActions(item);
  return item;
}

function updateWorkstream(current = "") {
  const panel = state.currentAgentMessage?.querySelector("#activeWorkstream");
  if (!panel) return;
  const currentNode = panel.querySelector("[data-work-current]");
  const companyNode = panel.querySelector("[data-work-companies]");
  const sourceNode = panel.querySelector("[data-work-sources]");
  if (currentNode && current) currentNode.textContent = compactText(current, 18);
  if (companyNode) companyNode.textContent = state.candidates.length ? `${state.candidates.length} 家` : "检索中";
  if (sourceNode) sourceNode.textContent = visibleSources().length ? `${visibleSources().length} 条` : "整理中";
}

function stopCurrentRun() {
  state.stopRequested = true;
  state.currentAbort?.abort();
  stopLiveProgress(false);
  setLiveStatus("已停止本轮分析");
  setAgentState("ready");
  ui.agentStatus.textContent = "已停止";
  state.currentAgentMessage?.querySelector(".live-status")?.classList.add("done");
  state.currentAgentMessage?.querySelector("#activeWorkstream")?.classList.add("stopped");
  renderAgentText("已停止本轮分析。你可以补充条件后继续，我会沿用当前线程上下文。");
}

function setLiveStatus(text) {
  const status = state.currentAgentMessage?.querySelector(".live-status");
  const label = status?.querySelector("span");
  if (label) label.textContent = text;
}

function setConversationMode(detail = "正在回复") {
  const message = state.currentAgentMessage;
  if (!message) return;
  const meta = message.querySelector(".message-meta span");
  if (meta) meta.textContent = "正在回复";
  message.querySelector(".activity-timeline")?.remove();
  message.querySelector("#activeWorkstream")?.remove();
  message.querySelector(".live-status")?.classList.remove("done");
  setLiveStatus(detail || "正在回复");
  renderAgentText("我正在整理回复，请稍候。");
}

function startLiveProgress() {
  stopLiveProgress(false);
  const phrases = [
    "正在整理招商目标",
    "正在等待资料返回",
    "正在核对可用信息",
    "正在形成初步判断",
  ];
  state.liveTick = 0;
  setLiveStatus(phrases[0]);
  state.liveTimer = window.setInterval(() => {
    state.liveTick += 1;
    setLiveStatus(phrases[state.liveTick % phrases.length]);
  }, 1600);
}

function stopLiveProgress(markDone = true) {
  if (state.liveTimer) {
    window.clearInterval(state.liveTimer);
    state.liveTimer = null;
  }
  if (markDone) setLiveStatus("已回复");
}

function activitySummary() {
  const doneCount = state.activityItems.filter((item) => item.status === "done").length;
  const sourceCount = visibleSources().length;
  const companyCount = state.candidates.length;
  if (doneCount || sourceCount || companyCount) {
    const parts = [`已完成 ${doneCount || state.activityItems.length} 步分析`];
    if (sourceCount) parts.push(`参考 ${sourceCount} 条资料`);
    if (companyCount) parts.push(`生成 ${companyCount} 家推荐`);
    return parts.join(" · ");
  }
  return "请求已提交";
}

function renderActivity() {
  const message = state.currentAgentMessage;
  const host = message?.querySelector(".activity-items");
  const summary = message?.querySelector(".activity-toggle span");
  if (!host) return;
  if (summary) summary.textContent = activitySummary();
  host.innerHTML = state.activityItems.length
    ? state.activityItems
        .map((item) => `
          <div class="activity-item ${escapeHtml(item.status)}">
            <i class="activity-dot"></i>
            <div>
              <strong>${escapeHtml(item.label)}</strong>
              <p>${escapeHtml(item.detail)}</p>
            </div>
          </div>
        `)
        .join("")
    : `<div class="activity-empty">等待服务返回进展。</div>`;
}

function normalizeActivity(label = "", detail = "") {
  const raw = `${label} ${detail}`;
  const matched = activityMap.find(([pattern]) => pattern.test(raw));
  if (matched) return { label: matched[1][0], detail: detail || matched[1][1] };
  return {
    label: label && label.length <= 18 ? label : "正在分析",
    detail: detail || "正在处理当前请求。",
  };
}

function markActivity(label, detail = "", status = "done") {
  const next = normalizeActivity(label, detail);
  const existing = state.activityItems.find((item) => item.label === next.label);
  if (existing) {
    existing.detail = next.detail || existing.detail;
    existing.status = status;
  } else {
    state.activityItems.push({ ...next, status });
  }
  renderActivity();
  updateWorkstream(next.label);
}

function finishActivities() {
  stopLiveProgress(true);
  if (!state.activityItems.length) {
    markActivity("请求已提交", "已收到任务。", "done");
    markActivity("正在分析", "正在整理判断。", "done");
  }
  markActivity("已返回结果", "已形成可继续追问的结果。", "done");
  state.activityItems = state.activityItems.map((item) => ({ ...item, status: "done" }));
  renderActivity();
  state.currentAgentMessage?.querySelector(".activity-timeline")?.classList.add("collapsed");
  state.currentAgentMessage?.querySelector(".live-status")?.classList.add("done");
  state.currentAgentMessage?.querySelector("#activeWorkstream")?.classList.add("done");
  const meta = state.currentAgentMessage?.querySelector(".message-meta span");
  if (meta) meta.textContent = "已完成";
}

function renderAgentText(text) {
  const host = state.currentAgentMessage?.querySelector(".agent-text");
  if (!host) return;
  state.currentAgentMessage.dataset.messageRaw = text || "";
  host.innerHTML = formatBlocks(text);
  bindMessageActions(state.currentAgentMessage);
  scrollThread();
}

function handleStreamEvent(event) {
  if (event.event === "agent_state") {
    stopLiveProgress(false);
    if (event.mode === "conversation") {
      setConversationMode(event.detail || event.label || "正在回复");
    } else {
      setLiveStatus(event.label || event.detail || "正在分析");
    }
  }
  if (event.event === "stage" || event.event === "status") {
    stopLiveProgress(false);
    setLiveStatus(event.label || event.detail || "正在分析");
  }
  if (event.event === "text_delta") {
    state.receivedTextDelta = true;
    state.jsonBuffer += event.content || "";
    if (state.debugMode) updateDebugPanel(event.content);
  }
  if (event.event === "artifact") {
    state.jsonBuffer = "";
    state.streamingText = "";
    if (event.type === "stats") {
      renderStats(event.stats || {});
    } else {
      const normalized = normalizeResponseToArtifact(event);
      renderReport(normalized);
    }
    if (state.debugMode && event.report) updateDebugPanel(null, event.report);
  }
  if (event.event === "done") {
    setAgentState("ready");
    finishActivities();
    if (!state.report && state.receivedTextDelta) {
      state.jsonBuffer = "";
      renderAgentText("结果解析失败，请重试");
    }
    state.receivedTextDelta = false;
  }
}

function normalizeResponseToArtifact(payload) {
  const report = payload.report || {};
  const cleaned = { ...payload };
  if (cleaned.report) {
    cleaned.report = { ...cleaned.report };
    delete cleaned.report.sources_used;
    delete cleaned.report.draft;
  }
  cleaned.exportData = {
    verdict: report.verdict || "",
    summary: report.summary || "",
    confidence: report.confidence || "",
    metrics: report.metrics || {},
    sections: report.sections || [],
    policy_matches: report.policy_matches || [],
    action_plan: report.action_plan || [],
    ranked_companies: report.ranked_companies || [],
  };
  return cleaned;
}

function updateDebugPanel(rawChunk, parsedReport) {
  const panel = document.getElementById("debugPanel");
  if (!panel) return;
  if (rawChunk) {
    const rawEl = panel.querySelector(".debug-raw");
    if (rawEl) rawEl.textContent += rawChunk;
  }
  if (parsedReport) {
    const parsedEl = panel.querySelector(".debug-parsed");
    if (parsedEl) parsedEl.textContent = JSON.stringify(parsedReport, null, 2);
  }
}

function normalizeCandidates(rows = [], report = {}) {
  const riskLevel = report.metrics?.risk_level || "待确认";
  return rows.map((row, index) => ({
    rank: row.rank || index + 1,
    name: row.name || "",
    industry: row.industry || "",
    subIndustry: row.sub_industry || "",
    score: row.score ?? row._score ?? "-",
    scoreParts: row.score_parts || row._score_parts || {},
    reason: row.reason || row._rank_reason || row.brief || "",
    brief: row.brief || row.description || "",
    nextStep: row.next_step || "",
    revenue: row.revenue_range || "",
    financing: row.financing_stage || "",
    patents: row.patents,
    employees: row.employees || row.employee_count || "",
    foundedYear: row.founded_year || row.established_year || "",
    region: row.region || row.city || row.location || "",
    qualification: row.qualification || row.certification || "",
    tags: parseTags(row.tags),
    riskLevel: row.risk_level || riskLevel,
  }));
}

function parseTags(value) {
  if (Array.isArray(value)) return value.filter(Boolean);
  if (!value) return [];
  const text = String(value).trim();
  try {
    const parsed = JSON.parse(text);
    if (Array.isArray(parsed)) return parsed.filter(Boolean);
  } catch {}
  return text.split(/[、,，/]/).map((item) => item.trim()).filter(Boolean);
}

function getCandidates(payload) {
  const report = payload?.report || {};
  const ranked = normalizeCandidates(report.ranked_companies || [], report);
  if (ranked.length) return ranked;
  const key = ["candidate", "_", "enter", "prises"].join("");
  return normalizeCandidates(payload?.context?.[key] || [], report);
}

function sourceKind(type = "") {
  const value = String(type || "");
  if (/policy/i.test(value)) return "政策机会";
  if (/industry|market/i.test(value)) return "产业资料";
  if (/risk/i.test(value)) return "风险资料";
  if (/enterprise|company|local/i.test(value)) return "企业画像";
  if (/crm|contact|history/i.test(value)) return "历史触达";
  return "判断依据";
}

function isDisplayableSource(item = {}) {
  const raw = `${item.id || ""} ${item.title || ""} ${item.source || ""} ${item.type || ""} ${item.snippet || ""}`;
  return !/rag|chromadb|workflow|mcp|system_status|unavailable|向量知识库|未连接/i.test(raw);
}

function visibleSources() {
  return state.sources.filter(isDisplayableSource);
}

function cleanSourceName(value = "", type = "") {
  const text = String(value || "").trim();
  if (!text || /\.(json|db|sqlite|csv)$/i.test(text) || /enterprises|policies|industry_graph|chroma|park_policies/i.test(text)) {
    return sourceKind(type);
  }
  return cleanBackendText(text, type);
}

function sourceTitle(item = {}) {
  const title = String(item.title || "");
  if (/candidate|rank|score|排序|评分/i.test(title)) return "推荐理由摘要";
  if (/\.(json|db|sqlite|csv)$/i.test(title)) return sourceKind(item.type);
  return cleanBackendText(title, item.type) || sourceKind(item.type);
}

function sourceSupportText(item = {}) {
  const text = cleanBackendText(item.relation || item.match_reason || "", item.type);
  if (!text || /^支撑/.test(text)) return evidenceImpact(item);
  return text;
}

function evidenceImpact(item = {}) {
  const type = String(item.type || "");
  const title = `${item.title || ""} ${item.id || ""}`;
  if (/policy/i.test(type) || /政策|补贴|奖励/.test(title)) return "政策抓手";
  if (/risk/i.test(type) || /风险/.test(title)) return "推进节奏";
  if (/crm/i.test(type) || /触达|跟进/.test(title)) return "沟通策略";
  if (/industry|graph|market/i.test(type) || /产业|链/.test(title)) return "产业匹配";
  if (/enterprise|structured|local/i.test(type) || /画像|企业/.test(title)) return "企业优先级";
  return "综合判断";
}

function formatCrmSnippet(value = "") {
  const raw = String(value || "").trim();
  const match = raw.match(/^(.*?)[：:]\s*(\[[\s\S]*\])\s*$/);
  if (!match) return raw;
  try {
    const prefix = match[1].trim();
    const records = JSON.parse(match[2]);
    if (!Array.isArray(records)) return raw;
    const lines = records
      .map((record) => `${record.date || ""} ${record.note || ""}`.trim())
      .filter(Boolean);
    return `${prefix}。关键记录：${lines.join("；")}`;
  } catch {
    return raw.replace(/[{}\[\]"]/g, "").replace(/date\s*:/gi, "日期：").replace(/note\s*:/gi, "记录：");
  }
}

function cleanBackendText(value = "", type = "") {
  let text = String(value || "").trim();
  if (!text) return "";
  if (/crm/i.test(type) || /"date"|"note"|date\s*:|note\s*:/i.test(text)) {
    text = formatCrmSnippet(text);
  }
  return text
    .replace(/本地企业库\s*enterprises/gi, "企业画像资料")
    .replace(/园区政策库\s*park_policies/gi, "园区政策资料")
    .replace(/产业图谱\s*industry_graph\.json/gi, "产业链资料")
    .replace(/enterprises\.risk_score\s*\+\s*本地规则/gi, "风险核验资料")
    .replace(/\benterprises\b/gi, "企业画像资料")
    .replace(/\bpark_policies\b/gi, "园区政策资料")
    .replace(/\bindustry_graph\.json\b/gi, "产业链资料")
    .replace(/\bRAG\s*\/\s*ChromaDB\b/gi, "补充知识库")
    .replace(/\bChromaDB\b/gi, "补充知识库")
    .replace(/\bRAG\b/gi, "补充知识库")
    .replace(/\s+/g, " ")
    .trim();
}

function sourceButton(item, index) {
  const impact = evidenceImpact(item);
  const snippet = compactText(cleanBackendText(item.snippet || item.match_reason || "", item.type), 96);
  return `
    <button type="button" data-source-index="${index}">
      <strong>${escapeHtml(sourceTitle(item))}<span>${escapeHtml(impact)}</span></strong>
      <p>${escapeHtml(snippet || "用于核验本轮招商判断。")}</p>
    </button>
  `;
}

function basisDialogTitle(item = {}) {
  const type = String(item.type || "");
  const title = `${item.title || ""} ${item.id || ""}`;
  if (/policy/i.test(type) || /政策|补贴|奖励/.test(title)) return "政策匹配依据";
  if (/risk/i.test(type) || /风险/.test(title)) return "风险核验依据";
  if (/crm|contact|history/i.test(type) || /触达|跟进|签约|联系/.test(title)) return "历史触达依据";
  if (/industry|graph|market/i.test(type) || /产业|链|赛道/.test(title)) return "产业位置依据";
  if (/enterprise|company|local|structured/i.test(type) || /画像|企业/.test(title)) return "企业画像依据";
  return "推荐依据";
}

function sourceIndexByKind(match, fallback = 0) {
  const sources = visibleSources();
  const index = sources.findIndex((item) => match.test(`${item.type || ""} ${item.title || ""} ${item.id || ""}`));
  return index >= 0 ? index : fallback;
}

function sourceIndexForCompany() {
  return sourceIndexByKind(/enterprise|company|local|structured|画像|企业/i);
}

function basisKeyFact(item = {}, active = selectedCompany()) {
  const snippet = cleanBackendText(item.snippet || item.match_reason || "", item.type);
  if (snippet) return compactText(snippet, 170);
  if (active) {
    const facts = [
      [active.industry, active.subIndustry].filter(Boolean).join(" / "),
      active.revenue,
      active.financing,
      active.patents ? `专利 ${active.patents} 项` : "",
      active.employees ? `员工 ${active.employees} 人` : "",
    ].filter(Boolean);
    return `${active.name}：${facts.join("，") || "企业画像信息待补充"}。`;
  }
  return "该资料用于补充本轮推荐的事实背景。";
}

function basisSupportedJudgment(item = {}, active = selectedCompany()) {
  const support = sourceSupportText(item);
  if (support && !/^综合判断$/.test(support)) return compactText(support, 130);
  const impact = evidenceImpact(item);
  if (active && /企业优先级|产业匹配/.test(impact)) return `支持判断 ${active.name} 是否符合本轮招商目标与优先级。`;
  if (/政策抓手/.test(impact)) return "支持判断是否存在可用于谈判、补贴、入驻或人才配套的政策机会。";
  if (/推进节奏/.test(impact)) return "支持判断推进前需要先核验的风险点和节奏安排。";
  if (/沟通策略/.test(impact)) return "支持判断是否适合继续触达，以及沟通切入点。";
  return "支持本轮推荐排序和后续推进动作。";
}

function basisVerification(item = {}, active = selectedCompany()) {
  const type = String(item.type || "");
  if (/policy/i.test(type)) return "核验政策适用条件、申报周期、兑现材料和企业是否满足门槛。";
  if (/risk/i.test(type)) return "核验经营状态、负面记录、团队稳定性和落地周期。";
  if (/crm|contact|history/i.test(type)) return "核验最近联系人、意向阶段、触达记录和下一次沟通安排。";
  if (/enterprise|company|local|structured/i.test(type)) return "核验营收、融资、专利、团队和租金承载力是否为最新口径。";
  if (active) return `补充核验 ${active.name} 的最新经营、融资和落地意愿。`;
  return "用于会前补充核验，不作为单一决策依据。";
}

function basisActionImpact(item = {}, active = selectedCompany()) {
  const impact = evidenceImpact(item);
  if (/政策抓手/.test(impact)) return "可转化为招商邀约中的政策抓手和谈判筹码。";
  if (/推进节奏/.test(impact)) return "决定是否先做风险复核，再安排约访或材料生成。";
  if (/沟通策略/.test(impact)) return "影响首次触达话术、拜访对象和沟通节奏。";
  if (/产业匹配/.test(impact)) return "影响是否纳入重点赛道清单及同类企业扩展方向。";
  if (active) return `用于校准 ${active.name} 的推进优先级和下一步动作。`;
  return "用于校准本轮推荐优先级和后续推进动作。";
}

function companyFactLine(item = {}) {
  const facts = [
    [item.industry, item.subIndustry].filter(Boolean).join(" / "),
    item.revenue,
    item.financing,
    item.patents ? `专利 ${item.patents} 项` : "",
    item.employees ? `员工 ${item.employees} 人` : "",
    item.riskLevel,
  ].filter(Boolean);
  return facts.join(" · ") || "企业画像待补充";
}

function renderBasisPanel(active, sources) {
  if (active) {
    const keySourceIndex = sourceIndexForCompany();
    const policyIndex = sourceIndexByKind(/policy|政策|补贴|奖励/i, -1);
    const riskIndex = sourceIndexByKind(/risk|风险/i, -1);
    return `
      <div class="basis-panel company-basis">
        <article class="basis-hero">
          <span>为什么关注</span>
          <strong>${escapeHtml(active.name)}</strong>
          <p>${escapeHtml(active.reason || "与当前招商目标存在明确匹配点，适合进入下一轮核验与触达。")}</p>
        </article>
        <div class="basis-facts">
          <span>${escapeHtml(companyFactLine(active))}</span>
          <span>匹配分 ${escapeHtml(active.score || "-")}</span>
        </div>
        <article class="basis-card">
          <strong>仍需核验</strong>
          <p>${escapeHtml(basisVerification(sources[keySourceIndex] || {}, active))}</p>
        </article>
        <article class="basis-card action-card">
          <strong>建议动作</strong>
          <p>${escapeHtml(actionSuggestion(active))}</p>
        </article>
        <div class="basis-actions">
          ${sources[keySourceIndex] ? `<button type="button" data-insight-source="${keySourceIndex}">企业画像依据</button>` : ""}
          ${sources[policyIndex] ? `<button type="button" data-insight-source="${policyIndex}">政策匹配依据</button>` : ""}
          ${sources[riskIndex] ? `<button type="button" data-insight-source="${riskIndex}">风险核验依据</button>` : ""}
        </div>
      </div>
    `;
  }

  if (state.candidates.length) {
    const topCompanies = state.candidates.slice(0, 3).map((item) => item.name).filter(Boolean).join("、");
    const sourceCount = sources.length ? `${sourceCategoryCount()} 类资料` : "资料待补充";
    return `
      <div class="basis-panel round-basis">
        <article class="basis-hero">
          <span>本轮判断</span>
          <strong>${escapeHtml(`${state.candidates.length} 家候选企业`)}</strong>
          <p>${escapeHtml(topCompanies ? `优先关注：${topCompanies}。` : "已形成一批可继续核验的企业线索。")}</p>
        </article>
        <div class="basis-grid">
          <article class="basis-card">
            <strong>推荐逻辑</strong>
            <p>综合企业画像、产业位置、承载能力、政策机会和风险因素形成排序。</p>
          </article>
          <article class="basis-card">
            <strong>资料覆盖</strong>
            <p>${escapeHtml(sourceCount)}，用于解释推荐理由和会前核验重点。</p>
          </article>
        </div>
        <div class="basis-actions">
          <button type="button" data-prompt="请展开说明这次推荐的筛选逻辑。">展开筛选逻辑</button>
          ${sources[0] ? `<button type="button" data-insight-source="0">查看关键依据</button>` : ""}
        </div>
      </div>
    `;
  }

  return `<p class="muted">形成建议后，这里会说明推荐理由、关键事实、待核验事项和下一步动作。</p>`;
}

function renderShortlistInsight() {
  if (!state.shortlist.length) {
    return `<p class="muted">推荐结果中加入清单后，这里会沉淀准备继续推进的企业。</p>`;
  }
  return `
    <div class="shortlist-panel">
      <header>
        <strong>跟进清单</strong>
        <button type="button" data-insight-compare ${state.shortlist.length < 2 ? "disabled" : ""}>对比</button>
      </header>
      ${state.shortlist.map((item, index) => `
        <article class="shortlist-mini-row">
          <button type="button" data-insight-company="${index}">
            <strong>${escapeHtml(item.name)}</strong>
            <span>${escapeHtml([item.industry, item.subIndustry].filter(Boolean).join(" / ") || "赛道待确认")} · ${escapeHtml(actionSuggestion(item))}</span>
          </button>
          <button type="button" data-insight-remove="${index}" aria-label="移出 ${escapeHtml(item.name)}">移出</button>
        </article>
      `).join("")}
    </div>
  `;
}

function renderShortlistShelf() {
  const el = ui.shelfList;
  const count = state.shortlist.length;
  if (ui.shelfCount) ui.shelfCount.textContent = count || "";
  state.shelfSelection = new Set([...state.shelfSelection].filter((i) => i < count));
  if (!el) return;
  if (!count) {
    el.innerHTML = `<p class="shelf-empty">加入企业后，这里会列出准备继续推进的线索。</p>`;
    if (ui.shelfCompare) { ui.shelfCompare.disabled = true; ui.shelfCompare.textContent = "对比企业"; }
    return;
  }
  const selectedCount = state.shelfSelection.size;
  el.innerHTML = state.shortlist
    .map((item, index) => {
      const checked = state.shelfSelection.has(index) ? "checked" : "";
      return `
      <div class="shelf-item ${checked ? "selected" : ""}" data-shelf-index="${index}">
        <label class="shelf-check">
          <input type="checkbox" data-shelf-select="${index}" ${checked}>
        </label>
        <strong>${escapeHtml(item.name)}</strong>
        <div class="shelf-item-meta">${escapeHtml([item.industry, item.subIndustry].filter(Boolean).join(" / ") || "赛道待确认")} · 匹配分 ${escapeHtml(item.score || "-")}</div>
        <div class="shelf-item-actions">
          <button type="button" data-shelf-focus="${index}">查看</button>
          <button type="button" data-shelf-outline="${index}">拜访提纲</button>
          <button type="button" class="shelf-remove" data-shelf-remove="${index}">移出</button>
        </div>
      </div>`;
    }).join("");
  if (ui.shelfCompare) {
    const enough = selectedCount >= 2;
    ui.shelfCompare.disabled = !enough;
    ui.shelfCompare.textContent = enough ? `对比已选 ${selectedCount} 家` : selectedCount === 1 ? "请再选 1 家" : "勾选企业后对比";
  }
  bindShortlistShelfItems();
}

function bindShortlistShelfItems() {
  const root = ui.shelfList;
  if (!root) return;
  root.querySelectorAll("[data-shelf-select]").forEach((cb) => {
    cb.addEventListener("change", () => {
      const index = Number(cb.dataset.shelfSelect);
      if (cb.checked) state.shelfSelection.add(index);
      else state.shelfSelection.delete(index);
      renderShortlistShelf();
    });
  });
  root.querySelectorAll("[data-shelf-focus]").forEach((btn) => {
    btn.addEventListener("click", () => focusShortlistItem(Number(btn.dataset.shelfFocus)));
  });
  root.querySelectorAll("[data-shelf-outline]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const item = state.shortlist[Number(btn.dataset.shelfOutline)];
      if (!item) return;
      state.selectedCompanyIndex = state.candidates.findIndex((c) => c.name === item.name);
      updateInsight();
      generateMaterial("outline", "", { scope: "company" });
    });
  });
  root.querySelectorAll("[data-shelf-remove]").forEach((btn) => {
    btn.addEventListener("click", () => {
      routeAction(ACTION_TYPES.local, "remove_from_shortlist", { index: Number(btn.dataset.shelfRemove) });
    });
  });
}

function renderActiveCompanyInsight(active) {
  return `
    <div class="active-company-card">
      <strong>${escapeHtml(active.name)}</strong>
      <p>${escapeHtml(companyFactLine(active))}</p>
      <div>
        <span>匹配分 ${escapeHtml(active.score || "-")}</span>
        <span>${escapeHtml(active.riskLevel || "风险待确认")}</span>
      </div>
      <button type="button" data-insight-material>生成拜访提纲</button>
    </div>
  `;
}

function bindInsightActions(sources = visibleSources()) {
  ui.sourceList.querySelectorAll("[data-insight-source]").forEach((button) => {
    button.addEventListener("click", () => openSource(Number(button.dataset.insightSource), sources));
  });
  ui.sourceList.querySelectorAll("[data-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      ui.input.value = button.dataset.prompt || "";
      ui.input.focus();
    });
  });
  ui.activeCompany.querySelectorAll("[data-insight-company]").forEach((button) => {
    button.addEventListener("click", () => {
      routeAction(ACTION_TYPES.local, "focus_company", { index: Number(button.dataset.insightCompany) });
    });
  });
  ui.activeCompany.querySelectorAll("[data-insight-remove]").forEach((button) => {
    button.addEventListener("click", () => {
      routeAction(ACTION_TYPES.local, "remove_from_shortlist", { index: Number(button.dataset.insightRemove) });
    });
  });
  ui.activeCompany.querySelector("[data-insight-compare]")?.addEventListener("click", () => routeAction(ACTION_TYPES.agent, "compare"));
  ui.activeCompany.querySelector("[data-insight-material]")?.addEventListener("click", () => routeAction(ACTION_TYPES.agent, "outline"));
}

function extractRisks() {
  const report = state.report || {};
  const risks = [];
  if (Array.isArray(report.risks)) {
    report.risks.forEach((item) => risks.push(typeof item === "string" ? item : item.detail || item.title || ""));
  }
  if (report.metrics?.risk_level) risks.unshift(`风险等级：${report.metrics.risk_level}`);
  return risks.filter(Boolean);
}

function mainRisksText() {
  const risks = extractRisks().map((item) => item.replace(/^风险等级：/, ""));
  if (risks.length) return compactText(risks.slice(0, 3).join("、"), 42);
  return "租金承载力、经营稳定性、落地周期";
}

function highPriorityCount() {
  return state.candidates.filter((item) => Number(item.score) >= 90).length;
}

function sourceCategoryCount() {
  const sources = visibleSources();
  return new Set(sources.map((item) => sourceKind(item.type))).size || sources.length;
}

function criteriaFromGoal() {
  const text = `${state.currentGoal} ${state.report?.summary || ""}`;
  const criteria = [...FALLBACK_CRITERIA];
  if (/政策|补贴|扶持|抓手/.test(text)) criteria.push("政策机会");
  if (/风险|稳定|核验/.test(text)) criteria.push("风险复核");
  if (/租金|承载/.test(text)) criteria.push("租金承载");
  return [...new Set(criteria)].slice(0, 6);
}

function renderRiskInsight() {
  const risks = extractRisks();
  if (!risks.length) return `<p class="muted">完成分析后，会列出需要复核的事项。</p>`;
  return `<ul>${risks.slice(0, 5).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderNextActions() {
  const defaults = [
    { label: "查看跟进清单", hint: "查看已加入的重点企业。", type: "shortlist" },
    { label: "生成拜访提纲", hint: "把当前判断转成拜访问题与沟通重点。", type: "material", material_type: "outline" },
    { label: "生成邀约话术", hint: "用于微信或电话首次触达。", type: "material", material_type: "wechat" },
    { label: "整理汇报摘要", hint: "压缩为领导可快速阅读的版本。", type: "material", material_type: "briefing" },
  ];
  const actions = state.actions.length ? state.actions : state.candidates.length ? defaults : [];
  if (!actions.length) {
    ui.nextActions.innerHTML = `<p class="muted">形成推荐后，可以继续生成材料或调整条件。</p>`;
    return;
  }
  ui.nextActions.innerHTML = actions
    .slice(0, 5)
    .map((action, index) => `
      <button type="button" data-action-index="${index}">
        <strong>${escapeHtml(action.label || "下一步推进")}</strong>
        <p>${escapeHtml(action.hint || "")}</p>
      </button>
    `)
    .join("");
  ui.nextActions.querySelectorAll("[data-action-index]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = actions[Number(button.dataset.actionIndex)];
      if (action?.type === "shortlist") routeAction(ACTION_TYPES.local, "view_shortlist");
      if (action?.type === "material" || action?.material_type) routeAction(ACTION_TYPES.agent, action.material_type || "outline");
    });
  });
}

function updateCommandContext() {
  ui.input.placeholder = state.candidates.length
    ? "继续追问：为什么推荐第 1 家？帮我生成拜访提纲？排除高风险企业？"
    : "直接输入招商目标，例如：推荐 8 家适合重点推进的芯片企业，并说明理由。";
  if (!ui.commandChips) return;
  const chips = state.shortlist.length
    ? [
        { label: "生成拜访提纲", action: "outline" },
        { label: "生成邀约话术", action: "wechat" },
        { label: "对比企业", action: "compare" },
        { label: "导出推荐摘要", action: "briefing" },
      ]
    : [
        { label: "展开筛选逻辑", prompt: "请展开说明这次推荐的筛选逻辑。" },
        { label: "解释第 1 家", prompt: "为什么推荐第 1 家？展开说明推荐理由。" },
        { label: "收紧筛选条件", prompt: "排除高风险企业，并收紧筛选条件重新推荐。" },
        { label: "生成拜访提纲", action: "outline" },
        { label: "导出推荐摘要", action: "briefing" },
      ];
  ui.commandChips.innerHTML = chips
    .map((chip) => chip.action
      ? `<button type="button" data-command-action="${escapeHtml(chip.action)}">${escapeHtml(chip.label)}</button>`
      : `<button type="button" data-prompt="${escapeHtml(chip.prompt)}">${escapeHtml(chip.label)}</button>`)
    .join("");
  bindPromptButtons(ui.commandChips);
  bindCommandActions(ui.commandChips);
}

function updateInsight() {
  ui.currentProject.textContent = state.currentGoal
    ? `当前任务：${compactText(state.currentGoal, 18)}`
    : "当前任务：重点企业筛选";
  ui.goalUnderstanding.textContent = state.currentGoal || "等待你交办招商目标。";

  const sources = visibleSources();
  const active = selectedCompany();
  ui.sourceList.innerHTML = renderBasisPanel(active, sources);

  ui.criteriaList.innerHTML = criteriaFromGoal().map((label) => `<span>${escapeHtml(label)}</span>`).join("");

  ui.activeCompany.innerHTML = active
    ? renderActiveCompanyInsight(active)
    : renderShortlistInsight();
  bindInsightActions(sources);

  ui.riskList.innerHTML = renderRiskInsight();
  renderNextActions();
  renderShortlistShelf();
  updateCommandContext();
  queuePersistThread();
}

function renderPlainAnswer(text) {
  setAgentState("ready");
  ui.agentStatus.textContent = "已回复";
  finishActivities();
  const answer = publicAnswerText(text || "我可以继续帮你推进招商任务。");
  state.lastSummary = compactText(answer, 700);
  addHistory("assistant", answer);
  renderAgentText(answer);
  updateInsight();
}

function renderMetaFallback(task = "") {
  setAgentState("ready");
  ui.agentStatus.textContent = "已回复";
  finishActivities();
  const answer = /你是谁|介绍/.test(task)
    ? "我是 ParkFlow，面向招商工作的智能顾问。你可以直接把招商目标交给我，例如筛选重点企业、解释推荐理由、对比清单企业、生成拜访提纲或邀约话术。"
    : "你可以直接输入招商目标，例如“推荐 8 家适合重点推进的芯片企业，并说明理由”，也可以在结果后继续追问“为什么推荐第 1 家”或“生成拜访提纲”。";
  renderAgentText(answer);
  addHistory("assistant", answer);
  updateInsight();
}

function isShortlistQuestion(task = "") {
  return /清单|已加入|加入清单|跟进池|名单/.test(task);
}

function isShortlistComparisonQuestion(task = "") {
  return /(对比|比较|优劣|哪家更|哪个更).*(清单|两家|这些|这几家|企业)|清单.*(对比|比较|优劣|哪家更|哪个更)/.test(task);
}

function isSelectionLogicQuestion(task = "") {
  return /筛选逻辑|推荐逻辑|展开逻辑|怎么筛|如何筛|为什么是这批|排序逻辑/.test(task);
}

function selectionLogicArtifact() {
  const companies = state.candidates.slice(0, 5);
  const sources = visibleSources();
  const requested = requestedCountFromTask(state.currentGoal);
  const countLine = requested && requested !== state.candidates.length
    ? `本轮目标为 ${requested} 家，当前后端返回 ${state.candidates.length} 家可推进企业。`
    : `本轮形成 ${state.candidates.length} 家可推进企业。`;
  return `
    <section class="inline-artifact logic-artifact">
      <div class="artifact-header">
        <div>
          <span class="artifact-kicker">筛选逻辑</span>
          <h2>本轮推荐如何形成</h2>
          <p>${escapeHtml(countLine)}排序综合考虑产业匹配、企业质量、承载能力、政策机会和风险因素。</p>
        </div>
      </div>
      <div class="artifact-body logic-body">
        <div class="logic-grid">
          ${criteriaFromGoal().map((item) => `
            <article>
              <strong>${escapeHtml(item)}</strong>
              <p>${escapeHtml(logicDescription(item))}</p>
            </article>
          `).join("")}
        </div>
        <div class="logic-list">
          ${companies.map((item, index) => `
            <article>
              <span>${String(index + 1).padStart(2, "0")}</span>
              <div>
                <strong>${escapeHtml(item.name)}</strong>
                <p>${escapeHtml(item.reason || "与本轮招商目标存在匹配点。")}</p>
              </div>
              <em>${escapeHtml(item.score || "-")}</em>
            </article>
          `).join("")}
        </div>
        <p class="logic-footnote">参考资料：${escapeHtml(sources.map(sourceTitle).slice(0, 4).join("、") || "企业画像、政策机会、风险核验")}。</p>
      </div>
    </section>
  `;
}

function logicDescription(label = "") {
  if (label.includes("产业")) return "判断企业方向是否匹配园区重点赛道，以及是否能补强产业链位置。";
  if (label.includes("承载") || label.includes("租金")) return "结合营收规模、融资阶段和载体需求，评估入驻和租金承载能力。";
  if (label.includes("成长")) return "参考融资阶段、专利、资质和团队背景，判断持续发展潜力。";
  if (label.includes("风险")) return "结合风险等级、经营状态和待核验事项，决定推进节奏。";
  if (label.includes("政策")) return "识别可用于谈判、补贴、入驻或人才配套的政策机会。";
  return "作为本轮招商判断的辅助条件。";
}

function renderSelectionLogicMessage() {
  setAgentState("ready");
  ui.agentStatus.textContent = "已解释逻辑";
  const agentMessage = createAgentMessage();
  markActivity("解析目标", "沿用当前招商目标和推荐结果。", "done");
  markActivity("形成优先级", "解释企业排序和筛选标准。", "done");
  markActivity("已返回结果", "已生成筛选逻辑说明。", "done");
  finishActivities();
  const answer = "这是基于当前推荐结果展开的筛选逻辑。它不是新的检索任务，而是解释刚才那批企业为什么进入推荐、为什么按这个优先级排列。";
  renderAgentText(answer);
  addHistory("assistant", answer);
  agentMessage.querySelector(".artifact-slot").innerHTML = selectionLogicArtifact();
  bindArtifactActions(agentMessage);
  updateInsight();
}

function addToShortlist(item) {
  if (!item?.name) return false;
  const existing = state.shortlist.find((company) => company.name === item.name);
  if (existing) return false;
  state.shortlist.push({
    ...item,
    addedAt: new Date().toLocaleString("zh-CN", { hour12: false }),
  });
  return true;
}

function removeFromShortlist(index) {
  if (!Number.isFinite(index) || index < 0) return null;
  return state.shortlist.splice(index, 1)[0] || null;
}

function refreshCurrentArtifact(root = state.currentAgentMessage) {
  const slot = root?.querySelector(".artifact-slot");
  if (!slot) return;
  if (state.candidates.length) {
    slot.innerHTML = recommendationArtifact();
    bindArtifactActions(root);
  } else if (state.shortlist.length) {
    slot.innerHTML = shortlistArtifact();
    bindArtifactActions(root);
  }
}

function focusShortlistItem(index) {
  const item = state.shortlist[Number(index)];
  if (!item) return;
  focusCompany(item);
  showToast(`已切换关注：${item.name}`);
}

function handleLocalStateAction(action, payload = {}) {
  if (action === "add_to_shortlist") {
    const item = payload.item;
    const added = addToShortlist(item);
    if (Number.isFinite(payload.index)) state.selectedCompanyIndex = payload.index;
    addHistory("system", `跟进清单：${state.shortlist.map((company) => company.name).join("、") || "空"}`);
    refreshCurrentArtifact(payload.root);
    updateInsight();
    showToast(added ? "已加入跟进清单，可继续生成拜访提纲" : "这家企业已在跟进清单中");
    return;
  }
  if (action === "remove_from_shortlist") {
    const removed = removeFromShortlist(Number(payload.index));
    if (removed && selectedCompany()?.name === removed.name) state.selectedCompanyIndex = -1;
    addHistory("system", removed?.name ? `已将 ${removed.name} 移出跟进清单。` : "已更新跟进清单。");
    refreshCurrentArtifact(payload.root);
    updateInsight();
    showToast(removed?.name ? `已移出：${removed.name}` : "跟进清单已更新");
    return;
  }
  if (action === "focus_company") {
    focusShortlistItem(Number(payload.index));
    return;
  }
  if (action === "view_shortlist") {
    state.selectedCompanyIndex = -1;
    updateInsight();
    showToast(state.shortlist.length ? `跟进清单已有 ${state.shortlist.length} 家企业` : "当前清单为空");
  }
}

function handleAgentGenerationAction(action) {
  if (action === "outline") {
    generateMaterial("outline");
    return;
  }
  if (action === "wechat") {
    generateMaterial("wechat");
    return;
  }
  if (action === "briefing") {
    generateMaterial("briefing", "把当前推荐整理成领导汇报摘要。", { scope: "thread" });
    return;
  }
  if (action === "compare") {
    if (state.shortlist.length !== 2) {
      showToast("请选择 2 家企业后再生成对比", "warn");
      return;
    }
    generateMaterial("comparison", "对比跟进清单中的两家企业，形成适合领导汇报的企业对比材料。", { scope: "thread" });
  }
}

function routeAction(actionType, action, payload = {}) {
  if (actionType === ACTION_TYPES.local) return handleLocalStateAction(action, payload);
  if (actionType === ACTION_TYPES.agent) return handleAgentGenerationAction(action, payload);
  if (actionType === ACTION_TYPES.light) return showToast(payload.message || "已更新");
  return null;
}

function shortlistArtifact() {
  const rows = state.shortlist.length
    ? state.shortlist
        .map((item, index) => `
          <article class="shortlist-row" data-shortlist-index="${index}">
            <span>${String(index + 1).padStart(2, "0")}</span>
            <div>
              <strong>${escapeHtml(item.name)}</strong>
              <p>${escapeHtml([item.industry, item.subIndustry].filter(Boolean).join(" / ") || "赛道待确认")} · 匹配分 ${escapeHtml(item.score || "-")}</p>
            </div>
            <em>${escapeHtml(actionSuggestion(item))}</em>
            <footer>
              <button type="button" data-shortlist-focus="${index}">查看</button>
              <button type="button" data-shortlist-material="${index}">拜访提纲</button>
              <button type="button" data-shortlist-remove="${index}">移出</button>
            </footer>
          </article>
        `)
        .join("")
    : `<p class="muted">当前还没有加入清单的企业。可以在推荐卡片中点击“加入清单”。</p>`;
  return `
    <section class="inline-artifact shortlist-artifact">
      <div class="artifact-header">
        <div>
          <span class="artifact-kicker">跟进清单</span>
          <h2>已加入 ${state.shortlist.length} 家企业</h2>
          <p>清单用于沉淀本轮准备继续推进的企业，后续生成拜访提纲、邀约话术和汇报摘要时会作为上下文。</p>
        </div>
      </div>
      <div class="artifact-body shortlist-body">
        ${state.shortlist.length >= 2 ? `<div class="shortlist-toolbar"><button type="button" data-compare-shortlist>对比清单企业</button></div>` : ""}
        ${rows}
      </div>
    </section>
  `;
}

function renderShortlistMessage() {
  setAgentState("ready");
  ui.agentStatus.textContent = "清单已更新";
  state.selectedCompanyIndex = -1;
  updateInsight();
  showToast(state.shortlist.length ? `跟进清单已有 ${state.shortlist.length} 家企业` : "当前清单为空");
}

function renderShortlistExplanation() {
  setAgentState("ready");
  ui.agentStatus.textContent = "已回复";
  const answer = state.shortlist.length
    ? `跟进清单用于沉淀本轮准备继续推进的企业，目前已有 ${state.shortlist.length} 家。后续生成拜访提纲、邀约话术、企业对比或汇报摘要时，会优先沿用这份清单。`
    : "跟进清单用于沉淀准备继续推进的企业。你可以在推荐卡片中点击“加入清单”，后续生成拜访提纲、邀约话术或汇报摘要时会沿用这些企业。";
  addMessage("agent", answer);
  addHistory("assistant", answer);
  updateInsight();
}

function numericScore(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function comparePart(item, names = [], fallback = "-") {
  const parts = item?.scoreParts || {};
  const key = names.find((name) => parts[name] !== undefined && parts[name] !== null);
  return key ? parts[key] : fallback;
}

function revenueWeight(value = "") {
  const text = String(value || "");
  if (/10亿以上/.test(text)) return 5;
  if (/5亿-10亿/.test(text)) return 4;
  if (/3亿-5亿/.test(text)) return 3;
  if (/1亿-3亿/.test(text)) return 2;
  if (text) return 1;
  return 0;
}

function riskWeight(value = "") {
  const text = String(value || "");
  if (/低/.test(text)) return 3;
  if (/中/.test(text)) return 2;
  if (/高/.test(text)) return 1;
  return 0;
}

function compareWinner(items = []) {
  return items
    .slice()
    .sort((a, b) => {
      const scoreDelta = numericScore(b.score) - numericScore(a.score);
      if (scoreDelta) return scoreDelta;
      const revenueDelta = revenueWeight(b.revenue) - revenueWeight(a.revenue);
      if (revenueDelta) return revenueDelta;
      const patentDelta = numericScore(b.patents) - numericScore(a.patents);
      if (patentDelta) return patentDelta;
      return riskWeight(b.riskLevel) - riskWeight(a.riskLevel);
    })[0] || null;
}

function compareDimensionRows(items = []) {
  const rows = [
    {
      label: "综合匹配",
      read: (item) => `${item.score || "-"} 分`,
      note: (item) => item.reason || "与本轮招商目标存在匹配点。",
    },
    {
      label: "承载能力",
      read: (item) => `${comparePart(item, ["租金承载", "承载能力"], item.revenue || "待确认")}`,
      note: (item) => item.revenue ? `营收区间 ${item.revenue}，可初步判断入驻承载力。` : "需要补充营收、面积和租金预算口径。",
    },
    {
      label: "成长潜力",
      read: (item) => `${comparePart(item, ["成长性", "成长潜力"], item.financing || "待确认")}`,
      note: (item) => [item.financing, item.patents ? `专利 ${item.patents} 项` : ""].filter(Boolean).join("，") || "需要补充融资、专利和团队信息。",
    },
    {
      label: "风险安全",
      read: (item) => `${comparePart(item, ["风险安全"], item.riskLevel || "待确认")}`,
      note: (item) => item.riskLevel ? `${item.riskLevel}，推进前仍需复核经营状态与负面记录。` : "需要补充经营状态和风险记录。",
    },
  ];
  return rows.map((row) => `
    <article class="compare-dimension">
      <header>
        <span>${escapeHtml(row.label)}</span>
        ${items.map((item) => `<strong>${escapeHtml(row.read(item))}</strong>`).join("")}
      </header>
      <div>
        ${items.map((item) => `<p><b>${escapeHtml(item.name)}</b>${escapeHtml(row.note(item))}</p>`).join("")}
      </div>
    </article>
  `).join("");
}

function compareDecisionText(best, items = []) {
  if (!best) return "清单中至少加入两家企业后，可形成对比建议。";
  const others = items.filter((item) => item.name !== best.name);
  const reason = [
    best.score ? `综合匹配分 ${best.score}` : "",
    best.revenue ? `营收 ${best.revenue}` : "",
    best.financing ? `${best.financing}` : "",
    best.patents ? `专利 ${best.patents} 项` : "",
    best.riskLevel ? `${best.riskLevel}` : "",
  ].filter(Boolean).join("，");
  const backup = others.length ? `；${others.map((item) => item.name).join("、")}可作为同赛道备选或补充核验对象` : "";
  return `${best.name}更适合作为本轮优先推进对象。${reason ? `主要依据是${reason}` : "主要依据是当前排序更靠前"}${backup}。`;
}

function compareOpenQuestions(items = []) {
  const questions = [];
  items.forEach((item) => {
    if (!item.revenue) questions.push(`${item.name}：补充营收和租金承载口径`);
    if (!item.financing) questions.push(`${item.name}：确认融资阶段与最新股权状态`);
    if (!item.patents) questions.push(`${item.name}：补充专利、资质和核心团队信息`);
    if (!item.riskLevel || /待确认|中|高/.test(item.riskLevel)) questions.push(`${item.name}：复核经营状态和风险记录`);
  });
  if (!questions.length) {
    questions.push("确认两家企业最新经营状态、实际载体面积需求和决策人信息。");
    questions.push("会前核验可适用政策的申报条件、兑现周期和材料清单。");
  }
  return [...new Set(questions)].slice(0, 4);
}

function compareActionPlan(best, items = []) {
  const otherNames = items.filter((item) => item.name !== best?.name).map((item) => item.name);
  const actions = [
    best ? `优先约访 ${best.name}，围绕载体需求、政策适配和落地周期确认真实意向。` : "先补充企业画像，再确定优先顺序。",
    otherNames.length ? `将 ${otherNames.join("、")} 作为备选线索，补充关键缺口后决定是否进入下一轮。` : "保留清单企业作为备选线索。",
    "生成拜访提纲与风险复核清单，把对比结论转成会前沟通问题。",
  ];
  return actions;
}

function shortlistComparisonArtifact(items) {
  if (!items || !items.length) items = state.shortlist.slice(0, 4);
  const best = compareWinner(items);
  const questions = compareOpenQuestions(items);
  const actions = compareActionPlan(best, items);
  return `
    <section class="inline-artifact compare-artifact">
      <div class="artifact-header">
        <div>
          <span class="artifact-kicker">企业对比</span>
          <h2>${items.length} 家清单企业推进优先级</h2>
          <p>${escapeHtml(compareDecisionText(best, items))}</p>
        </div>
        <div class="artifact-toolbar">
          <button class="artifact-action primary" type="button" data-prompt="基于这次对比，生成两家企业的拜访提纲。">生成拜访提纲</button>
          <button class="artifact-action" type="button" data-prompt="把这次企业对比整理成领导汇报摘要。">生成汇报摘要</button>
          <button class="artifact-action" type="button" data-export-report="">下载 Word</button>
          <button class="artifact-action" type="button" data-export-report="" data-format="pdf">下载 PDF</button>
        </div>
      </div>
      <div class="artifact-body compare-body">
        <div class="compare-executive">
          <article>
            <span>优先推进</span>
            <strong>${escapeHtml(best?.name || "待确认")}</strong>
            <p>${escapeHtml(best ? actionSuggestion(best) : "需要更多候选企业。")}</p>
          </article>
          <article>
            <span>对比维度</span>
            <strong>4 项</strong>
            <p>匹配度、承载能力、成长潜力、风险安全</p>
          </article>
          <article>
            <span>待核验</span>
            <strong>${escapeHtml(questions.length)} 项</strong>
            <p>${escapeHtml(questions[0] || "确认企业最新状态。")}</p>
          </article>
        </div>
        <div class="compare-table">
          <div class="compare-head">
            <span>企业</span>
            <span>赛道</span>
            <span>匹配分</span>
            <span>推荐依据</span>
            <span>推进建议</span>
          </div>
          ${items.map((item) => `
            <div class="compare-row">
              <strong>${escapeHtml(item.name)}</strong>
              <span>${escapeHtml([item.industry, item.subIndustry].filter(Boolean).join(" / ") || "待确认")}</span>
              <em>${escapeHtml(item.score || "-")}</em>
              <span>${escapeHtml(compactText(item.reason || "与本轮招商目标存在匹配点。", 48))}</span>
              <span>${escapeHtml(actionSuggestion(item))}</span>
            </div>
          `).join("")}
        </div>
        <div class="compare-dimensions">
          ${compareDimensionRows(items)}
        </div>
        <div class="compare-verdict">
          <span>顾问判断</span>
          <strong>${escapeHtml(best?.name || "待确认")}</strong>
          <p>${escapeHtml(compareDecisionText(best, items))}</p>
        </div>
        <div class="compare-followups">
          <article>
            <h3>会前待核验</h3>
            <ul>${questions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
          </article>
          <article>
            <h3>下一步推进</h3>
            <ol>${actions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>
          </article>
        </div>
      </div>
    </section>
  `;
}

function renderShortlistComparison(selectedIndices) {
  const indices = (selectedIndices || [...state.shelfSelection]).filter(
    (i) => Number.isFinite(i) && i >= 0 && i < state.shortlist.length
  );
  if (indices.length < 2) {
    showToast("请至少选择两家企业后再对比", "warn");
    return;
  }
  const items = indices.map((i) => state.shortlist[i]);
  const best = compareWinner(items);
  setAgentState("ready");
  ui.agentStatus.textContent = "已形成对比";
  const agentMessage = createAgentMessage();
  markActivity("形成优先级", "对比清单中企业的匹配度、风险和推进动作。", "done");
  finishActivities();
  const answer = `已基于跟进清单对比 ${items.length} 家企业。`;
  renderAgentText(answer);
  addHistory("assistant", `${answer}优先推进：${best?.name || "待确认"}。`);
  agentMessage.querySelector(".artifact-slot").innerHTML = shortlistComparisonArtifact(items);
  bindArtifactActions(agentMessage);
  state.report = {
    verdict: `建议优先推进${best?.name || "待确认"}`,
    summary: answer,
    ranked_companies: items,
    sections: [
      { id: "compare", title: "企业对比分析", body: "基于匹配度、承载能力、成长潜力和风险安全四个维度综合排序。" },
    ],
    action_plan: compareActionPlan(best, items),
  };
  state.context = { evidence: [] };
  updateInsight();
}

function renderShortlistComparisonMessage() {
  setAgentState("ready");
  ui.agentStatus.textContent = "已形成对比";
  const agentMessage = createAgentMessage();
  markActivity("形成优先级", "对比清单中企业的匹配度、风险和推进动作。", "done");
  finishActivities();
  const answer = state.shortlist.length >= 2
    ? `我已基于跟进清单对比 ${state.shortlist.length} 家企业。下面先给出可用于推进排序的简版判断。`
    : "清单里还不足两家企业，先加入至少两家后再进行对比。";
  renderAgentText(answer);
  addHistory("assistant", answer);
  agentMessage.querySelector(".artifact-slot").innerHTML = state.shortlist.length >= 2 ? shortlistComparisonArtifact() : shortlistArtifact();
  bindArtifactActions(agentMessage);
  updateInsight();
}

function companyFocusArtifact(item) {
  const index = findCandidateIndexByName(item?.name);
  const profile = index >= 0 ? state.candidates[index] : item;
  const fields = [
    ["所属赛道", [profile.industry, profile.subIndustry].filter(Boolean).join(" / ") || "待确认"],
    ["匹配分", profile.score || "-"],
    ["融资阶段", profile.financing || "待确认"],
    ["营收区间", profile.revenue || "待确认"],
    ["专利情况", profile.patents ? `${profile.patents} 项` : "待确认"],
    ["风险等级", profile.riskLevel || "待确认"],
  ];
  return `
    <section class="inline-artifact company-focus-artifact">
      <div class="artifact-header">
        <div>
          <span class="artifact-kicker">企业画像</span>
          <h2>${escapeHtml(profile.name || "当前企业")}</h2>
          <p>${escapeHtml(profile.reason || "与本轮招商目标存在匹配点，建议进一步沟通确认。")}</p>
        </div>
        <div class="artifact-toolbar">
          <button class="artifact-action primary" type="button" data-material-company="${index >= 0 ? index : 0}">生成拜访提纲</button>
          <button class="artifact-action" type="button" data-view-source="${index >= 0 ? index : 0}">推荐依据</button>
        </div>
      </div>
      <div class="artifact-body">
        <dl class="profile-grid">
          ${fields.map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join("")}
        </dl>
      </div>
    </section>
  `;
}

function renderCompanyFocusMessage(item) {
  if (!item?.name) return;
  focusCompany(item);
  setAgentState("ready");
  ui.agentStatus.textContent = "已切换企业";
  const agentMessage = createAgentMessage();
  finishActivities();
  const answer = `已切换到 ${item.name}。我会把它作为当前关注企业，后续你问“这家公司”“它为什么值得推进”时都会带上这家企业的上下文。`;
  renderAgentText(answer);
  addHistory("assistant", answer);
  agentMessage.querySelector(".artifact-slot").innerHTML = companyFocusArtifact(item);
  bindArtifactActions(agentMessage);
  updateInsight();
}

function renderStats(stats = {}) {
  setAgentState("ready");
  ui.agentStatus.textContent = "资料概览";
  state.sources = [{
    title: "本地资料覆盖概览",
    source: "本地项目资料",
    type: "local",
    snippet: `已整理 ${stats.enterprise_count ?? 0} 家企业线索，覆盖 ${stats.industry_count ?? 0} 个产业方向。`,
    match_reason: "帮助判断当前资料是否足够支撑招商筛选。",
    relation: "资料覆盖",
  }];
  const answer = `当前已整理 ${stats.enterprise_count ?? 0} 家企业线索，覆盖 ${stats.industry_count ?? 0} 个产业方向；包含 ${stats.policy_count ?? 0} 条政策资料和 ${stats.resource_count ?? 0} 项园区资源。`;
  finishActivities();
  renderAgentText(answer);
  addHistory("assistant", answer);
  state.lastSummary = answer;
  state.currentAgentMessage.querySelector(".artifact-slot").innerHTML = `
    <section class="inline-artifact">
      <div class="artifact-header">
        <div>
          <span class="artifact-kicker">资料概览</span>
          <h2>本地资料覆盖</h2>
          <p>这些资料会作为企业筛选、推荐理由和材料生成的基础。</p>
        </div>
      </div>
      <div class="artifact-body">
        <div class="artifact-metrics">
          <div class="metric"><span>企业线索</span><strong>${escapeHtml(stats.enterprise_count ?? 0)}</strong></div>
          <div class="metric"><span>政策资料</span><strong>${escapeHtml(stats.policy_count ?? 0)}</strong></div>
          <div class="metric"><span>园区资源</span><strong>${escapeHtml(stats.resource_count ?? 0)}</strong></div>
        </div>
      </div>
    </section>
  `;
  updateInsight();
}

function renderReport(payload = {}) {
  state.report = payload.report || {};
  state.context = payload.context || {};
  state.sources = payload["evi" + "dence"] || [];
  state.actions = payload.actions || [];
  state.candidates = getCandidates(payload);
  state.selectedCompanyIndex = -1;

  const summary = state.report.summary || "已形成可继续追问的招商建议。";
  state.lastSummary = compactText(summary, 700);
  addHistory("assistant", summary);
  setAgentState("ready");
  ui.agentStatus.textContent = "已形成建议";
  finishActivities();
  renderAgentText(summary);
  state.currentAgentMessage.querySelector(".artifact-slot").innerHTML = state.candidates.length ? recommendationArtifact() : "";
  bindArtifactActions(state.currentAgentMessage);
  updateInsight();
}

function findCandidateIndexByName(name) {
  if (!name) return -1;
  return state.candidates.findIndex((item) => item.name === name);
}

function focusCompany(item) {
  const index = findCandidateIndexByName(item?.name);
  if (index >= 0) state.selectedCompanyIndex = index;
  updateInsight();
}

function recommendationTitle() {
  const count = state.candidates.length;
  const requested = requestedCountFromTask(state.currentGoal);
  if (requested && count && requested !== count) return `已形成 ${count} 家候选企业建议（目标 ${requested} 家）`;
  if (count) return `${count} 家重点推进企业建议`;
  return "重点推进企业建议";
}

function recommendationSubtitle() {
  return "基于企业画像、园区政策、产业链位置和风险因素形成的优先级排序。";
}

function recommendationArtifact() {
  return `
    <section class="inline-artifact recommendation-artifact">
      <div class="artifact-header">
        <div>
          <span class="artifact-kicker">招商建议</span>
          <h2>${escapeHtml(recommendationTitle())}</h2>
          <p>${escapeHtml(recommendationSubtitle())}</p>
        </div>
        <div class="artifact-toolbar">
          <button class="artifact-action primary" type="button" data-material="outline">生成拜访提纲</button>
          <button class="artifact-action" type="button" data-prompt="请展开说明这次推荐的筛选逻辑。">查看筛选逻辑</button>
          <button class="artifact-action" type="button" data-export-report="">下载 Word</button>
          <button class="artifact-action" type="button" data-export-report="" data-format="pdf">下载 PDF</button>
        </div>
      </div>
      <div class="artifact-body">
        <div class="artifact-metrics compact">
          <div class="metric"><span>推荐企业</span><strong>${escapeHtml(state.candidates.length || "-")} 家</strong></div>
          <div class="metric"><span>高优先级</span><strong>${escapeHtml(highPriorityCount() || "-")} 家</strong></div>
          <div class="metric"><span>引用资料</span><strong>${escapeHtml(sourceCategoryCount() || "-")} 类</strong></div>
          <div class="metric wide"><span>主要风险</span><strong>${escapeHtml(mainRisksText())}</strong></div>
        </div>
        ${selectedCompanyFocus()}
        <div class="company-grid">
          ${renderCompanyCards()}
        </div>
      </div>
    </section>
  `;
}

function selectedCompanyFocus() {
  const active = selectedCompany();
  if (!active) return "";
  const profileItems = [
    ["赛道", [active.industry, active.subIndustry].filter(Boolean).join(" / ") || "待确认"],
    ["匹配分", active.score || "-"],
    ["融资", active.financing || "待确认"],
    ["营收", active.revenue || "待确认"],
    ["专利", active.patents ? `${active.patents} 项` : "待确认"],
    ["员工", active.employees ? `${active.employees} 人` : "待确认"],
    ["区域", active.region || "待确认"],
    ["资质", active.qualification || "待确认"],
    ["风险", active.riskLevel || "待确认"],
  ];
  const tags = evidenceTagsForCompany(active);
  return `
    <section class="selected-focus">
      <div>
        <span>当前查看</span>
        <strong>${escapeHtml(active.name)}</strong>
        <p>${escapeHtml(active.reason || "与本轮招商目标存在匹配点。")}</p>
        ${tags.length ? `<div class="evidence-tags">${tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}</div>` : ""}
      </div>
      <dl>
        ${profileItems.map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join("")}
      </dl>
      <footer>
        <button type="button" data-view-source="${state.selectedCompanyIndex}">推荐依据</button>
        <button type="button" data-material-company="${state.selectedCompanyIndex}">生成拜访提纲</button>
      </footer>
    </section>
  `;
}

function evidenceTagsForCompany(item) {
  const tags = [];
  if (item.revenue) tags.push(item.revenue);
  if (item.financing) tags.push(item.financing);
  if (item.patents !== undefined && item.patents !== null && item.patents !== "") tags.push(`专利 ${item.patents} 项`);
  if (item.riskLevel) tags.push(item.riskLevel);
  if (Array.isArray(item.tags)) tags.push(...item.tags.slice(0, 2));
  const kinds = [...new Set(visibleSources().map((source) => sourceKind(source.type)))];
  tags.push(...kinds.slice(0, 2));
  return tags.filter(Boolean).slice(0, 5);
}

function actionSuggestion(item) {
  const score = Number(item.score);
  if (item.riskLevel && /高/.test(item.riskLevel)) return "先补充风险核验";
  if (Number.isFinite(score) && score >= 90) return "优先约访";
  if (!item.revenue) return "确认租金承载力";
  return item.nextStep || "进入跟进池";
}

function renderCompanyCards() {
  if (!state.candidates.length) {
    return `
      <article class="company-card investment-card empty-card">
        <header><span class="rank">--</span><strong>暂无企业线索</strong><em class="score">-</em></header>
        <p>可以继续补充行业、地区、数量或风险偏好。</p>
      </article>
    `;
  }
  return state.candidates
    .map((item, index) => {
      const selected = index === state.selectedCompanyIndex;
      const inShortlist = state.shortlist.some((company) => company.name === item.name);
      const tags = evidenceTagsForCompany(item);
      return `
        <article class="company-card investment-card ${selected ? "selected" : ""}" data-company-index="${index}">
          <header>
            <span class="rank">${String(index + 1).padStart(2, "0")}</span>
            <div>
              <strong title="${escapeHtml(item.name)}">${escapeHtml(item.name || "企业线索")}</strong>
              <small>${escapeHtml([item.industry, item.subIndustry].filter(Boolean).join(" / ") || "赛道待确认")}</small>
            </div>
            <em class="score">${escapeHtml(item.score)}</em>
          </header>
          <p class="company-judgment">${escapeHtml(item.reason || "与本次招商目标存在匹配点，建议进一步沟通确认。")}</p>
          <div class="evidence-tags">
            ${tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}
          </div>
          <div class="card-next-step"><span>建议动作</span><strong>${escapeHtml(actionSuggestion(item))}</strong></div>
          <div class="card-actions">
            <button type="button" data-view-source="${index}">推荐依据</button>
            <button type="button" data-material-company="${index}">生成拜访提纲</button>
            <button type="button" data-add-company="${index}" ${inShortlist ? "disabled" : ""}>${inShortlist ? "已加入" : "加入清单"}</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function bindArtifactActions(root) {
  root.querySelectorAll("[data-company-index]").forEach((card) => {
    card.addEventListener("click", (event) => {
      if (event.target.closest("button")) return;
      state.selectedCompanyIndex = Number(card.dataset.companyIndex);
      const slot = root.querySelector(".artifact-slot");
      if (slot) slot.innerHTML = recommendationArtifact();
      bindArtifactActions(root);
      updateInsight();
    });
  });
  root.querySelectorAll("[data-view-source]").forEach((button) => {
    button.addEventListener("click", () => {
      const nextIndex = Number(button.dataset.viewSource);
      if (Number.isFinite(nextIndex) && nextIndex >= 0) state.selectedCompanyIndex = nextIndex;
      const slot = root.querySelector(".artifact-slot");
      if (slot && state.candidates.length) slot.innerHTML = recommendationArtifact();
      bindArtifactActions(root);
      updateInsight();
      const sources = visibleSources();
      const sourceIndex = sourceIndexForCompany();
      if (sources[sourceIndex]) openSource(sourceIndex, sources);
    });
  });
  root.querySelectorAll("[data-material-company]").forEach((button) => {
    button.addEventListener("click", () => {
      const nextIndex = Number(button.dataset.materialCompany);
      if (Number.isFinite(nextIndex) && nextIndex >= 0) state.selectedCompanyIndex = nextIndex;
      const slot = root.querySelector(".artifact-slot");
      if (slot && state.candidates.length) slot.innerHTML = recommendationArtifact();
      bindArtifactActions(root);
      updateInsight();
      generateMaterial("outline");
    });
  });
  root.querySelectorAll("[data-add-company]").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.addCompany);
      routeAction(ACTION_TYPES.local, "add_to_shortlist", {
        item: state.candidates[index],
        index,
        root,
      });
    });
  });
  root.querySelectorAll("[data-shortlist-focus]").forEach((button) => {
    button.addEventListener("click", () => {
      routeAction(ACTION_TYPES.local, "focus_company", { index: Number(button.dataset.shortlistFocus) });
    });
  });
  root.querySelectorAll("[data-shortlist-material]").forEach((button) => {
    button.addEventListener("click", () => {
      const item = state.shortlist[Number(button.dataset.shortlistMaterial)];
      focusCompany(item);
      routeAction(ACTION_TYPES.agent, "outline");
    });
  });
  root.querySelectorAll("[data-shortlist-remove]").forEach((button) => {
    button.addEventListener("click", () => {
      routeAction(ACTION_TYPES.local, "remove_from_shortlist", {
        index: Number(button.dataset.shortlistRemove),
        root,
      });
    });
  });
  root.querySelectorAll("[data-compare-shortlist]").forEach((button) => {
    button.addEventListener("click", () => routeAction(ACTION_TYPES.agent, "compare"));
  });
  root.querySelectorAll("[data-material]").forEach((button) => {
    button.addEventListener("click", () => routeAction(ACTION_TYPES.agent, button.dataset.material || "outline"));
  });
  root.querySelectorAll("[data-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      ui.input.value = button.dataset.prompt || "";
      ui.input.focus();
    });
  });
  root.querySelectorAll("[data-export-report]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!state.report) return;
      const fmt = button.dataset.format || "docx";
      const label = fmt === "pdf" ? "下载 PDF" : "下载 Word";
      button.disabled = true;
      button.textContent = "导出中...";
      try {
        const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
        await downloadFile("/api/export/report", {
          report: state.report,
          context: state.context || {},
          format: fmt,
        }, `园区重点招商企业推荐建议_${dateStr}.${fmt === "pdf" ? "pdf" : "docx"}`);
      } catch (err) {
        alert(err.message);
      } finally {
        button.disabled = false;
        button.textContent = label;
      }
    });
  });
  root.querySelectorAll("[data-export-material]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!state.lastMaterial) return;
      const fmt = button.dataset.format || "docx";
      const label = fmt === "pdf" ? "下载 PDF" : "下载 Word";
      button.disabled = true;
      button.textContent = "导出中...";
      try {
        const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
        const materialType = state.lastMaterial.type || "outline";
        const company = state.lastMaterial.company_name || state.lastMaterial.audience || "";
        const ext = fmt === "pdf" ? "pdf" : "docx";
        let filename;
        if (materialType === "outline" && company) {
          filename = `关于赴${company}开展招商拜访的提纲_${dateStr}.${ext}`;
        } else if (materialType === "wechat" && company) {
          filename = `${company}招商跟进话术_${dateStr}.${ext}`;
        } else {
          const title = (state.lastMaterial.title || "招商材料").replace(/[\\/:*?"<>|]/g, "");
          filename = `${title}_${dateStr}.${ext}`;
        }
        await downloadFile("/api/export/material", {
          material: state.lastMaterial,
          type: materialType,
          format: fmt,
        }, filename);
      } catch (err) {
        alert(err.message);
      } finally {
        button.disabled = false;
        button.textContent = label;
      }
    });
  });
}

async function generateMaterial(type, taskOverride = "", options = {}) {
  if (!state.report) return;
  const active = options.scope === "thread" ? null : selectedCompany() || state.candidates[0] || null;
  if (active && state.selectedCompanyIndex < 0) {
    state.selectedCompanyIndex = state.candidates.indexOf(active);
    updateInsight();
  }
  const agentMessage = createAgentMessage();
  agentMessage.querySelector(".message-meta span").textContent = "材料生成";
  renderAgentText(`正在整理${type === "brief" ? "汇报摘要" : active?.name ? `${active.name} 的招商材料` : "可直接使用的招商材料"}。`);
  markActivity("生成结果", "根据当前结论整理可复用文本。", "active");
  try {
    state.currentAbort = new AbortController();
    state.stopRequested = false;
    const materialTask = taskOverride || `生成${type === "wechat" ? "邀约话术" : type === "briefing" ? "汇报摘要" : type === "comparison" ? "企业对比材料" : "拜访提纲"}`;
    const body = {
      type,
      ...buildRequestPayload(materialTask),
      task: materialTask || state.currentGoal,
      company: active?.name || "",
      selectedCompany: active?.name || "",
      report: state.report,
      thread_context: buildThreadContext(),
    };
    const data = await requestJson("/api/material", {
      method: "POST",
      body: JSON.stringify(body),
      signal: state.currentAbort.signal,
    });
    const material = data.material || {};
    material.type = type;
    material.company_name = active?.name || "";
    state.lastMaterial = material;
    const content = Array.isArray(material.content) ? material.content : [material.content || ""];
    finishActivities();
    renderAgentText(`已生成：${material.title || "招商材料"}。`);
    addHistory("assistant", `已生成：${material.title || "招商材料"}。`);
    agentMessage.querySelector(".artifact-slot").innerHTML = `
      <section class="inline-artifact material-artifact">
        <div class="artifact-header">
          <div>
            <span class="artifact-kicker">${escapeHtml(type === "comparison" ? "企业对比" : "招商材料包")}</span>
            <h2>${escapeHtml(material.title || "招商材料")}</h2>
            <p>${escapeHtml(material.audience || "可用于后续招商推进。")}</p>
          </div>
          <div class="artifact-toolbar">
            <button class="artifact-action" type="button" data-prompt="基于这份材料，帮我再压缩成领导汇报摘要。">生成汇报摘要</button>
            <button class="artifact-action" type="button" data-prompt="把这份材料改成更适合微信沟通的语气。">改成微信话术</button>
            <button class="artifact-action" type="button" data-export-material="">下载 Word</button>
            <button class="artifact-action" type="button" data-export-material="" data-format="pdf">下载 PDF</button>
          </div>
        </div>
        <div class="artifact-body">
          <article class="material-card">
            <span>招商材料</span>
            ${content.map((line) => `<p>${escapeHtml(line)}</p>`).join("")}
            ${Array.isArray(material.source_notes) && material.source_notes.length ? `<footer>${material.source_notes.map(escapeHtml).join("；")}</footer>` : ""}
          </article>
        </div>
      </section>
    `;
    bindArtifactActions(agentMessage);
  } catch (error) {
    if (state.stopRequested || error.name === "AbortError") return;
    renderAgentText(`材料暂未生成：${error.message}`);
  } finally {
    state.currentAbort = null;
  }
}

function openSource(index, list = visibleSources()) {
  const item = list[index];
  if (!item) return;
  const active = selectedCompany();
  $("#dialogType").textContent = "判断依据";
  $("#dialogTitle").textContent = basisDialogTitle(item);
  $("#dialogSource").textContent = basisKeyFact(item, active);
  $("#dialogSnippet").textContent = basisSupportedJudgment(item, active);
  $("#dialogReason").textContent = basisVerification(item, active);
  $("#dialogRelation").textContent = basisActionImpact(item, active);
  ui.dialog.showModal();
}

function verificationHint(item = {}) {
  const type = String(item.type || "");
  if (/policy/i.test(type)) return "核验政策适用条件、申报周期和兑现材料。";
  if (/risk/i.test(type)) return "推进前复核经营状态、负面记录和关键风险来源。";
  if (/crm/i.test(type)) return "复核最近联系人、意向阶段和下一次触达安排。";
  if (/enterprise|structured|local/i.test(type)) return "复核营收、融资、专利和团队信息是否为最新口径。";
  return "用于会前准备时补充核验，不作为单一决策依据。";
}

async function analyzeWithStream(task, signal) {
  const payload = buildRequestPayload(task);
  const timeoutMs = 60000;
  const timeoutId = setTimeout(() => signal?.dispatchEvent?.(new Event("abort")), timeoutMs);
  const cleanup = () => clearTimeout(timeoutId);
  signal?.addEventListener("abort", cleanup, { once: true });

  const response = await fetch(apiUrl("/api/message_stream"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
  if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let lastPayload = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (!line.trim()) continue;
      const event = JSON.parse(line);
      handleStreamEvent(event);
      if (event.event === "chunk") {
        stopLiveProgress(false);
        setLiveStatus("正在整理回复");
        state.streamingText += event.content || "";
        renderAgentText(state.streamingText);
      }
      if (event.event === "message") {
        stopLiveProgress(false);
        state.streamingText = "";
        lastPayload = event;
        renderPlainAnswer(event.content || "");
      }
      if (event.event === "context") {
        stopLiveProgress(false);
        setLiveStatus("正在整理结果");
        state.streamingText = "";
        lastPayload = event;
        state.sources = event["evi" + "dence"] || [];
        state.candidates = getCandidates(event);
        updateInsight();
        updateWorkstream("整理返回结果");
      }
      if (event.event === "stats") {
        lastPayload = event;
        renderStats(event.stats || {});
      }
      if (event.event === "report") {
        state.streamingText = "";
        lastPayload = event;
        renderReport(event);
      }
      if (event.event === "error") {
        state.jsonBuffer = "";
        const error = new Error(event.error || "任务没有完成");
        error.payload = event;
        throw error;
      }
    }
  }
  return lastPayload;
}

async function runMission(task) {
  const missing = detectMissingPlaceholder(task);
  if (missing) {
    showToast(missing, "warn");
    return null;
  }
  showWorkspace();

  if (isMaterialRequest(task) && state.report) {
    addMessage("user", task);
    addHistory("user", task);
    const type = materialTypeFromTask(task);
    await generateMaterial(type, task, { scope: /对比|清单|这次|当前推荐|推荐/.test(task) ? "thread" : "company" });
    return { ok: true, intent: "material" };
  }

  if (isShortlistQuestion(task) && !/生成|分析|推荐|筛选|拜访|话术|汇报|材料|计划/.test(task)) {
    addMessage("user", task);
    addHistory("user", task);
    if (/意思|是什么|代表|说明|解释|为什么/.test(task)) renderShortlistExplanation();
    else renderShortlistMessage();
    return { ok: true, intent: "shortlist_state" };
  }

  // Reset stale context when a new independent question arrives
  const isContextual = isContextualFollowup(task);
  if (!isContextual && !isMetaConversation(task)) {
    state.currentGoal = task;
    state.selectedCompanyIndex = -1;
  }
  if (isMetaConversation(task) || (!isContextual && !/推荐|筛选|分析|评估|生成|企业|公司|产业|政策/.test(task))) {
    state.report = null;
    state.context = null;
    state.sources = [];
    state.actions = [];
    state.candidates = [];
    state.lastSummary = "";
  }
  setAgentState("running");
  ui.agentStatus.textContent = "正在分析";
  ui.goalUnderstanding.textContent = state.currentGoal || task;
  setLiveStatus("正在处理你的请求");
  state.streamingText = "";
  state.jsonBuffer = "";
  state.receivedTextDelta = false;
  state.stopRequested = false;
  state.currentAbort = new AbortController();
  addMessage("user", task);
  addHistory("user", task);
  createAgentMessage();
  try {
    let payload;
    try {
      payload = await analyzeWithStream(task, state.currentAbort.signal);
    } catch (streamError) {
      if (state.stopRequested || streamError.name === "AbortError") return { ok: false, intent: "stopped" };
      if (isMetaConversation(task)) {
        renderMetaFallback(task);
        return { ok: true, intent: "meta_fallback" };
      }
      setLiveStatus("正在通过常规接口完成分析");
      markActivity("正在分析", "流式返回不可用，正在通过常规接口完成。", "active");
      const body = buildRequestPayload(task);
      payload = await requestJson("/api/analyze", {
        method: "POST",
        body: JSON.stringify(body),
        signal: state.currentAbort.signal,
      });
      if (payload.intent === "data_inventory") renderStats(payload.stats || {});
      else renderReport(payload);
    }
    return payload;
  } catch (error) {
    if (state.stopRequested || error.name === "AbortError") return { ok: false, intent: "stopped" };
    stopLiveProgress(false);
    setAgentState("ready");
    finishActivities();
    const msg = String(error.message || "");
    if (/fetch|network|connect|ECONN|timeout|超时/i.test(msg)) {
      ui.agentStatus.textContent = "连接失败";
      renderAgentText(`后端服务暂时无法连接（${msg}）。请确认 API 地址和服务状态，或稍后重试。`);
    } else if (/没有找到|不足|线索|匹配/i.test(msg)) {
      ui.agentStatus.textContent = "需要补充";
      renderAgentText(`这次还没有形成可交付结果：${msg}。可以补充企业名称、产业方向、地区或数量后继续。`);
    } else {
      ui.agentStatus.textContent = "请求失败";
      renderAgentText(`请求未完成：${msg}。可以重试或调整条件后继续。`);
    }
  } finally {
    state.currentAbort = null;
  }
}

function resetThread(options = {}) {
  const { showHome = true, persist = true } = options;
  if (persist) persistCurrentThread();
  stopLiveProgress(false);
  state.currentAbort?.abort();
  state.currentAbort = null;
  state.stopRequested = false;
  state.threadId = createThreadId();
  state.currentGoal = "";
  state.selectedCompanyIndex = -1;
  state.lastSummary = "";
  state.report = null;
  state.context = null;
  state.sources = [];
  state.actions = [];
  state.candidates = [];
  state.shortlist = [];
  state.history = [];
  state.currentAgentMessage = null;
  state.activityItems = [];
  state.streamingText = "";
  ui.thread.innerHTML = "";
  ui.input.value = "";
  ui.goalUnderstanding.textContent = "等待你交办招商目标。";
  ui.sourceList.innerHTML = `<p class="muted">形成建议后，会列出影响判断的关键资料。</p>`;
  ui.criteriaList.innerHTML = FALLBACK_CRITERIA.map((item) => `<span>${item}</span>`).join("");
  ui.activeCompany.innerHTML = `<p class="muted">点击推荐卡片后，这里会同步当前关注企业。</p>`;
  ui.riskList.innerHTML = `<p class="muted">完成分析后，会列出需要复核的事项。</p>`;
  ui.nextActions.innerHTML = `<p class="muted">形成推荐后，可以继续生成材料或调整条件。</p>`;
  ui.currentProject.textContent = "当前任务：重点企业筛选";
  ui.agentStatus.textContent = "待命";
  setAgentState("idle");
  updateCommandContext();
  ui.threadScroll.scrollTop = 0;
  if (showHome) showHomeView();
  else showWorkspace();
}

function bindPromptButtons(root = document) {
  root.querySelectorAll("[data-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      ui.input.value = button.dataset.prompt || "";
      ui.input.focus();
    });
  });
}

function bindCommandActions(root = document) {
  root.querySelectorAll("[data-command-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const promptMap = {
        outline: "基于当前招商研判，帮我生成企业拜访提纲。",
        wechat: "基于当前推荐企业，帮我生成微信邀约话术。",
        briefing: "把当前推荐整理成领导汇报摘要。",
        compare: "帮我对比清单中的候选企业，给出优先级排序。",
      };
      const action = button.dataset.commandAction || "outline";
      ui.input.value = promptMap[action] || `帮我${button.textContent.trim()}`;
      ui.input.focus();
    });
  });
}


function bindControls() {
  ui.homeForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const task = ui.homeInput.value.trim();
    if (!task) return;
    showHomeHint("");
    ui.homeInput.value = "";
    startThreadFromGoal(task);
  });

  ui.homeInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      ui.homeForm.requestSubmit();
    }
  });

  ui.homeInput.addEventListener("input", () => {
    if (ui.homeHint?.classList.contains("visible")) {
      showHomeHint("");
    }
  });

  document.querySelectorAll("[data-home-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      const prompt = button.dataset.homePrompt || "";
      if (!prompt) return;
      if (document.body.dataset.view === "workspace") {
        ui.input.value = prompt;
        ui.input.focus();
        ui.input.style.height = "auto";
        ui.input.style.height = `${Math.min(108, ui.input.scrollHeight)}px`;
      } else {
        ui.homeInput.value = prompt;
        ui.homeInput.focus();
      }
    });
  });

  ui.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const task = ui.input.value.trim();
    if (!task) return;
    ui.input.value = "";
    ui.input.style.height = "auto";
    ui.form.querySelector("button[type='submit']").disabled = true;
    await runMission(task);
    ui.form.querySelector("button[type='submit']").disabled = false;
    ui.input.focus();
  });

  ui.input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      ui.form.requestSubmit();
    }
  });

  ui.input.addEventListener("input", () => {
    ui.input.style.height = "auto";
    ui.input.style.height = `${Math.min(108, ui.input.scrollHeight)}px`;
  });

  ui.dialogClose.addEventListener("click", () => ui.dialog.close());
  ui.newThreadButton.addEventListener("click", () => resetThread({ showHome: true }));
  ui.brandHomeButton.addEventListener("click", showHomeView);
  ui.historyButton.addEventListener("click", openHistoryDrawer);
  ui.openHistoryFromHome.addEventListener("click", openHistoryDrawer);
  ui.historyClose.addEventListener("click", closeHistoryDrawer);
  ui.drawerOverlay.addEventListener("click", closeHistoryDrawer);
  bindPromptButtons(document);
  bindCommandActions(document);
  bindMessageActions(document);
  if (ui.shelfTab) {
    ui.shelfTab.addEventListener("click", () => {
      const expanded = ui.shelf.dataset.expanded === "true";
      ui.shelf.dataset.expanded = expanded ? "false" : "true";
    });
    ui.shelf.addEventListener("mouseenter", () => {
      if (ui.shelf.dataset.expanded !== "true") ui.shelf.dataset.expanded = "true";
    });
    ui.shelf.addEventListener("mouseleave", () => {
      if (ui.shelf.dataset.expanded === "true") ui.shelf.dataset.expanded = "false";
    });
  }
  if (ui.shelfCompare) {
    ui.shelfCompare.addEventListener("click", () => {
      const selected = [...state.shelfSelection].sort();
      if (selected.length < 2) return;
      renderShortlistComparison(selected);
    });
  }
  if (ui.shelfBatchOutline) {
    ui.shelfBatchOutline.addEventListener("click", () => {
      if (!state.shortlist.length) return;
      const names = state.shortlist.map((c) => c.name).slice(0, 3).join("、");
      ui.input.value = `基于跟进清单中的 ${names}，生成一份招商拜访提纲。`;
      ui.input.focus();
    });
  }
  updateCommandContext();
  renderShortlistShelf();
}

async function checkHealth() {
  try {
    const data = await requestJson("/api/health");
    ui.health.textContent = data.llm_configured ? "在线" : "未配置";
  } catch {
    ui.health.textContent = "未连接";
  }
}

async function loadStats() {
  try {
    const data = await requestJson("/api/stats");
    const stats = data.stats || {};
    ui.corpusDetail.textContent = `已连接 ${stats.enterprise_count ?? 0} 家企业线索、${stats.policy_count ?? 0} 条政策资料、${stats.resource_count ?? 0} 项园区资源`;
  } catch {
    ui.corpusDetail.textContent = "请确认本地服务已启动";
  }
}

loadThreads();
renderRecentThreads();
renderHistoryList();
showHomeView();
bindControls();
checkHealth();
loadStats();
initDebugPanel();

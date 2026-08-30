const statusEl = document.querySelector("#status");
const API_BASE = "http://127.0.0.1:8765";
const resumeTextEl = document.querySelector("#resumeText");
const resumeFileEl = document.querySelector("#resumeFile");
const rulesPreviewEl = document.querySelector("#rulesPreview");
const resultsEl = document.querySelector("#results");
const resultCountEl = document.querySelector("#resultCount");
const debugTraceEl = document.querySelector("#debugTrace");
const serviceBadgeEl = document.querySelector("#serviceBadge");
const rankerBadgeEl = document.querySelector("#rankerBadge");
const jobCountBadgeEl = document.querySelector("#jobCountBadge");
const profileSummaryEl = document.querySelector("#profileSummary");
const resultHintEl = document.querySelector("#resultHint");
const diagnosticSummaryEl = document.querySelector("#diagnosticSummary");
const scanModeEl = document.querySelector("#scanMode");
const maxCandidatesEl = document.querySelector("#maxCandidates");
const filterButtons = Array.from(document.querySelectorAll(".filter-button"));
const trackerListEl = document.querySelector("#trackerList");
const trackerCountEl = document.querySelector("#trackerCount");
const savedCountEl = document.querySelector("#savedCount");
const readyCountEl = document.querySelector("#readyCount");
const appliedCountEl = document.querySelector("#appliedCount");
const interviewCountEl = document.querySelector("#interviewCount");
const dueSoonCountEl = document.querySelector("#dueSoonCount");
const overdueCountEl = document.querySelector("#overdueCount");
const trackerSearchEl = document.querySelector("#trackerSearch");
const trackerStatusFilterEl = document.querySelector("#trackerStatusFilter");
const trackerSortEl = document.querySelector("#trackerSort");
let renderedJobs = [];
let renderedResultItems = [];
let lastResults = [];
let activeFilter = "all";
let savedJobs = [];
let trackerSearch = "";
let trackerStatusFilter = "all";
let trackerSort = "priority";

document.querySelector("#healthButton").addEventListener("click", checkHealth);
document.querySelector("#uploadFileButton").addEventListener("click", uploadResumeFile);
document.querySelector("#saveResumeButton").addEventListener("click", saveResume);
document.querySelector("#rulesButton").addEventListener("click", generateRules);
document.querySelector("#scanButton").addEventListener("click", scanCurrentPage);
document.querySelector("#exportTrackerButton").addEventListener("click", exportTrackerCsv);
document.querySelector("#clearTrackerButton").addEventListener("click", clearTracker);
document.querySelector("#saveVisibleResultsButton").addEventListener("click", saveVisibleResultsToTracker);
scanModeEl.addEventListener("change", applyScanMode);
trackerSearchEl.addEventListener("input", updateTrackerSearch);
trackerStatusFilterEl.addEventListener("change", updateTrackerStatusFilter);
trackerSortEl.addEventListener("change", updateTrackerSort);
for (const button of filterButtons) button.addEventListener("click", updateResultFilter);
resultsEl.addEventListener("click", openJobDetailFromResult);
resultsEl.addEventListener("click", saveResultToTracker);
resultsEl.addEventListener("click", copyResultSummary);
resultsEl.addEventListener("click", generateApplicationKitFromResult);
trackerListEl.addEventListener("click", handleTrackerClick);
trackerListEl.addEventListener("change", handleTrackerStatusChange);
trackerListEl.addEventListener("change", handleTrackerFieldInput);
trackerListEl.addEventListener("input", handleTrackerFieldInput);

init();

async function init() {
  const stored = await chrome.storage.local.get(["resumeText", "rules", "lastResults", "lastDebugTrace", "scanPrefs", "resultFilter", "savedJobs", "trackerPrefs"]);
  savedJobs = stored.savedJobs || [];
  hydrateTrackerPrefs(stored.trackerPrefs || {});
  if (stored.resumeText) resumeTextEl.value = stored.resumeText;
  if (stored.scanPrefs) hydrateScanPrefs(stored.scanPrefs);
  if (stored.resultFilter) {
    activeFilter = stored.resultFilter;
    updateFilterButtons();
  }
  if (stored.rules) {
    rulesPreviewEl.textContent = JSON.stringify(stored.rules.profile || stored.rules, null, 2);
    updateProfileSummary(stored.rules);
  }
  if (stored.lastResults) renderResults(stored.lastResults.results || [], stored.lastResults.source);
  if (stored.lastDebugTrace) renderDebugTrace(stored.lastDebugTrace);
  renderTracker();
  await checkHealth();
}

async function checkHealth() {
  setStatus("检查本地服务...");
  setServiceBadge("检查中");
  try {
    await send({ type: "HEALTH" });
    setStatus("本地服务已连接");
    setServiceBadge("已连接");
  } catch (error) {
    setStatus("未连接本地服务，请启动 FastAPI");
    setServiceBadge("未连接");
  }
}

async function saveResume() {
  const text = resumeTextEl.value.trim();
  if (!text) return setStatus("请先粘贴简历文本");
  setBusy(true);
  try {
    const response = await send({ type: "UPLOAD_RESUME", text });
    await chrome.storage.local.set({ resumeText: text, resumeId: response.resume_id });
    setStatus(`简历已保存：已抽取 ${response.text_length} 字`);
    updateProfileSummary({ textLength: response.text_length });
  } catch (error) {
    setStatus(`保存失败：${error.message}`);
  } finally {
    setBusy(false);
  }
}

async function uploadResumeFile() {
  const file = resumeFileEl.files?.[0];
  if (!file) return setStatus("请选择 PDF、DOCX 或 TXT 简历文件");
  setBusy(true);
  setStatus("上传简历文件...");
  try {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(`${API_BASE}/resume/upload`, { method: "POST", body: form });
    if (!response.ok) throw new Error(await response.text());
    const payload = await response.json();
    const extractedText = payload.extracted_text || payload.preview || "";
    await chrome.storage.local.set({ resumeId: payload.resume_id, resumeText: extractedText });
    resumeTextEl.value = extractedText;
    setStatus(`简历文件已上传：已抽取 ${payload.text_length} 字`);
    updateProfileSummary({ textLength: payload.text_length });
  } catch (error) {
    setStatus(`上传失败：${error.message}`);
  } finally {
    setBusy(false);
  }
}

async function generateRules() {
  const stored = await chrome.storage.local.get(["resumeId"]);
  const resumeText = resumeTextEl.value.trim();
  setBusy(true);
  setStatus("生成匹配规则...");
  try {
    const response = await send({ type: "GENERATE_RULES", resumeId: stored.resumeId, resumeText });
    await chrome.storage.local.set({ resumeId: response.resume_id, rules: response });
    rulesPreviewEl.textContent = JSON.stringify(response.profile, null, 2);
    setStatus(`规则已生成：${response.source}`);
    updateProfileSummary(response);
  } catch (error) {
    setStatus(`规则生成失败：${error.message}`);
  } finally {
    setBusy(false);
  }
}

async function scanCurrentPage() {
  const options = {
    scanMode: scanModeEl.value,
    topN: Number(document.querySelector("#topN").value || 5),
    maxPages: Number(document.querySelector("#maxPages").value || 10),
    maxJobs: Number(document.querySelector("#maxJobs").value || 100),
    maxDetails: Number(document.querySelector("#maxDetails").value || 30),
    maxCandidates: Number(maxCandidatesEl.value || 30)
  };
  await chrome.storage.local.set({ scanPrefs: options });
  setBusy(true);
  resultsEl.innerHTML = "";
  lastResults = [];
  renderedJobs = [];
  jobCountBadgeEl.textContent = "扫描中";
  rankerBadgeEl.textContent = "运行中";
  resultHintEl.textContent = "正在抽取岗位与详情链接";
  setStatus("扫描网页中...");
  try {
    const response = await send({ type: "SCAN_ACTIVE_TAB", options });
    if (response.status === "login_required") {
      setStatus("页面需要登录，请登录后再次扫描");
      return;
    }
    if (response.status === "partial_error") {
      renderResults([], "partial_error");
      renderDebugTrace(response.debugTrace || []);
      jobCountBadgeEl.textContent = String(response.totalJobs || 0);
      rankerBadgeEl.textContent = "error";
      setStatus(`扫描部分失败：已抽取 ${response.totalJobs || 0} 个岗位，请展开诊断查看错误`);
      return;
    }
    renderResults(response.ranked?.results || [], response.ranked?.source);
    renderDebugTrace([...(response.debugTrace || []), ...((response.ranked?.diagnostics || []).map((message) => ({ step: "ranker", message })))]);
    jobCountBadgeEl.textContent = String(response.totalJobs || 0);
    rankerBadgeEl.textContent = response.ranked?.source || "unknown";
    setStatus(`扫描完成：${response.totalJobs || 0} 个岗位，排序来源：${response.ranked?.source || "unknown"}`);
  } catch (error) {
    setStatus(`扫描失败：${error.message}`);
  } finally {
    setBusy(false);
  }
}

function renderDebugTrace(trace) {
  if (!debugTraceEl) return;
  debugTraceEl.textContent = JSON.stringify(trace || [], null, 2);
  renderDiagnosticSummary(trace || []);
}

function renderResults(results, source) {
  lastResults = results || [];
  const visibleResults = filterResults(lastResults);
  resultCountEl.textContent = source ? `${visibleResults.length}/${lastResults.length} · ${source}` : `${visibleResults.length}/${lastResults.length}`;
  resultHintEl.textContent = source ? `排序来源：${source}` : "等待扫描";
  resultsEl.innerHTML = "";
  renderedJobs = visibleResults.map((item) => ({ ...(item.job || {}), detail_url: bestJobUrl(item) }));
  renderedResultItems = visibleResults;
  if (!visibleResults.length) {
    resultsEl.innerHTML = `<div class="empty-state">
      <strong>${lastResults.length ? "当前筛选下暂无结果" : "暂无推荐结果"}</strong>
      <span>${lastResults.length ? "切换筛选条件查看其他岗位" : "上传简历并扫描当前招聘页面后，这里会显示排序结果"}</span>
    </div>`;
    return;
  }
  for (const [index, item] of visibleResults.entries()) {
    const card = document.createElement("article");
    card.className = "result-card";
    const reasons = listHtml(item.reasons);
    const risks = listHtml(item.risks);
    const score = clamp(Number(item.score || 0), 0, 100);
    const decision = item.decision || "maybe";
    const decisionClass = normalizeDecision(decision);
    const detailUrl = bestJobUrl(item);
    const hasRealDetail = isLikelyDetailUrl(detailUrl);
    card.innerHTML = `
      <div class="result-top">
        <h3>${escapeHtml(item.rank || index + 1)}. ${escapeHtml(item.title || item.job?.title || "未命名岗位")}</h3>
        <span class="decision ${escapeHtml(decisionClass)}">${escapeHtml(decisionLabel(decisionClass))}</span>
      </div>
      <div class="score-row">
        <span class="score-value">${escapeHtml(score)} 分</span>
        <div class="score-track"><div class="score-fill" style="width: ${escapeAttribute(score)}%"></div></div>
      </div>
      <div class="meta">
        ${item.company ? `<span class="chip">${escapeHtml(item.company)}</span>` : ""}
        <span class="chip ${hasRealDetail ? "detail-chip" : "detail-chip missing"}">${hasRealDetail ? "详情链接已捕获" : "需定位详情"}</span>
      </div>
      ${reasons ? `<strong>理由</strong>${reasons}` : ""}
      ${risks ? `<strong>风险</strong>${risks}` : ""}
      <div class="result-actions">
        <button class="save-job-button" data-index="${index}">加入岗位库</button>
        <button class="copy-summary-button" data-index="${index}">复制摘要</button>
        <button class="kit-result-button" data-index="${index}">生成材料包</button>
        <button class="open-job-button" data-index="${index}">打开岗位详情</button>
      </div>
    `;
    resultsEl.appendChild(card);
  }
}

async function saveResultToTracker(event) {
  const button = event.target.closest(".save-job-button");
  if (!button) return;
  const item = renderedResultItems[Number(button.dataset.index)];
  if (!item) return;
  const result = upsertSavedJob(item);
  await persistTracker();
  setStatus(result === "added" ? "已加入岗位库" : "岗位库已更新");
}

async function saveVisibleResultsToTracker() {
  if (!renderedResultItems.length) return setStatus("当前筛选下没有可保存结果");
  let added = 0;
  let updated = 0;
  for (const item of renderedResultItems) {
    const result = upsertSavedJob(item);
    if (result === "added") added += 1;
    if (result === "updated") updated += 1;
  }
  await persistTracker();
  setStatus(`已保存 ${added} 个新岗位，更新 ${updated} 个岗位`);
}

function upsertSavedJob(item) {
  const job = item.job || {};
  const key = trackerKey(item);
  const existing = savedJobs.find((entry) => entry.key === key);
  const payload = {
    key,
    title: item.title || job.title || "未命名岗位",
    company: item.company || job.company || "",
    score: Number(item.score || 0),
    decision: normalizeDecision(item.decision),
    job_url: bestJobUrl(item),
    reasons: item.reasons || [],
    risks: item.risks || [],
    missing_skills: item.missing_skills || [],
    job,
    status: existing?.status || "saved",
    priority: existing?.priority || "medium",
    note: existing?.note || "",
    tags: existing?.tags || "",
    deadline: existing?.deadline || "",
    next_action: existing?.next_action || "",
    saved_at: existing?.saved_at || new Date().toISOString()
  };
  if (existing) {
    Object.assign(existing, payload);
    return "updated";
  }
  savedJobs.unshift(payload);
  return "added";
}

function trackerKey(item) {
  const job = item.job || {};
  return bestJobUrl(item) || `${item.title || job.title}|${job.source_url || ""}`;
}

async function copyResultSummary(event) {
  const button = event.target.closest(".copy-summary-button");
  if (!button) return;
  const item = renderedResultItems[Number(button.dataset.index)];
  if (!item) return;
  const job = item.job || {};
  const text = [
    `岗位：${item.title || job.title || ""}`,
    `公司：${item.company || job.company || ""}`,
    `分数：${item.score || 0}`,
    `决策：${decisionLabel(normalizeDecision(item.decision))}`,
    `链接：${bestJobUrl(item)}`,
    `理由：${(item.reasons || []).join("；")}`,
    `风险：${(item.risks || []).join("；")}`,
    `缺失技能：${(item.missing_skills || []).join("；")}`
  ].filter(Boolean).join("\n");
  await navigator.clipboard.writeText(text);
  setStatus("岗位分析摘要已复制");
}

async function generateApplicationKitFromResult(event) {
  const button = event.target.closest(".kit-result-button");
  if (!button) return;
  const item = renderedResultItems[Number(button.dataset.index)];
  if (!item) return;
  await generateAndCopyApplicationKit(applicationKitPayloadFromResult(item));
}

async function openJobDetailFromResult(event) {
  const button = event.target.closest(".open-job-button");
  if (!button) return;
  try {
    const job = renderedJobs[Number(button.dataset.index)] || {};
    await send({ type: "OPEN_JOB_DETAIL", job });
  } catch (error) {
    setStatus(`打开岗位失败：${error.message}`);
  }
}

function listHtml(items) {
  if (!items || !items.length) return "";
  return `<ul>${items.slice(0, 4).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function setBusy(isBusy) {
  for (const button of document.querySelectorAll("button")) button.disabled = isBusy;
}

function setStatus(text) {
  statusEl.textContent = text;
}

function setServiceBadge(text) {
  if (serviceBadgeEl) serviceBadgeEl.textContent = text;
}

function updateProfileSummary(payload) {
  if (!profileSummaryEl) return;
  const profile = payload?.profile || payload;
  if (payload?.textLength) {
    profileSummaryEl.textContent = `${payload.textLength} 字，待生成规则`;
    return;
  }
  const roles = profile?.target_roles || [];
  const skills = profile?.core_skills || [];
  if (roles.length || skills.length) {
    profileSummaryEl.textContent = [...roles.slice(0, 1), ...skills.slice(0, 3)].join(" / ");
  } else {
    profileSummaryEl.textContent = "规则已生成";
  }
}

function applyScanMode() {
  const mode = scanModeEl.value;
  const presets = {
    fast: { topN: 5, maxPages: 3, maxJobs: 50, maxDetails: 8, maxCandidates: 15 },
    balanced: { topN: 5, maxPages: 10, maxJobs: 100, maxDetails: 30, maxCandidates: 30 },
    deep: { topN: 10, maxPages: 20, maxJobs: 250, maxDetails: 80, maxCandidates: 50 }
  };
  hydrateScanPrefs({ scanMode: mode, ...(presets[mode] || presets.balanced) });
}

function hydrateScanPrefs(prefs) {
  if (prefs.scanMode && scanModeEl) scanModeEl.value = prefs.scanMode;
  setInputValue("#topN", prefs.topN);
  setInputValue("#maxPages", prefs.maxPages);
  setInputValue("#maxJobs", prefs.maxJobs);
  setInputValue("#maxDetails", prefs.maxDetails);
  if (prefs.maxCandidates !== undefined) maxCandidatesEl.value = prefs.maxCandidates;
}

function setInputValue(selector, value) {
  if (value === undefined || value === null) return;
  const input = document.querySelector(selector);
  if (input) input.value = value;
}

async function updateResultFilter(event) {
  activeFilter = event.currentTarget.dataset.filter || "all";
  await chrome.storage.local.set({ resultFilter: activeFilter });
  updateFilterButtons();
  renderResults(lastResults, (await chrome.storage.local.get("lastResults")).lastResults?.source);
}

function updateFilterButtons() {
  for (const button of filterButtons) {
    button.classList.toggle("active", button.dataset.filter === activeFilter);
  }
}

function filterResults(results) {
  if (activeFilter === "all") return results;
  return results.filter((item) => normalizeDecision(item.decision) === activeFilter);
}

function renderDiagnosticSummary(trace) {
  if (!diagnosticSummaryEl) return;
  const counts = trace.reduce((acc, item) => {
    const step = item?.step || "unknown";
    acc[step] = (acc[step] || 0) + 1;
    return acc;
  }, {});
  const detailAttempts = trace.filter((item) => item?.step === "click_detail" || item?.step === "open_detail_url");
  const detailOk = detailAttempts.filter((item) => item.ok).length;
  const rankerMessages = trace.filter((item) => item?.step === "ranker").length;
  const quality = [...trace].reverse().find((item) => item?.step === "detail_url_quality") || {};
  diagnosticSummaryEl.innerHTML = `
    <div><span>列表抽取</span><strong>${escapeHtml(counts.extract_list || 0)}</strong></div>
    <div><span>详情补抓</span><strong>${escapeHtml(detailOk)}/${escapeHtml(detailAttempts.length)}</strong></div>
    <div><span>真实详情</span><strong>${escapeHtml(quality.realDetail ?? 0)}/${escapeHtml(quality.total ?? 0)}</strong></div>
    <div><span>列表回退</span><strong>${escapeHtml(quality.listFallback ?? 0)}</strong></div>
    <div><span>排序诊断</span><strong>${escapeHtml(rankerMessages)}</strong></div>
    <div><span>分页/滚动</span><strong>${escapeHtml((counts.extract_list || 1) - 1)}</strong></div>
  `;
}

function renderTracker() {
  if (!trackerListEl) return;
  const visibleJobs = filterSavedJobs(savedJobs);
  trackerCountEl.textContent = String(savedJobs.length);
  savedCountEl.textContent = String(savedJobs.filter((item) => item.status === "saved").length);
  readyCountEl.textContent = String(savedJobs.filter((item) => item.status === "ready").length);
  appliedCountEl.textContent = String(savedJobs.filter((item) => item.status === "applied").length);
  interviewCountEl.textContent = String(savedJobs.filter((item) => item.status === "interview").length);
  dueSoonCountEl.textContent = String(savedJobs.filter((item) => isDueSoon(item) && !isTerminalStatus(item.status)).length);
  overdueCountEl.textContent = String(savedJobs.filter((item) => isOverdue(item) && !isTerminalStatus(item.status)).length);
  if (!visibleJobs.length) {
    trackerListEl.innerHTML = `<div class="empty-state compact">
      <strong>${savedJobs.length ? "当前筛选下暂无岗位" : "岗位库为空"}</strong>
      <span>${savedJobs.length ? "调整搜索或状态筛选" : "在推荐结果里点击“加入岗位库”，用于后续投递跟踪"}</span>
    </div>`;
    return;
  }
  trackerListEl.innerHTML = visibleJobs.slice(0, 40).map((item) => `
    <article class="tracker-item">
      <div>
        <h3>${escapeHtml(item.title)}</h3>
        <p>${escapeHtml([item.company, `${item.score || 0} 分`, decisionLabel(item.decision)].filter(Boolean).join(" · "))}</p>
      </div>
      <select data-key="${escapeAttribute(item.key)}" class="tracker-status">
        <option value="saved" ${item.status === "saved" ? "selected" : ""}>收藏</option>
        <option value="ready" ${item.status === "ready" ? "selected" : ""}>准备投递</option>
        <option value="applied" ${item.status === "applied" ? "selected" : ""}>已投递</option>
        <option value="interview" ${item.status === "interview" ? "selected" : ""}>面试中</option>
        <option value="rejected" ${item.status === "rejected" ? "selected" : ""}>放弃</option>
      </select>
      <div class="tracker-fields">
        <label>标签<input class="tracker-tags" data-key="${escapeAttribute(item.key)}" value="${escapeAttribute(item.tags || "")}" placeholder="AI, 后端, 上海" /></label>
        <label>截止<input class="tracker-deadline" data-key="${escapeAttribute(item.key)}" type="date" value="${escapeAttribute(item.deadline || "")}" /></label>
        <label>优先级
          <select class="tracker-priority" data-key="${escapeAttribute(item.key)}">
            <option value="high" ${item.priority === "high" ? "selected" : ""}>高</option>
            <option value="medium" ${!item.priority || item.priority === "medium" ? "selected" : ""}>中</option>
            <option value="low" ${item.priority === "low" ? "selected" : ""}>低</option>
          </select>
        </label>
        <label>下一步<input class="tracker-next-action" data-key="${escapeAttribute(item.key)}" type="date" value="${escapeAttribute(item.next_action || "")}" /></label>
        <label class="tracker-note-label">备注<textarea class="tracker-note" data-key="${escapeAttribute(item.key)}" rows="2" placeholder="投递注意点、内推人、简历版本">${escapeHtml(item.note || "")}</textarea></label>
      </div>
      <div class="tracker-item-actions">
        <button class="kit-tracker-button" data-key="${escapeAttribute(item.key)}">生成材料包</button>
        <button class="prompt-tracker-button" data-key="${escapeAttribute(item.key)}">复制Prompt</button>
        <button class="open-tracker-button" data-key="${escapeAttribute(item.key)}">打开</button>
        <button class="remove-tracker-button" data-key="${escapeAttribute(item.key)}">移除</button>
      </div>
    </article>
  `).join("");
}

function filterSavedJobs(items) {
  const query = trackerSearch.trim().toLowerCase();
  return items.filter((item) => {
    const statusOk = trackerStatusFilter === "all" || item.status === trackerStatusFilter;
    const haystack = [item.title, item.company, item.tags, item.note, item.priority, item.job_url].join(" ").toLowerCase();
    const queryOk = !query || haystack.includes(query);
    return statusOk && queryOk;
  }).sort(compareTrackedJobs);
}

async function handleTrackerClick(event) {
  const openButton = event.target.closest(".open-tracker-button");
  const removeButton = event.target.closest(".remove-tracker-button");
  const promptButton = event.target.closest(".prompt-tracker-button");
  const kitButton = event.target.closest(".kit-tracker-button");
  if (kitButton) {
    const item = savedJobs.find((entry) => entry.key === kitButton.dataset.key);
    if (item) await generateAndCopyApplicationKit(applicationKitPayloadFromTracker(item));
    return;
  }
  if (promptButton) {
    const item = savedJobs.find((entry) => entry.key === promptButton.dataset.key);
    if (item) {
      await navigator.clipboard.writeText(buildApplicationPrompt(item));
      setStatus("定制投递 Prompt 已复制");
    }
    return;
  }
  if (openButton) {
    const item = savedJobs.find((entry) => entry.key === openButton.dataset.key);
    if (item?.job_url) {
      await chrome.tabs.create({ url: item.job_url, active: true });
    }
    return;
  }
  if (removeButton) {
    savedJobs = savedJobs.filter((entry) => entry.key !== removeButton.dataset.key);
    await persistTracker();
    setStatus("已从岗位库移除");
  }
}

async function handleTrackerStatusChange(event) {
  const select = event.target.closest(".tracker-status");
  if (!select) return;
  const item = savedJobs.find((entry) => entry.key === select.dataset.key);
  if (!item) return;
  item.status = select.value;
  item.updated_at = new Date().toISOString();
  await persistTracker();
}

async function handleTrackerFieldInput(event) {
  const field = event.target.closest(".tracker-tags, .tracker-deadline, .tracker-note, .tracker-priority, .tracker-next-action");
  if (!field) return;
  const item = savedJobs.find((entry) => entry.key === field.dataset.key);
  if (!item) return;
  if (field.classList.contains("tracker-tags")) item.tags = field.value;
  if (field.classList.contains("tracker-deadline")) item.deadline = field.value;
  if (field.classList.contains("tracker-note")) item.note = field.value;
  if (field.classList.contains("tracker-priority")) item.priority = field.value;
  if (field.classList.contains("tracker-next-action")) item.next_action = field.value;
  item.updated_at = new Date().toISOString();
  await chrome.storage.local.set({ savedJobs });
  updateTrackerCountsOnly();
}

async function updateTrackerSearch(event) {
  trackerSearch = event.target.value || "";
  await persistTrackerPrefs();
  renderTracker();
}

async function updateTrackerStatusFilter(event) {
  trackerStatusFilter = event.target.value || "all";
  await persistTrackerPrefs();
  renderTracker();
}

async function updateTrackerSort(event) {
  trackerSort = event.target.value || "priority";
  await persistTrackerPrefs();
  renderTracker();
}

function hydrateTrackerPrefs(prefs) {
  trackerSearch = prefs.search || "";
  trackerStatusFilter = prefs.status || "all";
  trackerSort = prefs.sort || "priority";
  if (trackerSearchEl) trackerSearchEl.value = trackerSearch;
  if (trackerStatusFilterEl) trackerStatusFilterEl.value = trackerStatusFilter;
  if (trackerSortEl) trackerSortEl.value = trackerSort;
}

async function persistTrackerPrefs() {
  await chrome.storage.local.set({ trackerPrefs: { search: trackerSearch, status: trackerStatusFilter, sort: trackerSort } });
}

function updateTrackerCountsOnly() {
  trackerCountEl.textContent = String(savedJobs.length);
  savedCountEl.textContent = String(savedJobs.filter((item) => item.status === "saved").length);
  readyCountEl.textContent = String(savedJobs.filter((item) => item.status === "ready").length);
  appliedCountEl.textContent = String(savedJobs.filter((item) => item.status === "applied").length);
  interviewCountEl.textContent = String(savedJobs.filter((item) => item.status === "interview").length);
  dueSoonCountEl.textContent = String(savedJobs.filter((item) => isDueSoon(item) && !isTerminalStatus(item.status)).length);
  overdueCountEl.textContent = String(savedJobs.filter((item) => isOverdue(item) && !isTerminalStatus(item.status)).length);
}

async function persistTracker() {
  await chrome.storage.local.set({ savedJobs });
  renderTracker();
}

async function clearTracker() {
  if (!savedJobs.length) return setStatus("岗位库已经为空");
  savedJobs = [];
  await persistTracker();
  setStatus("岗位库已清空");
}

function exportTrackerCsv() {
  if (!savedJobs.length) return setStatus("岗位库为空，无法导出");
  const rows = [
    ["title", "company", "score", "decision", "status", "priority", "tags", "deadline", "next_action", "note", "url", "reasons", "risks", "missing_skills", "saved_at"],
    ...savedJobs.map((item) => [
      item.title,
      item.company,
      item.score,
      item.decision,
      item.status,
      item.priority,
      item.tags,
      item.deadline,
      item.next_action,
      item.note,
      item.job_url,
      (item.reasons || []).join(" | "),
      (item.risks || []).join(" | "),
      (item.missing_skills || []).join(" | "),
      item.saved_at
    ])
  ];
  const csv = rows.map((row) => row.map(csvCell).join(",")).join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `ai-job-judge-tracker-${new Date().toISOString().slice(0, 10)}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
  setStatus("岗位库 CSV 已导出");
}

function csvCell(value) {
  return `"${String(value ?? "").replace(/"/g, '""')}"`;
}

function compareTrackedJobs(left, right) {
  if (trackerSort === "score") return Number(right.score || 0) - Number(left.score || 0);
  if (trackerSort === "deadline") return compareDates(left.deadline, right.deadline) || priorityRank(right.priority) - priorityRank(left.priority);
  if (trackerSort === "next_action") return compareDates(left.next_action, right.next_action) || priorityRank(right.priority) - priorityRank(left.priority);
  if (trackerSort === "saved_at") return String(right.saved_at || "").localeCompare(String(left.saved_at || ""));
  return priorityRank(right.priority) - priorityRank(left.priority) || compareDates(left.next_action || left.deadline, right.next_action || right.deadline);
}

function compareDates(left, right) {
  const leftTime = dateTime(left);
  const rightTime = dateTime(right);
  if (leftTime === rightTime) return 0;
  if (leftTime === null) return 1;
  if (rightTime === null) return -1;
  return leftTime - rightTime;
}

function priorityRank(value) {
  return { high: 3, medium: 2, low: 1 }[value || "medium"] || 2;
}

function dateTime(value) {
  if (!value) return null;
  const time = new Date(`${value}T00:00:00`).getTime();
  return Number.isNaN(time) ? null : time;
}

function isDueSoon(item) {
  const target = dateTime(item.next_action || item.deadline);
  if (target === null) return false;
  const today = startOfToday();
  const sevenDays = today + 7 * 24 * 60 * 60 * 1000;
  return target >= today && target <= sevenDays;
}

function isOverdue(item) {
  const target = dateTime(item.next_action || item.deadline);
  return target !== null && target < startOfToday();
}

function startOfToday() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
}

function isTerminalStatus(status) {
  return status === "applied" || status === "rejected";
}

function buildApplicationPrompt(item) {
  return [
    "你是我的求职投递助手。请基于我的简历方向和下面的岗位分析，生成一份定制投递建议。",
    "",
    "请输出：",
    "1. 这个岗位是否值得投递，以及原因。",
    "2. 简历应该突出哪些项目经历和技术关键词。",
    "3. 如果要写一段投递备注/求职信，应该怎么写。",
    "4. 面试准备重点和可能风险。",
    "5. 不要编造我没有的经历。",
    "",
    `岗位：${item.title || ""}`,
    `公司：${item.company || ""}`,
    `匹配分：${item.score || 0}`,
    `推荐等级：${decisionLabel(item.decision)}`,
    `岗位链接：${item.job_url || ""}`,
    `标签：${item.tags || ""}`,
    `备注：${item.note || ""}`,
    `匹配理由：${(item.reasons || []).join("；")}`,
    `风险点：${(item.risks || []).join("；")}`,
    `缺失技能：${(item.missing_skills || []).join("；")}`
  ].join("\n");
}

async function generateAndCopyApplicationKit(payload) {
  setBusy(true);
  setStatus("Claude 正在生成投递材料包...");
  try {
    const kit = await send({ type: "GENERATE_APPLICATION_KIT", payload });
    await navigator.clipboard.writeText(formatApplicationKit(kit, payload));
    setStatus(`投递材料包已复制：${kit.source}`);
  } catch (error) {
    await navigator.clipboard.writeText(buildApplicationPromptFromPayload(payload));
    setStatus(`材料包生成失败，已复制兜底 Prompt：${error.message}`);
  } finally {
    setBusy(false);
  }
}

function applicationKitPayloadFromResult(item) {
  const job = item.job || {};
  return {
    job: normalizeJobForKit({
      ...job,
      title: item.title || job.title,
      company: item.company || job.company,
      detail_url: bestJobUrl(item),
      apply_url: job.apply_url,
      source_url: job.source_url
    }),
    score: Number(item.score || 0),
    decision: normalizeDecision(item.decision),
    reasons: item.reasons || [],
    risks: item.risks || [],
    missing_skills: item.missing_skills || []
  };
}

function applicationKitPayloadFromTracker(item) {
  return {
    job: normalizeJobForKit({
      ...(item.job || {}),
      title: item.title,
      company: item.company,
      detail_url: bestJobUrl(item),
      source_url: item.job?.source_url || item.job_url
    }),
    score: Number(item.score || 0),
    decision: normalizeDecision(item.decision),
    reasons: item.reasons || [],
    risks: item.risks || [],
    missing_skills: item.missing_skills || [],
    notes: [
      item.tags ? `标签：${item.tags}` : "",
      item.note ? `备注：${item.note}` : "",
      item.deadline ? `截止：${item.deadline}` : "",
      item.next_action ? `下一步：${item.next_action}` : ""
    ].filter(Boolean).join("\n")
  };
}

function normalizeJobForKit(job) {
  return {
    id: job.id || null,
    title: job.title || "未命名岗位",
    company: job.company || null,
    department: job.department || null,
    location: job.location || null,
    description: job.description || "",
    requirements: job.requirements || "",
    skills: Array.isArray(job.skills) ? job.skills : [],
    detail_url: job.detail_url || null,
    detail_selector: job.detail_selector || null,
    apply_url: job.apply_url || null,
    source_url: job.source_url || job.detail_url || null,
    confidence: Number(job.confidence || 0.5)
  };
}

function bestJobUrl(item) {
  const job = item?.job || item || {};
  const candidates = [job.detail_url, item?.job_url, job.apply_url, job.source_url];
  return candidates.find(isLikelyDetailUrl) || candidates.find(Boolean) || "";
}

function formatApplicationKit(kit, payload) {
  const job = payload.job || {};
  return [
    `# 投递材料包：${job.title || ""}`,
    "",
    `来源：${kit.source || "unknown"}`,
    `公司：${job.company || ""}`,
    `链接：${job.detail_url || job.apply_url || job.source_url || ""}`,
    "",
    "## 匹配判断",
    kit.fit_summary || "",
    "",
    "## 简历突出点",
    bulletLines(kit.resume_focus),
    "",
    "## 投递备注 / 求职信",
    kit.cover_note || "",
    "",
    "## 面试准备",
    bulletLines(kit.interview_prep),
    "",
    "## 可补充关键词",
    bulletLines(kit.keywords_to_add),
    "",
    "## 风险与补强",
    bulletLines(kit.risk_mitigation),
    "",
    "## 可准备的问题",
    bulletLines(kit.questions_to_prepare),
    "",
    `注意：${kit.no_fabrication_warning || "不要编造简历中没有体现的经历、指标或技能。"}`
  ].join("\n").replace(/\n{3,}/g, "\n\n").trim();
}

function bulletLines(items) {
  if (!items || !items.length) return "- 暂无";
  return items.map((item) => `- ${item}`).join("\n");
}

function buildApplicationPromptFromPayload(payload) {
  const job = payload.job || {};
  return [
    "你是我的求职投递助手。请基于简历方向和下面岗位信息，生成投递材料包。",
    "请输出：匹配判断、简历突出点、投递备注、面试准备、可补充关键词、风险补强、可准备问题。",
    "不要编造我没有的经历、指标或技能。",
    "",
    `岗位：${job.title || ""}`,
    `公司：${job.company || ""}`,
    `链接：${job.detail_url || job.apply_url || job.source_url || ""}`,
    `描述：${job.description || ""}`,
    `要求：${job.requirements || ""}`,
    `分数：${payload.score || 0}`,
    `决策：${decisionLabel(payload.decision)}`,
    `匹配理由：${(payload.reasons || []).join("；")}`,
    `风险点：${(payload.risks || []).join("；")}`,
    `缺失技能：${(payload.missing_skills || []).join("；")}`,
    `备注：${payload.notes || ""}`
  ].join("\n");
}

function decisionLabel(value) {
  if (value === "recommend") return "推荐";
  if (value === "reject") return "不建议";
  return "可考虑";
}

function normalizeDecision(value) {
  const text = String(value || "").toLowerCase();
  if (text.includes("recommend") || text.includes("推荐")) return "recommend";
  if (text.includes("reject") || text.includes("不建议") || text.includes("淘汰")) return "reject";
  return "maybe";
}

function isLikelyDetailUrl(url) {
  if (!url) return false;
  const lower = String(url).toLowerCase();
  const normalized = lower.replace(/#/g, "/");
  if (/\/detail(?:[/?#]|$)/i.test(normalized)) return true;
  if (/\/(?:job|jobs|position|positions)[-_]?detail(?:[/?#]|$)/i.test(normalized)) return true;
  if (/[?&](jobadid|jobid|job_id|positionid|position_id|postid|post_id|recruitjobid)=/i.test(lower)) return true;
  return /\/(?:job|jobs|position|positions)\/[^/?#]{6,}(?:[/?#]|$)/i.test(normalized);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function send(message) {
  return chrome.runtime.sendMessage(message).then((response) => {
    if (response?.ok === false) throw new Error(response.error || "Unknown error");
    return response;
  });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[char]);
}

function escapeAttribute(value) {
  return escapeHtml(value).replace(/`/g, "&#096;");
}

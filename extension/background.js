const API_BASE = "http://127.0.0.1:8765";

chrome.action.onClicked.addListener(async (tab) => {
  await chrome.sidePanel.open({ tabId: tab.id });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sender).then(sendResponse).catch((error) => {
    sendResponse({ ok: false, error: error.message || String(error) });
  });
  return true;
});

async function handleMessage(message) {
  if (message.type === "HEALTH") {
    return api("/health");
  }
  if (message.type === "UPLOAD_RESUME") {
    return uploadResume(message.text);
  }
  if (message.type === "GENERATE_RULES") {
    return api("/resume/rules", { method: "POST", body: { resume_id: message.resumeId, resume_text: message.resumeText } });
  }
  if (message.type === "SCAN_ACTIVE_TAB") {
    return scanActiveTab(message.options || {});
  }
  if (message.type === "OPEN_JOB_DETAIL") {
    return openJobDetail(message.job);
  }
  if (message.type === "GENERATE_APPLICATION_KIT") {
    return generateApplicationKit(message.payload || {});
  }
  throw new Error(`Unknown message: ${message.type}`);
}

async function scanActiveTab(options) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) throw new Error("No active tab");
  const resumeId = options.resumeId || (await chrome.storage.local.get("resumeId")).resumeId;
  const allJobs = [];
  let pageCount = 0;
  let lastUrl = "";
  let stagnantScrolls = 0;
  const maxPages = Number(options.maxPages || 10);
  const maxJobs = Number(options.maxJobs || 100);
  const maxDetails = Number(options.maxDetails || 30);
  const topN = Number(options.topN || 5);
  const maxCandidates = Number(options.maxCandidates || 30);
  const debugTrace = [];
  let detailAttemptsUsed = 0;

  while (pageCount < maxPages && allJobs.length < maxJobs) {
    try {
      const snapshot = await collectSnapshot(tab.id);
      const page = await api("/page/analyze", { method: "POST", body: snapshot });
      if (page.requires_login) {
        return { ok: true, status: "login_required", page, jobs: allJobs };
      }
      const extracted = await api("/jobs/extract", { method: "POST", body: snapshot });
      debugTrace.push({
        step: "extract_list",
        url: snapshot.url,
        siteFamily: page.site_family || "unknown",
        jobs: (extracted.jobs || []).map((job) => job.title)
      });
      allJobs.push(...dedupeJobs(extracted.jobs, allJobs));
      const samePageBudget = Math.max(0, maxDetails - detailAttemptsUsed);
      if (samePageBudget > 0) {
        const samePageCandidates = (extracted.jobs || []).filter(jobNeedsSamePageDetail);
        const selectorDetails = await collectSelectorDetailJobs(tab.id, samePageCandidates, samePageBudget, debugTrace, snapshot.url);
        detailAttemptsUsed += Math.min(samePageCandidates.length, samePageBudget);
        allJobs.push(...dedupeJobs(selectorDetails, allJobs));
      }

      if (allJobs.length >= maxJobs) break;
      const pagination = extracted.pagination || page.pagination || { type: "none" };
      if (pagination.type === "next_button" || pagination.type === "page_numbers" || pagination.type === "load_more") {
        if (!pagination.next_selector) break;
        const clicked = await sendToTab(tab.id, { type: "CLICK_SELECTOR", selector: pagination.next_selector });
        if (!clicked?.ok) break;
        await sleep(1600);
        pageCount += 1;
        const current = await chrome.tabs.get(tab.id);
        if (current.url === lastUrl && pagination.type !== "load_more") break;
        lastUrl = current.url || "";
        continue;
      }
      if (pagination.type === "infinite_scroll" && stagnantScrolls < 3) {
        const before = allJobs.length;
        await sendToTab(tab.id, { type: "SCROLL_FOR_MORE" });
        await sleep(1400);
        stagnantScrolls = allJobs.length === before ? stagnantScrolls + 1 : 0;
        pageCount += 1;
        continue;
      }
      break;
    } catch (error) {
      debugTrace.push({
        step: "scan_step_error",
        pageCount,
        message: error.message || String(error)
      });
      if (allJobs.length) break;
      throw error;
    }
  }

  try {
    const urlDetailBudget = Math.max(0, maxDetails - detailAttemptsUsed);
    const detailJobs = await collectDetailJobs(allJobs.filter(jobNeedsUrlDetail).slice(0, urlDetailBudget), debugTrace);
    const merged = dedupeJobs([...allJobs, ...detailJobs], []);
    debugTrace.push(detailUrlQualityTrace(merged));
    const matched = await api("/jobs/match", { method: "POST", body: { jobs: merged, resume_id: resumeId, max_candidates: maxCandidates } });
    const ranked = await api("/jobs/rank", { method: "POST", body: { matches: matched.matches, resume_id: resumeId, top_n: topN } });
    debugTrace.push({
      step: "result_count_quality",
      extractedJobs: merged.length,
      matchedJobs: matched.matches?.length || 0,
      rankedJobs: ranked.results?.length || 0,
      topN
    });
    await chrome.storage.local.set({ lastResults: ranked, lastMatched: matched, lastJobCount: merged.length, lastDebugTrace: debugTrace });
    return { ok: true, status: "done", totalJobs: merged.length, matched, ranked, debugTrace };
  } catch (error) {
    debugTrace.push({
      step: "rank_pipeline_error",
      message: error.message || String(error),
      extractedJobs: allJobs.length
    });
    await chrome.storage.local.set({ lastDebugTrace: debugTrace, lastJobCount: allJobs.length });
    if (allJobs.length) {
      return { ok: true, status: "partial_error", totalJobs: allJobs.length, jobs: allJobs, debugTrace };
    }
    throw error;
  }
}

async function openJobDetail(job) {
  if (!job) throw new Error("No job payload");
  const url = job.detail_url || job.source_url || job.apply_url;
  if (!url) throw new Error("No job URL");
  const tab = await chrome.tabs.create({ url, active: true });
  await waitForTabComplete(tab.id);
  await sleep(700);
  if (isDetailUrl(url)) {
    return { ok: true, detailUrl: url };
  }
  const actionClicked = await sendToTab(tab.id, { type: "CLICK_JOB_DETAIL_ACTION", title: job.title });
  if (!actionClicked?.ok && job.detail_selector) {
    await sendToTab(tab.id, { type: "CLICK_SELECTOR", selector: job.detail_selector });
  } else if (!actionClicked?.ok && job.title) {
    await sendToTab(tab.id, { type: "CLICK_TEXT", text: job.title });
  }
  return { ok: true };
}

async function collectDetailJobs(jobs, debugTrace) {
  const detailJobs = [];
  const urlJobs = [];
  const seenUrls = new Set();
  for (const job of jobs || []) {
    const url = job.detail_url;
    if (!url || url === job.source_url || !isDetailUrl(url) || seenUrls.has(url)) continue;
    seenUrls.add(url);
    urlJobs.push({ url, job });
  }
  const workers = Array.from({ length: Math.min(4, urlJobs.length) }, async (_, workerIndex) => {
    for (let index = workerIndex; index < urlJobs.length; index += 4) {
      const { url, job } = urlJobs[index];
      const extractedJobs = await collectOneDetailUrl(url, job, debugTrace);
      detailJobs.push(...extractedJobs);
    }
  });
  await Promise.all(workers);
  return detailJobs;
}

async function collectOneDetailUrl(url, job, debugTrace) {
  const detailJobs = [];
  let tabId = null;
    try {
      const tab = await chrome.tabs.create({ url, active: false });
      tabId = tab.id;
      await waitForTabComplete(tabId);
      const snapshot = await collectSnapshot(tabId);
      snapshot.meta = { ...(snapshot.meta || {}), focused_title: job.title };
      const extracted = await api("/jobs/extract", { method: "POST", body: snapshot });
      const focusedJob = (extracted.jobs || []).find((candidate) => sameJobTitle(candidate.title, job.title));
      const jobs = focusedJob ? [focusedJob] : extracted.jobs || [];
      detailJobs.push(...jobs.map((item) => ({ ...item, source_url: job.source_url, detail_url: url })));
      debugTrace?.push({
        step: "open_detail_url",
        title: job.title,
        url,
        ok: true,
        focusedFound: Boolean(focusedJob),
        extracted: jobs.length
      });
      await chrome.tabs.remove(tabId);
      tabId = null;
    } catch (_error) {
      debugTrace?.push({
        step: "open_detail_url",
        title: job.title,
        url,
        ok: false,
        reason: "exception"
      });
      if (tabId !== null) {
        try {
          await chrome.tabs.remove(tabId);
        } catch (_removeError) {
          // Ignore cleanup failures for tabs that the user or browser already closed.
        }
      }
    }
  return detailJobs;
}

async function collectSelectorDetailJobs(tabId, jobs, maxDetails, debugTrace, listUrl) {
  const detailJobs = [];
  const clickableJobs = (jobs || []).filter(jobNeedsSamePageDetail).slice(0, maxDetails);
  if (clickableJobs.length) {
    debugTrace?.push({
      step: "same_page_detail_queue",
      total: clickableJobs.length,
      titles: clickableJobs.slice(0, 8).map((job) => job.title)
    });
  }
  for (const job of clickableJobs) {
    try {
      await ensureTabUrl(tabId, listUrl);
      let clicked = null;
      let clickMethod = "detail_action";
      clicked = await sendToTab(tabId, { type: "CLICK_JOB_DETAIL_ACTION", title: job.title });
      if (!clicked?.ok && job.detail_selector) {
        clickMethod = "selector";
        clicked = await sendToTab(tabId, { type: "CLICK_SELECTOR", selector: job.detail_selector });
      }
      if (!clicked?.ok) {
        clickMethod = "text";
        clicked = await sendToTab(tabId, { type: "CLICK_TEXT", text: job.title });
      }
      if (!clicked?.ok) {
        debugTrace?.push({
          step: "click_detail",
          title: job.title,
          ok: false,
          method: clickMethod,
          reason: clicked?.reason || "click_failed"
        });
        continue;
      }
      await waitForPostClickDetailState(tabId, clicked?.href);
      const currentTab = await chrome.tabs.get(tabId);
      const snapshot = await collectSnapshot(tabId);
      snapshot.meta = { ...(snapshot.meta || {}), focused_title: job.title };
      const extracted = await api("/jobs/extract", { method: "POST", body: snapshot });
      const focusedJob = (extracted.jobs || []).find((candidate) => sameJobTitle(candidate.title, job.title));
      const reachedDetailUrl = isDetailUrl(currentTab.url);
      const clickedDetailUrl = isDetailUrl(clicked?.href) ? clicked.href : null;
      if (focusedJob && reachedDetailUrl) {
        focusedJob.detail_url = currentTab.url;
      } else if (focusedJob && clickedDetailUrl) {
        focusedJob.detail_url = clickedDetailUrl;
      }
      debugTrace?.push({
        step: "click_detail",
        title: job.title,
        ok: true,
        method: clickMethod,
        currentUrl: currentTab.url || "",
        reachedDetailUrl,
        clickedHref: clicked?.href || "",
        clickedText: clicked.clickedText || "",
        focusedFound: Boolean(focusedJob),
        focusedDescriptionLength: focusedJob?.description?.length || 0,
        focusedSkills: focusedJob?.skills || []
      });
      if (focusedJob) {
        detailJobs.push(focusedJob);
      }
    } catch (_error) {
      debugTrace?.push({
        step: "click_detail",
        title: job.title,
        ok: false,
        reason: "exception"
      });
      // Same-page detail panels are best-effort.
    }
  }
  return detailJobs;
}

async function uploadResume(text) {
  const form = new FormData();
  form.append("text", text || "");
  const response = await fetch(`${API_BASE}/resume/upload`, { method: "POST", body: form });
  if (!response.ok) throw new Error(await response.text());
  const payload = await response.json();
  await chrome.storage.local.set({ resumeId: payload.resume_id });
  return payload;
}

async function generateApplicationKit(payload) {
  const resumeId = payload.resume_id || (await chrome.storage.local.get("resumeId")).resumeId;
  return api("/jobs/application-kit", { method: "POST", body: { ...payload, resume_id: resumeId } });
}

async function api(path, options = {}) {
  const init = { method: options.method || "GET", headers: {} };
  if (options.body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(options.body);
  }
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function collectSnapshot(tabId) {
  return sendToTab(tabId, { type: "COLLECT_SNAPSHOT" });
}

async function sendToTab(tabId, message) {
  try {
    return await chrome.tabs.sendMessage(tabId, message);
  } catch (_error) {
    await chrome.scripting.executeScript({ target: { tabId }, files: ["content.js"] });
    return chrome.tabs.sendMessage(tabId, message);
  }
}

async function waitForTabComplete(tabId, timeoutMs = 8000) {
  const tab = await chrome.tabs.get(tabId).catch(() => null);
  if (tab?.status === "complete") {
    await sleep(300);
    return;
  }
  return new Promise((resolve) => {
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      chrome.tabs.onUpdated.removeListener(listener);
      resolve();
    };
    const listener = (updatedTabId, changeInfo) => {
      if (updatedTabId === tabId && changeInfo.status === "complete") {
        setTimeout(finish, 500);
      }
    };
    const timer = setTimeout(finish, timeoutMs);
    chrome.tabs.onUpdated.addListener(listener);
  });
}

async function waitForPostClickDetailState(tabId, clickedHref, timeoutMs = 3200) {
  if (isDetailUrl(clickedHref)) {
    await sleep(700);
    return;
  }
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    await sleep(350);
    const tab = await chrome.tabs.get(tabId).catch(() => null);
    if (isDetailUrl(tab?.url)) return;
    const snapshot = await collectSnapshot(tabId).catch(() => null);
    if (snapshot && hasDetailPanelText(snapshot.visible_text)) return;
  }
}

function dedupeJobs(incoming, existing) {
  const keyFor = (job) => preferredJobUrl(job) || `${job.title}|${job.source_url}`;
  const titleSourceKeyFor = (job) => `${normalizeTitle(job.title)}|${job.source_url || ""}`;
  const existingByKey = new Map(existing.map((job) => [keyFor(job), job]));
  const existingByTitleSource = new Map(existing.map((job) => [titleSourceKeyFor(job), job]));
  const unique = [];
  for (const job of incoming || []) {
    const key = keyFor(job);
    const titleSourceKey = titleSourceKeyFor(job);
    let current = existingByKey.get(key);
    if (current && !sameJobTitle(current.title, job.title)) {
      current = null;
    }
    current = current || existingByTitleSource.get(titleSourceKey);
    if (current) {
      mergeJob(current, job);
      existingByKey.set(keyFor(current), current);
      existingByTitleSource.set(titleSourceKeyFor(current), current);
      continue;
    }
    existingByKey.set(key, job);
    existingByTitleSource.set(titleSourceKey, job);
    unique.push(job);
  }
  return unique;
}

function mergeJob(target, source) {
  if ((source.description || "").length > (target.description || "").length) target.description = source.description;
  if ((source.requirements || "").length > (target.requirements || "").length) target.requirements = source.requirements;
  if (isDetailUrl(source.detail_url) && !isDetailUrl(target.detail_url)) target.detail_url = source.detail_url;
  else if (!target.detail_url && source.detail_url) target.detail_url = source.detail_url;
  if (!target.apply_url && source.apply_url) target.apply_url = source.apply_url;
  if (!target.detail_selector && source.detail_selector) target.detail_selector = source.detail_selector;
  target.skills = Array.from(new Set([...(target.skills || []), ...(source.skills || [])]));
  target.confidence = Math.max(target.confidence || 0, source.confidence || 0);
}

function preferredJobUrl(job) {
  if (isDetailUrl(job?.detail_url)) return job.detail_url;
  if (isDetailUrl(job?.apply_url)) return job.apply_url;
  if (isDetailUrl(job?.source_url)) return job.source_url;
  return job?.detail_url || job?.apply_url || job?.source_url || "";
}

function detailUrlQualityTrace(jobs) {
  const realDetail = (jobs || []).filter((job) => isDetailUrl(preferredJobUrl(job))).length;
  const missing = (jobs || []).filter((job) => !preferredJobUrl(job)).length;
  const listFallback = (jobs || []).filter((job) => preferredJobUrl(job) && !isDetailUrl(preferredJobUrl(job))).length;
  return {
    step: "detail_url_quality",
    total: (jobs || []).length,
    realDetail,
    listFallback,
    missing
  };
}

function jobNeedsDetail(job) {
  const text = `${job.description || ""}\n${job.requirements || ""}`;
  const hasDetailSection = /工作职责|岗位职责|职位描述|任职资格|任职要求|requirements|responsibilities/i.test(text);
  const hasEnoughText = text.length >= 220;
  const hasSkills = Array.isArray(job.skills) && job.skills.length > 0;
  return !(hasDetailSection && hasEnoughText && hasSkills);
}

function hasDetailPanelText(text) {
  return /工作职责|岗位职责|职位描述|任职资格|任职要求|requirements|responsibilities/i.test(String(text || ""));
}

function jobNeedsUrlDetail(job) {
  return jobNeedsDetail(job) && isDetailUrl(job.detail_url);
}

function jobNeedsSamePageDetail(job) {
  return jobNeedsDetail(job) && !isDetailUrl(job.detail_url);
}

async function ensureTabUrl(tabId, url) {
  if (!url) return;
  const tab = await chrome.tabs.get(tabId);
  if ((tab.url || "").split("#")[0] === url.split("#")[0]) return;
  await chrome.tabs.update(tabId, { url });
  await waitForTabComplete(tabId);
  await sleep(700);
}

function isDetailUrl(url) {
  if (!url) return false;
  const raw = String(url);
  const lower = raw.toLowerCase();
  const normalized = lower.replace(/#/g, "/");
  if (/\/detail(?:[/?#]|$)/i.test(normalized)) return true;
  if (/\/(?:job|jobs|position|positions)[-_]?detail(?:[/?#]|$)/i.test(normalized)) return true;
  if (/[?&](jobadid|jobid|job_id|positionid|position_id|postid|post_id|recruitjobid)=/i.test(lower)) return true;
  return /\/(?:job|jobs|position|positions)\/[^/?#]{6,}(?:[/?#]|$)/i.test(normalized);
}

function sameJobTitle(left, right) {
  const leftKey = normalizeTitle(left);
  const rightKey = normalizeTitle(right);
  return leftKey && rightKey && (leftKey.includes(rightKey) || rightKey.includes(leftKey));
}

function normalizeTitle(value) {
  return String(value || "").replace(/\s+/g, "").toLowerCase();
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

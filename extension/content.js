const JOB_JUDGE_MAX_TEXT = 70000;
const JOB_JUDGE_MAX_BLOCKS = 160;
const JOB_JUDGE_MAX_LINKS = 300;

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "COLLECT_SNAPSHOT") {
    sendResponse(collectSnapshot());
    return true;
  }
  if (message.type === "CLICK_SELECTOR") {
    const ok = clickSelector(message.selector);
    sendResponse({ ok });
    return true;
  }
  if (message.type === "CLICK_TEXT") {
    const result = clickText(message.text);
    sendResponse(result);
    return true;
  }
  if (message.type === "CLICK_JOB_DETAIL_ACTION") {
    const result = clickJobDetailAction(message.title);
    sendResponse(result);
    return true;
  }
  if (message.type === "SCROLL_FOR_MORE") {
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
    setTimeout(() => sendResponse({ ok: true, scrollHeight: document.body.scrollHeight }), 900);
    return true;
  }
  return false;
});

function collectSnapshot() {
  const visibleText = compactText(document.body?.innerText || "").slice(0, JOB_JUDGE_MAX_TEXT);
  const links = Array.from(document.querySelectorAll("a[href]"))
    .filter(isVisible)
    .slice(0, JOB_JUDGE_MAX_LINKS)
    .map((node) => ({
      text: compactText(node.innerText || node.getAttribute("aria-label") || ""),
      href: inferredHrefFor(node) || node.href,
      selector: selectorFor(node),
      attrs: collectInterestingAttrs(node)
    }));
  const buttons = clickableCandidates()
    .filter(isVisible)
    .slice(0, JOB_JUDGE_MAX_LINKS)
    .map((node) => ({
      text: compactText(node.innerText || node.value || node.getAttribute("aria-label") || node.title || ""),
      selector: selectorFor(node),
      tag: node.tagName.toLowerCase(),
      role: node.getAttribute("role"),
      href: inferredHrefFor(node),
      attrs: collectInterestingAttrs(node)
    }));
  return {
    url: location.href,
    title: document.title || "",
    visible_text: visibleText,
    links,
    buttons,
    blocks: collectBlocks(),
    meta: {
      innerHeight: window.innerHeight,
      scrollHeight: document.body?.scrollHeight || 0,
      timestamp: Date.now()
    }
  };
}

function collectBlocks() {
  const selectors = [
    "article",
    "li",
    "tr",
    "[onclick]",
    "[tabindex]",
    "[role='option']",
    "[role='listitem']",
    "[data-job-id]",
    "[data-position-id]",
    "[data-ats-job-id]",
    "[data-id]",
    "[class*='item']",
    "[class*='name']",
    "[class*='job']",
    "[class*='Job']",
    "[class*='职位']",
    "[class*='岗位']",
    "[class*='position']",
    "[class*='Position']",
    "[class*='career']",
    "[class*='Career']",
    "[class*='recruit']",
    "[class*='Recruit']",
    "[class*='list']",
    "[class*='List']",
    ".card",
    "section",
    "main > div"
  ];
  const nodes = Array.from(document.querySelectorAll(selectors.join(","))).filter(isVisible);
  const blocks = [];
  const seen = new Set();
  for (const node of nodes) {
    const text = compactText(node.innerText || "");
    if (text.length < 12 || text.length > 5000 || seen.has(text.slice(0, 240))) continue;
    seen.add(text.slice(0, 240));
    const links = detailLinkCandidatesIn(node).slice(0, 16);
    blocks.push({ text, selector: selectorFor(node), links });
    if (blocks.length >= JOB_JUDGE_MAX_BLOCKS) break;
  }
  if (!blocks.length) {
    blocks.push({ text: compactText(document.body?.innerText || "").slice(0, 5000), selector: "body", links: [] });
  }
  return blocks;
}

function clickSelector(selector) {
  if (!selector) return false;
  const node = document.querySelector(selector);
  if (!node) return false;
  node.scrollIntoView({ block: "center", inline: "center" });
  node.click();
  return true;
}

function clickText(text) {
  const targetText = normalizeForMatch(text);
  if (!targetText) return { ok: false, reason: "empty_text" };
  const candidates = Array.from(document.querySelectorAll("a, button, [role='button'], [role='option'], [role='listitem'], [onclick], [tabindex], li, tr, div, span"))
    .filter(isVisible)
    .map((node) => ({ node, text: normalizeForMatch(node.innerText || node.textContent || node.getAttribute("aria-label") || "") }))
    .filter((item) => item.text && (item.text === targetText || item.text.includes(targetText) || targetText.includes(item.text)))
    .sort((a, b) => scoreClickCandidate(a.node, a.text, targetText) - scoreClickCandidate(b.node, b.text, targetText));
  if (!candidates.length) return { ok: false, reason: "text_not_found" };
  const node = closestClickable(candidates[0].node);
  node.scrollIntoView({ block: "center", inline: "center" });
  node.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
  node.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
  node.click();
  node.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
  return {
    ok: true,
    selector: selectorFor(node),
    clickedText: compactText(node.innerText || node.textContent || ""),
    href: inferredHrefFor(node)
  };
}

function clickJobDetailAction(title) {
  const titleKey = normalizeForMatch(title);
  if (!titleKey) return { ok: false, reason: "empty_title" };
  const block = findBestJobBlock(titleKey);
  if (!block) return { ok: false, reason: "job_block_not_found" };

  const action = findDetailActionInBlock(block);
  if (!action) {
    return { ok: false, reason: "detail_action_not_found", blockText: compactText(block.innerText || "").slice(0, 200) };
  }

  action.scrollIntoView({ block: "center", inline: "center" });
  action.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
  action.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
  action.click();
  action.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
  return {
    ok: true,
    selector: selectorFor(action),
    method: "job_detail_action",
    clickedText: compactText(action.innerText || action.textContent || action.getAttribute("aria-label") || ""),
    href: inferredHrefFor(action)
  };
}

function findBestJobBlock(titleKey) {
  const candidates = Array.from(document.querySelectorAll("article, li, tr, [class*='job'], [class*='Job'], [class*='position'], [class*='Position'], [class*='item'], [class*='card'], [data-job-id], [data-position-id], div"))
    .filter(isVisible)
    .map((node) => ({ node, text: normalizeForMatch(node.innerText || node.textContent || "") }))
    .filter((item) => item.text && item.text.includes(titleKey))
    .sort((a, b) => scoreJobBlock(a.node, a.text, titleKey) - scoreJobBlock(b.node, b.text, titleKey));
  return candidates[0]?.node || null;
}

function findDetailActionInBlock(block) {
  const actionWords = ["查看详情", "详情", "职位详情", "岗位详情", "申请", "投递", "立即投递", "apply", "detail"];
  const nodes = Array.from(block.querySelectorAll("a, button, [role='button'], [onclick], [tabindex], span, div"))
    .filter(isVisible)
    .map((node) => ({
      node,
      text: compactText(node.innerText || node.textContent || node.getAttribute("aria-label") || node.title || ""),
      href: inferredHrefFor(node) || ""
    }))
    .filter((item) => {
      const haystack = `${item.text} ${item.href}`.toLowerCase();
      return actionWords.some((word) => haystack.includes(word.toLowerCase()));
    })
    .sort((a, b) => scoreDetailAction(a.node, a.text, a.href) - scoreDetailAction(b.node, b.text, b.href));
  if (!nodes.length) return null;
  return closestClickable(nodes[0].node);
}

function scoreJobBlock(node, text, titleKey) {
  let score = Math.abs(text.length - titleKey.length);
  const tag = node.tagName.toLowerCase();
  if (tag === "li" || tag === "tr" || tag === "article") score -= 50;
  if ((node.className || "").toString().match(/job|position|item|card|职位|岗位/i)) score -= 30;
  score += node.querySelectorAll("*").length;
  return score;
}

function scoreDetailAction(node, text, href) {
  let score = 0;
  const tag = node.tagName.toLowerCase();
  const compact = normalizeForMatch(text);
  if (compact === "查看详情" || compact === "详情" || compact === "职位详情" || compact === "岗位详情") score -= 100;
  if (/detail|jobAdId|position|job/i.test(href || "")) score -= 80;
  if (tag === "a") score -= 30;
  if (tag === "button") score -= 20;
  score += compact.length;
  return score;
}

function detailLinkCandidatesIn(root) {
  const nodes = Array.from(root.querySelectorAll("a[href], button, [role='button'], [onclick], [tabindex], span, div"))
    .filter(isVisible);
  const candidates = [];
  const seen = new Set();
  for (const node of nodes) {
    const href = inferredHrefFor(node);
    const text = compactText(node.innerText || node.textContent || node.getAttribute("aria-label") || node.title || "");
    if (!href && !looksLikeDetailAction(text)) continue;
    const key = `${text}|${href || ""}|${selectorFor(node) || ""}`;
    if (seen.has(key)) continue;
    seen.add(key);
    if (href || looksLikeDetailAction(text)) {
      candidates.push({
        text,
        href: href || location.href,
        selector: selectorFor(node),
        attrs: collectInterestingAttrs(node)
      });
    }
  }
  return candidates;
}

function clickableCandidates() {
  const selector = [
    "button",
    "[role='button']",
    "[role='option']",
    "[role='listitem']",
    "input[type='button']",
    "input[type='submit']",
    "a[href]",
    "[onclick]",
    "[tabindex]",
    "[data-job-id]",
    "[data-job-ad-id]",
    "[data-jobadid]",
    "[data-position-id]",
    "[data-ats-job-id]",
    "[data-recruit-job-id]",
    "[data-url]",
    "[data-href]",
    "[data-link]",
    "[data-to]",
    "[class*='job']",
    "[class*='Job']",
    "[class*='position']",
    "[class*='Position']",
    "[class*='职位']",
    "[class*='岗位']",
    "[class*='item']"
  ].join(",");
  const nodes = Array.from(document.querySelectorAll(selector));
  const byNode = new Set();
  return nodes.filter((node) => {
    if (byNode.has(node)) return false;
    byNode.add(node);
    return true;
  });
}

function inferredHrefFor(node) {
  if (!node) return null;
  const direct = absoluteUrl(node.href);
  if (direct) return direct;
  const anchor = node.closest?.("a[href]");
  if (anchor?.href) return absoluteUrl(anchor.href);

  let current = node;
  let depth = 0;
  while (current && current !== document.body && depth < 6) {
    const fromAttrs = hrefFromAttributes(current);
    if (fromAttrs) return fromAttrs;
    const fromIds = hrefFromDataIds(current);
    if (fromIds) return fromIds;
    current = current.parentElement;
    depth += 1;
  }
  return null;
}

function hrefFromAttributes(node) {
  for (const attr of Array.from(node.attributes || [])) {
    const name = attr.name.toLowerCase();
    const value = attr.value || "";
    if (!value) continue;
    if (/href|url|link|route|path|to|onclick/.test(name)) {
      const url = extractUrlFromText(value) || absoluteUrl(value);
      if (url) return url;
    }
    if (/jobadid|job-ad-id|job_id|jobid|positionid|position-id|recruitjobid|recruit-job-id/.test(name) || (location.hostname.includes("mokahr.com") && name === "data-id")) {
      const url = synthesizeDetailUrl(name, value);
      if (url) return url;
    }
  }
  return null;
}

function hrefFromDataIds(node) {
  const dataset = node.dataset || {};
  for (const [key, value] of Object.entries(dataset)) {
    const lower = key.toLowerCase();
    if (/jobadid|jobid|job_id|positionid|recruitjobid|atsjobid/.test(lower) || (location.hostname.includes("mokahr.com") && lower === "id")) {
      const url = synthesizeDetailUrl(lower, value);
      if (url) return url;
    }
    if (/url|href|link|route|path|to/.test(lower)) {
      const url = extractUrlFromText(value) || absoluteUrl(value);
      if (url) return url;
    }
  }
  return null;
}

function extractUrlFromText(value) {
  const text = String(value || "");
  const full = text.match(/https?:\/\/[^'")\s<>]+/i);
  if (full) return absoluteUrl(full[0]);
  const path = text.match(/\/[^'")\s<>]*(?:detail|jobAdId|jobId|job_id|positionId|position_id|recruitJobId)[^'")\s<>]*/i);
  if (path) return absoluteUrl(path[0]);
  const query = text.match(/(?:jobAdId|jobId|job_id|positionId|position_id|recruitJobId)=([A-Za-z0-9_-]{8,})/i);
  if (query) return synthesizeDetailUrl(query[0].split("=")[0], query[1]);
  return null;
}

function synthesizeDetailUrl(name, value) {
  const id = String(value || "").trim();
  if (!id || id.length < 6) return null;
  const lowerName = String(name || "").toLowerCase();
  if (location.hostname.includes("zhiye.com")) {
    const tenant = location.pathname.split("/").filter(Boolean)[0] || "5";
    const param = lowerName.includes("position") ? "positionId" : lowerName.includes("recruit") ? "recruitJobId" : "jobAdId";
    return `${location.origin}/${tenant}/detail?${param}=${encodeURIComponent(id)}`;
  }
  if (location.hostname.includes("mokahr.com")) {
    const base = `${location.origin}${location.pathname}`;
    return `${base}#/job/${encodeURIComponent(id)}`;
  }
  if (lowerName.includes("position")) return absoluteUrl(`/position/${encodeURIComponent(id)}`);
  if (lowerName.includes("job")) return absoluteUrl(`/job/${encodeURIComponent(id)}`);
  return null;
}

function absoluteUrl(value) {
  const raw = String(value || "").trim();
  if (!raw || raw === "#" || raw.startsWith("javascript:")) return null;
  try {
    return new URL(raw, location.href).href;
  } catch (_error) {
    return null;
  }
}

function collectInterestingAttrs(node) {
  const attrs = {};
  for (const attr of Array.from(node?.attributes || [])) {
    const name = attr.name;
    if (!/href|url|link|route|path|to|onclick|job|position|post|recruit|data-|id/i.test(name)) continue;
    attrs[name] = String(attr.value || "").slice(0, 300);
    if (Object.keys(attrs).length >= 16) break;
  }
  return attrs;
}

function looksLikeDetailAction(text) {
  const value = compactText(text).toLowerCase();
  return /查看详情|职位详情|岗位详情|详情|detail|apply|申请|投递/.test(value);
}

function closestClickable(node) {
  let current = node;
  while (current && current !== document.body) {
    const style = window.getComputedStyle(current);
    const tag = current.tagName.toLowerCase();
    if (
      tag === "a" ||
      tag === "button" ||
      current.getAttribute("role") === "button" ||
      current.getAttribute("role") === "option" ||
      current.getAttribute("role") === "listitem" ||
      current.hasAttribute("onclick") ||
      current.hasAttribute("tabindex") ||
      style.cursor === "pointer"
    ) {
      return current;
    }
    current = current.parentElement;
  }
  return node;
}

function scoreClickCandidate(node, nodeText, targetText) {
  let score = Math.abs(nodeText.length - targetText.length);
  const tag = node.tagName.toLowerCase();
  if (nodeText === targetText) score -= 100;
  if (tag === "a" || tag === "button") score -= 30;
  if (node.hasAttribute("onclick") || node.hasAttribute("tabindex")) score -= 20;
  if (window.getComputedStyle(node).cursor === "pointer") score -= 20;
  score += node.querySelectorAll("*").length * 2;
  return score;
}

function compactText(value) {
  return String(value || "").replace(/\s+\n/g, "\n").replace(/\n\s+/g, "\n").replace(/[ \t]{2,}/g, " ").trim();
}

function normalizeForMatch(value) {
  return compactText(value).replace(/\s+/g, "").toLowerCase();
}

function isVisible(node) {
  const rect = node.getBoundingClientRect();
  const style = window.getComputedStyle(node);
  return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
}

function selectorFor(node) {
  if (!node || node.nodeType !== Node.ELEMENT_NODE) return null;
  if (node.id) return `#${CSS.escape(node.id)}`;
  const parts = [];
  let current = node;
  while (current && current.nodeType === Node.ELEMENT_NODE && parts.length < 5) {
    let part = current.tagName.toLowerCase();
    const classNames = Array.from(current.classList || []).filter(Boolean).slice(0, 2);
    if (classNames.length) part += "." + classNames.map((name) => CSS.escape(name)).join(".");
    const parent = current.parentElement;
    if (parent) {
      const siblings = Array.from(parent.children).filter((child) => child.tagName === current.tagName);
      if (siblings.length > 1) part += `:nth-of-type(${siblings.indexOf(current) + 1})`;
    }
    parts.unshift(part);
    current = parent;
  }
  return parts.join(" > ");
}

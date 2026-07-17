"use strict";

const API_PREFIX = "/api/v1";

const state = {
  recordsById: new Map(),
  selectedIds: new Set(),
  mode: "search",
  busy: false,
};

const elements = {
  thread: document.querySelector("#thread"),
  composer: document.querySelector("#composer"),
  prompt: document.querySelector("#prompt"),
  send: document.querySelector("#send"),
  language: document.querySelector("#language"),
  modeSearch: document.querySelector("#mode-search"),
  modeAsk: document.querySelector("#mode-ask"),
  tray: document.querySelector("#evidence-tray"),
  trayChips: document.querySelector("#tray-chips"),
  trayClear: document.querySelector("#tray-clear"),
};

const answerExamples = {
  success: "What do the selected synthetic records demonstrate?",
  abstained: "Who was objectively the most influential Belgian artist?",
  unavailable: "simulate-generation-unavailable",
};

const searchPlaceholder =
  "Search the synthetic collection — try poster, Bruxelles, or haven";

const mediaGlyphs = {
  image: "▣",
  text: "¶",
  sound: "♬",
  video: "▶",
  "3d": "◆",
};

const prefersReducedMotion = window.matchMedia(
  "(prefers-reduced-motion: reduce)",
).matches;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function humanize(value) {
  return value.replaceAll("_", " ");
}

function scrollToEnd() {
  window.scrollTo({
    top: document.body.scrollHeight,
    behavior: prefersReducedMotion ? "auto" : "smooth",
  });
}

function appendUserMessage(kind, text) {
  const message = element("article", "message from-user");
  const body = element("div", "message-body");
  const meta = element(
    "span",
    "meta-tag",
    `${kind} · ${elements.language.value.toUpperCase()}`,
  );
  const bubble = element("div", "user-bubble");
  bubble.append(element("p", "", text));
  body.append(meta, bubble);
  message.append(body);
  elements.thread.append(message);
  scrollToEnd();
}

function appendAssistantMessage(...nodes) {
  const message = element("article", "message from-assistant");
  const avatar = element("span", "avatar", "✦");
  avatar.setAttribute("aria-hidden", "true");
  const body = element("div", "message-body");
  body.append(...nodes);
  message.append(avatar, body);
  elements.thread.append(message);
  scrollToEnd();
  return message;
}

function showTyping() {
  const indicator = element("div", "typing");
  indicator.setAttribute("aria-label", "The assistant is working");
  indicator.append(element("i"), element("i"), element("i"));
  return appendAssistantMessage(indicator);
}

function statePanel(kind, symbol, title, detail) {
  const panel = element("div", `state-panel state-${kind}`);
  const mark = element("span", "", symbol);
  mark.setAttribute("aria-hidden", "true");
  const copy = element("div");
  copy.append(element("strong", "", title));
  if (detail) copy.append(element("p", "", detail));
  panel.append(mark, copy);
  return panel;
}

function limitationList(limitations) {
  if (!limitations.length) return null;
  const list = element("ul", "limitation-list");
  limitations.forEach((limitation) => list.append(element("li", "", limitation)));
  return list;
}

function titleFor(record) {
  const language = elements.language.value;
  return (
    record.titles.find((title) => title.language === language) || record.titles[0]
  );
}

function descriptionFor(record) {
  const language = elements.language.value;
  return (
    record.descriptions.find(
      (description) => description.language === language,
    ) || record.descriptions[0]
  );
}

function setBusy(busy) {
  state.busy = busy;
  elements.send.disabled = busy;
  elements.composer.setAttribute("aria-busy", String(busy));
}

function setMode(mode) {
  state.mode = mode;
  const searchActive = mode === "search";
  elements.modeSearch.classList.toggle("is-active", searchActive);
  elements.modeSearch.setAttribute("aria-pressed", String(searchActive));
  elements.modeAsk.classList.toggle("is-active", !searchActive);
  elements.modeAsk.setAttribute("aria-pressed", String(!searchActive));
  elements.prompt.placeholder = searchActive
    ? searchPlaceholder
    : `Ask about the ${state.selectedIds.size} selected record${state.selectedIds.size === 1 ? "" : "s"}`;
}

function toggleSelection(evidenceId) {
  const wasEmpty = state.selectedIds.size === 0;
  if (state.selectedIds.has(evidenceId)) state.selectedIds.delete(evidenceId);
  else state.selectedIds.add(evidenceId);

  if (wasEmpty && state.selectedIds.size === 1) setMode("ask");
  if (state.selectedIds.size === 0) setMode("search");
  syncSelectionUI();
}

function clearSelection() {
  state.selectedIds.clear();
  setMode("search");
  syncSelectionUI();
}

function syncSelectionUI() {
  const count = state.selectedIds.size;

  document.querySelectorAll(".evidence-card").forEach((card) => {
    const selected = state.selectedIds.has(card.dataset.evidenceId);
    card.classList.toggle("is-selected", selected);
    const toggle = card.querySelector(".select-toggle");
    toggle.setAttribute("aria-pressed", String(selected));
    toggle.textContent = selected ? "✓" : "";
  });

  elements.trayChips.replaceChildren();
  state.selectedIds.forEach((evidenceId) => {
    const record = state.recordsById.get(evidenceId);
    const chip = element("span", "tray-chip");
    chip.append(
      element("span", "tray-chip-title", record ? titleFor(record).text : evidenceId),
    );
    const remove = element("button", "tray-remove", "✕");
    remove.type = "button";
    remove.setAttribute("aria-label", `Remove ${evidenceId} from selected evidence`);
    remove.addEventListener("click", () => toggleSelection(evidenceId));
    chip.append(remove);
    elements.trayChips.append(chip);
  });
  elements.tray.hidden = count === 0;

  elements.modeAsk.disabled = count === 0;
  document.querySelectorAll(".answer-chip").forEach((button) => {
    button.disabled = count === 0;
  });

  if (state.mode === "ask") setMode("ask");
}

function renderEvidenceCard(record) {
  const card = element("article", "evidence-card");
  card.dataset.evidenceId = record.evidence_id;

  const toggle = element("button", "select-toggle");
  toggle.type = "button";
  toggle.setAttribute("aria-pressed", "false");
  toggle.setAttribute(
    "aria-label",
    `Select ${titleFor(record).text} as answer evidence`,
  );

  const badges = element("div", "badge-row");
  badges.append(
    element("span", "synthetic-badge", "Synthetic record"),
    element(
      "span",
      "media-badge",
      `${mediaGlyphs[record.media_type] || "◈"} ${record.media_type}`,
    ),
  );

  const title = element("h3", "", titleFor(record).text);

  const meta = element("div", "record-meta");
  if (record.object_type) meta.append(element("span", "", record.object_type));
  if (record.date_display) meta.append(element("span", "", record.date_display));
  meta.append(element("span", "", record.evidence_id));

  const provenance = element("details", "provenance");
  provenance.append(element("summary", "", "Provenance & rights"));
  const grid = element("div", "provenance-grid");

  const providers = element("div", "detail-box");
  providers.append(element("strong", "", "Providers"));
  record.providers.forEach((provider) => {
    providers.append(
      element("p", "", `${provider.name} · ${humanize(provider.role)}`),
    );
  });

  const rights = element("div", "detail-box");
  rights.append(element("strong", "", "Recorded rights"));
  record.rights.forEach((statement) => {
    rights.append(
      element("p", "", `${humanize(statement.scope)}: ${statement.label}`),
    );
  });

  grid.append(providers, rights);
  provenance.append(grid);

  const links = element("div", "link-list");
  record.source_links.forEach((source) => {
    const link = element("a", "", `${source.label} ↗`);
    link.href = source.url;
    link.target = "_blank";
    link.rel = "noreferrer";
    links.append(link);
  });

  card.append(toggle, badges, title);
  const description = descriptionFor(record);
  if (description) card.append(element("p", "description", description.text));
  card.append(meta, provenance, links);

  const activate = (event) => {
    if (event.target.closest("a, summary, .provenance")) return;
    toggleSelection(record.evidence_id);
  };
  toggle.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleSelection(record.evidence_id);
  });
  card.addEventListener("click", activate);

  return card;
}

function renderSearchResponse(payload) {
  if (payload.outcome === "empty") {
    appendAssistantMessage(
      statePanel(
        "empty",
        "◌",
        "No synthetic records matched",
        "This is a valid empty result, not an operational error. Try poster, Bruxelles, or haven.",
      ),
    );
    return;
  }

  payload.results.forEach((record) => {
    state.recordsById.set(record.evidence_id, record);
  });

  const summary = element("p", "result-summary");
  summary.append(
    element(
      "strong",
      "",
      `${payload.total} synthetic record${payload.total === 1 ? "" : "s"} found`,
    ),
    document.createTextNode(" — select evidence, then switch to Ask."),
  );

  const grid = element("div", "evidence-grid");
  payload.results.forEach((record) => grid.append(renderEvidenceCard(record)));

  const nodes = [summary, grid];
  const limitations = limitationList(payload.limitations);
  if (limitations) nodes.push(limitations);

  appendAssistantMessage(...nodes);
  syncSelectionUI();
}

function renderAnswerResponse(payload) {
  if (payload.outcome === "answered") {
    const panel = element("div", "answer-panel");
    panel.append(
      element("h3", "", "Grounded answer"),
      element("p", "answer-text", payload.answer_text),
    );
    const citations = element("div", "citation-list");
    payload.citations.forEach((citation) => {
      citations.append(element("span", "citation-item", citation.label));
    });
    panel.append(citations);
    const limitations = limitationList(payload.limitations);
    if (limitations) panel.append(limitations);
    appendAssistantMessage(panel);
    return;
  }

  const nodes = [];
  if (payload.outcome === "abstained") {
    nodes.push(
      statePanel(
        "abstained",
        "◈",
        "The assistant abstained",
        `Reason: ${humanize(payload.reason)}. The selected evidence does not support the requested conclusion, and your search results remain visible above.`,
      ),
    );
  } else {
    nodes.push(
      statePanel(
        "unavailable",
        "◇",
        "Generation unavailable",
        "The answer component cannot run right now; the selected records, providers, links, and rights above remain fully usable.",
      ),
    );
  }
  const limitations = limitationList(payload.limitations);
  if (limitations) nodes.push(limitations);
  appendAssistantMessage(...nodes);
}

async function readApiResponse(response) {
  const payload = await response.json();
  if (!response.ok) {
    const message =
      payload.error?.message || "The API returned an unexpected error.";
    throw new Error(message);
  }
  return payload;
}

async function submitSearch(query) {
  appendUserMessage("Search", query);
  const typing = showTyping();
  setBusy(true);

  try {
    const response = await fetch(`${API_PREFIX}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        language: elements.language.value,
        limit: 10,
      }),
    });
    const payload = await readApiResponse(response);
    typing.remove();
    renderSearchResponse(payload);
  } catch (error) {
    typing.remove();
    appendAssistantMessage(
      statePanel("error", "✕", "Search could not be completed", error.message),
    );
  } finally {
    setBusy(false);
    scrollToEnd();
  }
}

async function submitAsk(question) {
  appendUserMessage("Ask", question);
  const typing = showTyping();
  setBusy(true);

  try {
    const response = await fetch(`${API_PREFIX}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        language: elements.language.value,
        evidence_ids: Array.from(state.selectedIds),
      }),
    });
    const payload = await readApiResponse(response);
    typing.remove();
    renderAnswerResponse(payload);
  } catch (error) {
    typing.remove();
    appendAssistantMessage(
      statePanel("error", "✕", "Answer could not be completed", error.message),
    );
  } finally {
    setBusy(false);
    scrollToEnd();
  }
}

elements.composer.addEventListener("submit", (event) => {
  event.preventDefault();
  if (state.busy) return;
  const text = elements.prompt.value.trim();
  if (!text) return;
  elements.prompt.value = "";

  if (state.mode === "ask" && state.selectedIds.size > 0) submitAsk(text);
  else submitSearch(text);
});

elements.modeSearch.addEventListener("click", () => setMode("search"));
elements.modeAsk.addEventListener("click", () => {
  if (!elements.modeAsk.disabled) setMode("ask");
});
elements.trayClear.addEventListener("click", clearSelection);

document.querySelectorAll(".example-chip").forEach((button) => {
  button.addEventListener("click", () => {
    if (state.busy) return;
    setMode("search");
    elements.prompt.value = button.dataset.query;
    elements.composer.requestSubmit();
  });
});

document.querySelectorAll(".answer-chip").forEach((button) => {
  button.addEventListener("click", () => {
    if (state.busy || button.disabled) return;
    setMode("ask");
    elements.prompt.value = answerExamples[button.dataset.answer];
    elements.composer.requestSubmit();
  });
});

elements.prompt.focus();

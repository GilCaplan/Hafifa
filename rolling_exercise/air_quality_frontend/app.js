const UPLOAD_URL = "/air-quality/upload";
const LOGS_URL = "/logs";
const TABLES_URL = "/tables";
const OPENAPI_URL = "/openapi.json";
// Endpoints that exist only to feed this page; the Endpoints card lists everything else.
const FRONTEND_ONLY_PATHS = ["/logs", "/tables/{table}"];
const CALL_LOG_LIMIT = 100;
const REQUEST_ID_HEADER = "X-Request-ID";
const LOG_LIMIT = 300;
const REFRESH_INTERVAL_MS = 3000;
const FILTER_DEBOUNCE_MS = 300;
const ERROR_LEVELS = ["ERROR", "CRITICAL"];
const DEFAULT_SORT = { column: "date", descending: true };
const COLUMN_LABELS = {
  id: "ID",
  date: "Date",
  city: "City",
  pm25: "PM2.5",
  no2: "NO2",
  co2: "CO2",
  aqi: "AQI",
  aqi_level: "Level",
};
const NUMERIC_COLUMNS = ["id", "pm25", "no2", "co2", "aqi"];
const AQI_LEVEL_COLORS = {
  Good: "var(--aqi-good)",
  Moderate: "var(--aqi-moderate)",
  "Unhealthy for Sensitive Groups": "var(--aqi-sensitive)",
  Unhealthy: "var(--aqi-unhealthy)",
  "Very Unhealthy": "var(--aqi-very-unhealthy)",
  Hazardous: "var(--aqi-hazardous)",
};

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const results = document.getElementById("results");
const resultsHead = document.getElementById("results-head");
const logList = document.getElementById("log-list");
const logCounts = document.getElementById("log-counts");
const logSearch = document.getElementById("log-search");
const levelFilter = document.getElementById("level-filter");
const autoRefresh = document.getElementById("auto-refresh");
const refreshButton = document.getElementById("refresh-logs");
const apiStatus = document.getElementById("api-status");
const tableTabs = document.getElementById("table-tabs");
const tableFilters = document.getElementById("table-filters");
const dataTable = document.getElementById("data-table");
const tableRange = document.getElementById("table-range");
const prevPage = document.getElementById("prev-page");
const nextPage = document.getElementById("next-page");
const endpointList = document.getElementById("endpoint-list");

const state = { level: "ALL", search: "", entries: [], lastSignature: "" };
const tableState = { table: "readings", sort: { ...DEFAULT_SORT }, offset: 0, limit: 25, total: 0, requestId: 0 };

// Builds an element. Text always goes through textContent, so filenames and log messages can't inject HTML.
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

/* ---------- Upload ---------- */

dropzone.addEventListener("click", (event) => {
  event.preventDefault();
  fileInput.click();
});
dropzone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    fileInput.click();
  }
});
fileInput.addEventListener("change", () => {
  uploadFiles(fileInput.files);
  fileInput.value = "";
});

["dragenter", "dragover"].forEach((type) =>
  dropzone.addEventListener(type, (event) => {
    event.preventDefault();
    dropzone.classList.add("dragging");
  })
);
["dragleave", "drop"].forEach((type) =>
  dropzone.addEventListener(type, (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragging");
  })
);
dropzone.addEventListener("drop", (event) => uploadFiles(event.dataTransfer.files));

// Stop the browser from opening a file dropped outside the dropzone.
["dragover", "drop"].forEach((type) => window.addEventListener(type, (event) => event.preventDefault()));

document.getElementById("clear-results").addEventListener("click", () => {
  results.replaceChildren();
  resultsHead.hidden = true;
});

async function uploadFiles(fileList) {
  for (const file of Array.from(fileList)) {
    await uploadFile(file);
  }
}

async function uploadFile(file) {
  const card = renderPendingResult(file.name);
  const body = new FormData();
  body.append("file", file);
  let requestId = null;

  try {
    const response = await fetch(UPLOAD_URL, { method: "POST", body });
    requestId = response.headers.get(REQUEST_ID_HEADER);
    const data = await response.json().catch(() => ({}));
    if (response.ok) {
      renderSuccessResult(card, data);
    } else {
      renderErrorResult(card, `${response.status} ${response.statusText}`, formatDetail(data.detail));
    }
  } catch {
    renderErrorResult(card, "Network error", "Could not reach the API. Is the server running?");
  }
  card.append(renderCallLogs(await logsForRequest(requestId)));
  loadLogs();
  loadTable();
}

// FastAPI sends `detail` as a string for HTTPException, and as a list for request validation errors.
function formatDetail(detail) {
  if (!detail) return "The server returned an error without details.";
  if (Array.isArray(detail)) return detail.map((item) => `${item.loc?.join(".") ?? ""}: ${item.msg}`).join("\n");
  return String(detail);
}

function renderPendingResult(filename) {
  resultsHead.hidden = false;
  const card = el("li", "result");
  const top = el("div", "result-top");
  top.append(el("span", "result-name", filename), el("span", "badge pending", "Uploading…"));
  card.append(top);
  results.prepend(card);
  return card;
}

function setBadge(card, className, text) {
  const badge = card.querySelector(".badge");
  badge.className = `badge ${className}`;
  badge.textContent = text;
}

function renderSuccessResult(card, data) {
  const skippedCount = data.skipped_rows.length;
  if (data.reason) {
    setBadge(card, "warn", "Nothing saved");
  } else if (skippedCount > 0 || data.duplicate_rows > 0) {
    setBadge(card, "warn", "Saved with warnings");
  } else {
    setBadge(card, "ok", "Saved");
  }

  const stats = el("div", "stats");
  stats.append(
    stat("Inserted", data.inserted_rows),
    stat("Duplicates", data.duplicate_rows, data.duplicate_rows > 0 ? "warn" : ""),
    stat("Skipped", skippedCount, skippedCount > 0 ? "warn" : ""),
    stat("Alerts", data.alerts, data.alerts > 0 ? "alert" : "")
  );
  card.append(stats);

  if (data.reason) {
    card.append(el("p", "result-detail", `Reason: ${data.reason}`));
  }
  if (skippedCount > 0) {
    card.append(el("p", "result-detail", `Skipped lines (missing or invalid values): ${data.skipped_rows.join(", ")}`));
  }
}

function stat(label, value, modifier = "") {
  const box = el("div", `stat ${modifier}`.trim());
  box.append(el("div", "stat-value", String(value)), el("div", "stat-label", label));
  return box;
}

function renderErrorResult(card, status, message) {
  card.classList.add("error");
  setBadge(card, "error", status);
  card.append(el("p", "result-detail", message));
}

/* ---------- Logs ---------- */

levelFilter.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  state.level = button.dataset.level;
  levelFilter.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
  renderLogs();
});

logSearch.addEventListener("input", () => {
  state.search = logSearch.value.trim().toLowerCase();
  renderLogs();
});

refreshButton.addEventListener("click", () => {
  refreshButton.classList.remove("spinning");
  void refreshButton.offsetWidth; // restart the animation
  refreshButton.classList.add("spinning");
  loadLogs();
});

async function loadLogs() {
  try {
    const response = await fetch(`${LOGS_URL}?limit=${LOG_LIMIT}`);
    if (!response.ok) throw new Error(response.statusText);
    const entries = await response.json();
    setApiStatus("online", "API online");

    const signature = `${entries.length}|${entries[0]?.time}|${entries[0]?.message}`;
    if (signature === state.lastSignature) return;
    state.lastSignature = signature;
    state.entries = entries;
    renderLogs();
  } catch {
    setApiStatus("offline", "API offline");
  }
}

function setApiStatus(stateName, label) {
  apiStatus.dataset.state = stateName;
  apiStatus.querySelector(".label").textContent = label;
}

function matchesLevel(entry) {
  if (state.level === "ALL") return true;
  if (state.level === "ERROR") return ERROR_LEVELS.includes(entry.level);
  return entry.level === state.level;
}

function renderLogs() {
  const visible = state.entries.filter(
    (entry) => matchesLevel(entry) && (!state.search || entry.message.toLowerCase().includes(state.search))
  );

  const count = (levels) => state.entries.filter((entry) => levels.includes(entry.level)).length;
  logCounts.textContent =
    `${count(["INFO"])} info · ${count(["WARNING"])} warnings · ${count(ERROR_LEVELS)} errors` +
    (visible.length !== state.entries.length ? ` — showing ${visible.length} of ${state.entries.length}` : "");

  if (visible.length === 0) {
    const message = state.entries.length === 0 ? "No logs yet. Upload a file to get started." : "No logs match this filter.";
    logList.replaceChildren(el("div", "empty", message));
    return;
  }
  logList.replaceChildren(...visible.map(renderLogRow));
}

function renderLogRow(entry) {
  const row = el("div", `log-row ${entry.level}`);
  const [date, time] = entry.time.split(" ");
  const timeCell = el("span", "log-time", time.split(",")[0]);
  timeCell.title = `${date} ${time}`;

  const message = el("div", "log-message");
  const [firstLine, ...rest] = entry.message.split("\n");
  if (rest.length > 0) {
    // Multi-line entries are usually exception tracebacks: show the first line, expand for the rest.
    const details = el("details");
    details.append(el("summary", "", firstLine), el("pre", "", rest.join("\n")));
    message.append(details);
  } else {
    message.textContent = firstLine;
  }

  row.append(timeCell, el("span", `badge ${entry.level}`, entry.level), message);
  return row;
}

/* ---------- Logs written by a single call ---------- */

// The API tags every log line with the id of the request that wrote it, and sends that id back in a header.
// Returns that request's entries, oldest first.
async function logsForRequest(requestId) {
  if (!requestId) return [];
  try {
    const params = new URLSearchParams({ limit: CALL_LOG_LIMIT, request_id: requestId });
    const response = await fetch(`${LOGS_URL}?${params}`);
    const entries = await response.json();
    return entries.reverse();
  } catch {
    return [];
  }
}

function renderCallLogs(entries) {
  const details = el("details", "call-logs");
  details.open = entries.some((entry) => entry.level === "WARNING" || ERROR_LEVELS.includes(entry.level));
  details.append(el("summary", "", `Logs from this call (${entries.length})`));
  const list = el("div", "log-list");
  if (entries.length === 0) {
    list.append(el("div", "empty", "This call didn't write any logs."));
  } else {
    list.append(...entries.map(renderLogRow));
  }
  details.append(list);
  return details;
}

/* ---------- Endpoints ---------- */

async function loadEndpoints() {
  try {
    const response = await fetch(OPENAPI_URL);
    const spec = await response.json();
    const items = [];
    for (const [path, operations] of Object.entries(spec.paths)) {
      if (FRONTEND_ONLY_PATHS.includes(path)) continue;
      for (const [method, operation] of Object.entries(operations)) {
        items.push(renderEndpoint(spec, path, method, operation));
      }
    }
    endpointList.replaceChildren(...items);
  } catch {
    endpointList.replaceChildren(el("div", "empty table-error", "Could not load the API description. Is the server running?"));
  }
}

// Optional parameters are described as anyOf [type, null]; this finds the non-null part.
function baseSchema(schema = {}) {
  return schema.anyOf?.find((option) => option.type !== "null") ?? schema;
}

function inputTypeFor(schema) {
  const base = baseSchema(schema);
  if (base.format === "date") return "date";
  if (base.type === "integer" || base.type === "number") return "number";
  return "text";
}

// Names of the file fields in a multipart request body, if the endpoint takes one.
function fileFieldsFor(spec, operation) {
  let schema = operation.requestBody?.content?.["multipart/form-data"]?.schema;
  if (!schema) return [];
  if (schema.$ref) {
    schema = schema.$ref.split("/").slice(1).reduce((node, key) => node[key], spec);
  }
  return Object.entries(schema.properties ?? {})
    .filter(([, property]) => property.format === "binary" || property.contentMediaType)
    .map(([name]) => name);
}

function fieldName(name, required) {
  const span = el("span", "", name);
  if (required) span.append(el("span", "required", " *"));
  return span;
}

function renderEndpoint(spec, path, method, operation) {
  const parameters = operation.parameters ?? [];
  const fileFields = fileFieldsFor(spec, operation);

  const details = el("details", "endpoint");
  const summary = el("summary");
  summary.append(
    el("span", `method ${method}`, method.toUpperCase()),
    el("span", "endpoint-path", path),
    el("span", "endpoint-summary", operation.summary ?? "")
  );

  const body = el("div", "endpoint-body");
  body.append(el("p", "endpoint-description", operation.description ?? ""));

  const form = el("form", "endpoint-form");
  for (const parameter of parameters) {
    const label = el("label");
    label.append(fieldName(parameter.name, parameter.required));
    const input = el("input");
    input.name = parameter.name;
    input.type = inputTypeFor(parameter.schema);
    // No `required` attribute on purpose: sending without a value shows the API's own validation error.
    label.append(input);
    form.append(label);
  }
  for (const field of fileFields) {
    const label = el("label");
    label.append(fieldName(field, true));
    const input = el("input");
    input.name = field;
    input.type = "file";
    input.accept = ".csv,text/csv";
    label.append(input);
    form.append(label);
  }
  const send = el("button", "send-btn", "Send");
  send.type = "submit";
  form.append(send);

  const resultSlot = el("div");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    send.disabled = true;
    send.textContent = "Sending…";
    await callEndpoint(path, method, parameters, fileFields, new FormData(form), resultSlot);
    send.disabled = false;
    send.textContent = "Send";
  });

  body.append(form, resultSlot);
  details.append(summary, body);
  return details;
}

async function callEndpoint(path, method, parameters, fileFields, formData, resultSlot) {
  let url = path;
  const query = new URLSearchParams();
  for (const parameter of parameters) {
    const value = formData.get(parameter.name);
    if (!value) continue;
    if (parameter.in === "path") {
      url = url.replace(`{${parameter.name}}`, encodeURIComponent(value));
    } else {
      query.set(parameter.name, value);
    }
  }
  if (query.size) url += `?${query}`;

  let body;
  if (fileFields.length) {
    body = new FormData();
    for (const field of fileFields) {
      const file = formData.get(field);
      if (file && file.size) body.append(field, file);
    }
  }

  const started = performance.now();
  let response = null;
  let payload;
  try {
    response = await fetch(url, { method: method.toUpperCase(), body });
    const text = await response.text();
    try {
      payload = text ? JSON.parse(text) : undefined;
    } catch {
      payload = text;
    }
  } catch {
    // network error: response stays null
  }
  const durationMs = Math.round(performance.now() - started);
  const logs = await logsForRequest(response?.headers.get(REQUEST_ID_HEADER));

  resultSlot.replaceChildren(renderCallResult(method, url, response, payload, durationMs, logs));
  loadLogs();
  if (method !== "get") loadTable();
}

function renderCallResult(method, url, response, payload, durationMs, logs) {
  const ok = response?.ok ?? false;
  const box = el("div", ok ? "call-result" : "call-result error");
  const top = el("div", "call-result-top");
  const statusText = response ? `${response.status} ${response.statusText}` : "Network error";
  top.append(
    el("span", `badge ${ok ? "ok" : "error"}`, statusText),
    el("span", "endpoint-path", `${method.toUpperCase()} ${url}`),
    el("span", "call-duration", `${durationMs} ms`)
  );
  box.append(top);

  if (!response) {
    box.append(el("p", "call-note", "Could not reach the API. Is the server running?"));
  } else if (!ok) {
    box.append(el("p", "call-note", formatDetail(payload?.detail ?? payload)));
  } else if (payload === null || payload === undefined) {
    box.append(el("p", "call-note", "Empty response (null): the function doesn't return anything yet."));
  } else if (Array.isArray(payload) && payload.length && payload.every((item) => item && typeof item === "object")) {
    box.append(renderObjectTable(payload));
  } else {
    box.append(el("pre", "call-body", JSON.stringify(payload, null, 2)));
  }

  box.append(renderCallLogs(logs));
  return box;
}

function renderObjectTable(items) {
  const columns = [...new Set(items.flatMap((item) => Object.keys(item)))];
  const table = el("table", "data-table");
  const headRow = el("tr");
  columns.forEach((column) => headRow.append(el("th", "", COLUMN_LABELS[column] ?? column)));
  table.createTHead().append(headRow);
  const tbody = table.createTBody();
  for (const item of items) {
    const row = el("tr");
    columns.forEach((column) => {
      const value = item[column];
      row.append(el("td", "", typeof value === "object" && value !== null ? JSON.stringify(value) : String(value ?? "")));
    });
    tbody.append(row);
  }
  const wrap = el("div", "table-wrap");
  wrap.append(table);
  return wrap;
}

/* ---------- Data tables ---------- */

tableTabs.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button || button.dataset.table === tableState.table) return;
  tableState.table = button.dataset.table;
  tableState.sort = { ...DEFAULT_SORT };
  tableState.offset = 0;
  tableTabs.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
  loadTable();
});

let filterTimer;
tableFilters.addEventListener("input", () => {
  clearTimeout(filterTimer);
  filterTimer = setTimeout(() => {
    tableState.offset = 0;
    loadTable();
  }, FILTER_DEBOUNCE_MS);
});
tableFilters.addEventListener("submit", (event) => event.preventDefault());
tableFilters.addEventListener("reset", () => {
  // The form clears its fields after this event fires, so load on the next tick.
  setTimeout(() => {
    tableState.offset = 0;
    loadTable();
  });
});

prevPage.addEventListener("click", () => {
  tableState.offset = Math.max(0, tableState.offset - tableState.limit);
  loadTable();
});
nextPage.addEventListener("click", () => {
  tableState.offset += tableState.limit;
  loadTable();
});

dataTable.querySelector("thead").addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  const column = button.dataset.column;
  tableState.sort =
    tableState.sort.column === column
      ? { column, descending: !tableState.sort.descending }
      : { column, descending: false };
  tableState.offset = 0;
  loadTable();
});

async function loadTable() {
  const requestId = ++tableState.requestId;
  const form = new FormData(tableFilters);
  tableState.limit = Number(form.get("limit"));

  const params = new URLSearchParams();
  for (const [key, value] of form) {
    if (value) params.set(key, value);
  }
  params.set("sort", tableState.sort.column);
  params.set("descending", String(tableState.sort.descending));
  params.set("offset", String(tableState.offset));

  try {
    const response = await fetch(`${TABLES_URL}/${tableState.table}?${params}`);
    const data = await response.json().catch(() => ({}));
    if (requestId !== tableState.requestId) return; // a newer request already replaced this one
    if (!response.ok) {
      renderTableMessage(formatDetail(data.detail), true);
      return;
    }
    tableState.total = data.total;
    renderTable(data);
  } catch {
    if (requestId === tableState.requestId) renderTableMessage("Could not reach the API. Is the server running?", true);
  }
}

function renderTable({ columns, rows, total, offset }) {
  const headRow = el("tr");
  for (const column of columns) {
    const th = el("th", NUMERIC_COLUMNS.includes(column) ? "num" : "");
    if (tableState.sort.column === column) {
      th.setAttribute("aria-sort", tableState.sort.descending ? "descending" : "ascending");
    }
    const button = el("button", "", COLUMN_LABELS[column] ?? column);
    button.type = "button";
    button.dataset.column = column;
    th.append(button);
    headRow.append(th);
  }
  dataTable.tHead.replaceChildren(headRow);

  if (rows.length === 0) {
    const hasFilters = [...new FormData(tableFilters)].some(([key, value]) => key !== "limit" && value);
    renderTableMessage(hasFilters ? "No rows match these filters." : "This table is empty. Upload a CSV to add data.", false, columns.length);
  } else {
    dataTable.tBodies[0].replaceChildren(...rows.map((row) => renderTableRow(row, columns)));
  }

  const first = rows.length ? offset + 1 : 0;
  const last = offset + rows.length;
  tableRange.textContent = `${first}–${last} of ${total} ${total === 1 ? "row" : "rows"}`;
  prevPage.disabled = offset === 0;
  nextPage.disabled = last >= total;
}

function renderTableRow(row, columns) {
  const tr = el("tr");
  for (const column of columns) {
    const value = row[column];
    const td = el("td", NUMERIC_COLUMNS.includes(column) ? "num" : "");
    if (column === "id") {
      td.classList.add("id");
      td.textContent = value;
    } else if (column === "aqi_level") {
      const level = el("span", "aqi-level", value);
      level.style.setProperty("--level-color", AQI_LEVEL_COLORS[value] ?? "var(--muted)");
      td.append(level);
    } else if (NUMERIC_COLUMNS.includes(column)) {
      td.textContent = Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 });
    } else {
      td.textContent = value;
    }
    tr.append(td);
  }
  return tr;
}

function renderTableMessage(message, isError, colspan = dataTable.tHead.rows[0]?.cells.length || 1) {
  const cell = el("td", isError ? "empty table-error" : "empty", message);
  cell.colSpan = colspan;
  const row = el("tr");
  row.append(cell);
  dataTable.tBodies[0].replaceChildren(row);
  if (isError) {
    tableRange.textContent = "";
    prevPage.disabled = true;
    nextPage.disabled = true;
  }
}

loadLogs();
loadTable();
loadEndpoints();
setInterval(() => {
  if (autoRefresh.checked && !document.hidden) loadLogs();
}, REFRESH_INTERVAL_MS);

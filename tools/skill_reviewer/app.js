const STORAGE_KEY = "promptEngineeringSkillReviewerSettingsV1";
const DEFAULT_SETTINGS = {
  categories: {
    clothing: {
      label: "服装",
      color: "#5eead4",
      enabled: true,
      terms: [
        "白色", "黑色", "灰色", "蓝色", "红色", "粉色", "绿色", "米色", "卡其",
        "浅卡其", "牛仔", "衬衫", "T恤", "外套", "针织衫", "卫衣", "连衣裙",
        "半身裙", "长裙", "西装", "开衫", "毛衣", "短袖", "长袖", "运动套装",
        "休闲裤", "阔腿裤", "牛仔裤", "通勤", "休闲", "甜酷", "简约", "轻运动"
      ]
    },
    person: {
      label: "人物特征",
      color: "#fbbf24",
      enabled: true,
      terms: [
        "年轻", "女生", "男生", "女性", "男性", "中国", "圆脸", "鹅蛋脸", "瓜子脸",
        "脸型", "五官", "眉眼", "单眼皮", "双眼皮", "发型", "短发", "长发", "卷发",
        "直发", "马尾", "丸子头", "刘海", "黑发", "棕发", "发色", "微笑", "直视镜头",
        "正面", "人物居中", "固定中景", "数字人口播首帧", "甜美", "可爱", "清冷",
        "御姐", "邻家", "清爽"
      ]
    },
    benefit: {
      label: "利益点",
      color: "#a78bfa",
      enabled: true,
      terms: [
        "淘宝闪购", "红包", "无门槛红包", "最高12元", "最高25元", "优惠", "优惠券",
        "抵扣", "满减", "折扣", "福利", "活动", "新人", "包邮", "配送到家", "外卖到家",
        "领", "省", "划算"
      ]
    },
    product: {
      label: "商品信息",
      color: "#93c5fd",
      enabled: true,
      terms: [
        "商品", "品类", "商品名称", "卖点", "包装", "桌面", "台面", "购物袋", "完整",
        "可见", "不由人物手持", "人物不看商品", "人物不接触商品"
      ]
    },
    custom: {
      label: "自定义",
      color: "#fb7185",
      enabled: true,
      terms: []
    }
  },
  customTerms: []
};

const state = {
  settings: loadSettings(),
  sourceName: "",
  sourceType: "",
  rows: [],
  columns: [],
  filteredRows: [],
  selectedIndex: 0,
  databaseId: "",
  tables: [],
  activeTable: "",
  pageOffset: 0,
  pageLimit: 200,
  sourceFiles: [],
  activeSourceId: "",
  statusByTaskId: {},
  statusDatabase: "",
  displayLabel: ""
};

const elements = {
  fileInput: document.getElementById("file-input"),
  refreshSources: document.getElementById("refresh-sources"),
  dailySourceList: document.getElementById("daily-source-list"),
  sourceRoot: document.getElementById("source-root"),
  sourceStatus: document.getElementById("source-status"),
  dbPanel: document.getElementById("db-panel"),
  tableSelect: document.getElementById("table-select"),
  prevPage: document.getElementById("prev-page"),
  nextPage: document.getElementById("next-page"),
  searchInput: document.getElementById("search-input"),
  highlightToggle: document.getElementById("highlight-toggle"),
  denseToggle: document.getElementById("dense-toggle"),
  categoryControls: document.getElementById("category-controls"),
  resetSettings: document.getElementById("reset-settings"),
  customForm: document.getElementById("custom-form"),
  customTerm: document.getElementById("custom-term"),
  customCategory: document.getElementById("custom-category"),
  customList: document.getElementById("custom-list"),
  datasetTitle: document.getElementById("dataset-title"),
  datasetMeta: document.getElementById("dataset-meta"),
  emptyState: document.getElementById("empty-state"),
  reviewGrid: document.getElementById("review-grid"),
  rowList: document.getElementById("row-list"),
  detailContent: document.getElementById("detail-content"),
  exportSettings: document.getElementById("export-settings"),
  settingsInput: document.getElementById("settings-input")
};

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function loadSettings() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    if (!stored || !stored.categories) {
      return clone(DEFAULT_SETTINGS);
    }
    const merged = clone(DEFAULT_SETTINGS);
    for (const [key, category] of Object.entries(stored.categories)) {
      merged.categories[key] = { ...(merged.categories[key] || {}), ...category };
    }
    merged.customTerms = Array.isArray(stored.customTerms) ? stored.customTerms : [];
    return merged;
  } catch {
    return clone(DEFAULT_SETTINGS);
  }
}

function saveSettings() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.settings));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function textOf(row, field) {
  const value = row[field];
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = "";
  let insideQuotes = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];
    if (insideQuotes) {
      if (char === '"' && next === '"') {
        value += '"';
        index += 1;
      } else if (char === '"') {
        insideQuotes = false;
      } else {
        value += char;
      }
      continue;
    }
    if (char === '"') {
      insideQuotes = true;
    } else if (char === ",") {
      row.push(value);
      value = "";
    } else if (char === "\n") {
      row.push(value);
      rows.push(row);
      row = [];
      value = "";
    } else if (char !== "\r") {
      value += char;
    }
  }
  if (value || row.length) {
    row.push(value);
    rows.push(row);
  }
  if (!rows.length) {
    return { columns: [], rows: [] };
  }
  const columns = rows[0].map((header, index) => header.trim() || `column_${index + 1}`);
  const dataRows = rows.slice(1).filter((items) => items.some((item) => item.trim()));
  return {
    columns,
    rows: dataRows.map((items) => Object.fromEntries(columns.map((column, index) => [column, items[index] || ""])))
  };
}

function noteLabel(value) {
  const normalized = String(value || "").trim();
  if (!normalized) {
    return "";
  }
  for (const separator of ["+", "＋"]) {
    const index = normalized.indexOf(separator);
    if (index > -1) {
      return normalized.slice(0, index).trim();
    }
  }
  return normalized;
}

function noteSummary(rows) {
  const counts = new Map();
  for (const row of rows) {
    const label = noteLabel(textOf(row, "notes"));
    if (!label) {
      continue;
    }
    counts.set(label, (counts.get(label) || 0) + 1);
  }
  return [...counts.entries()].map(([label, count]) => `${label}x${count}`).join(" ");
}

function formatBytes(size) {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function formatModified(timestamp) {
  if (!timestamp) {
    return "";
  }
  return new Date(timestamp * 1000).toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit"
  });
}

function categoryEntries() {
  return Object.entries(state.settings.categories);
}

function buildHighlightTerms() {
  const terms = [];
  for (const [key, category] of categoryEntries()) {
    if (!category.enabled) {
      continue;
    }
    const categoryTerms = [...(category.terms || [])];
    for (const customTerm of state.settings.customTerms) {
      if (customTerm.category === key) {
        categoryTerms.push(customTerm.term);
      }
    }
    for (const term of categoryTerms) {
      const normalized = String(term || "").trim();
      if (normalized) {
        terms.push({ term: normalized, key, color: category.color });
      }
    }
  }
  terms.sort((left, right) => right.term.length - left.term.length);
  return terms;
}

function highlight(value) {
  const source = String(value ?? "");
  if (!elements.highlightToggle.checked || !source) {
    return escapeHtml(source);
  }
  const terms = buildHighlightTerms();
  if (!terms.length) {
    return escapeHtml(source);
  }
  const pattern = new RegExp(terms.map((item) => escapeRegExp(item.term)).join("|"), "g");
  const byTerm = new Map(terms.map((item) => [item.term, item]));
  let cursor = 0;
  let output = "";
  for (const match of source.matchAll(pattern)) {
    const index = match.index || 0;
    const text = match[0];
    const item = byTerm.get(text);
    output += escapeHtml(source.slice(cursor, index));
    output += `<span class="hl" style="background:${item.color}" title="${escapeHtml(state.settings.categories[item.key].label)}">${escapeHtml(text)}</span>`;
    cursor = index + text.length;
  }
  output += escapeHtml(source.slice(cursor));
  return output;
}

function primaryFields() {
  return [
    "script", "audio_prompt", "marked_script", "person_prompt", "image_prompt",
    "avatar_prompt", "copywriting_prompt", "title", "notes", "task_id"
  ];
}

function rowTitle(row, index) {
  return textOf(row, "task_id") || textOf(row, "title") || textOf(row, "id") || `row-${index + 1}`;
}

function rowSummary(row) {
  for (const field of primaryFields()) {
    const value = textOf(row, field);
    if (value && field !== "task_id" && field !== "title") {
      return value;
    }
  }
  const firstTextColumn = state.columns.find((column) => textOf(row, column));
  return firstTextColumn ? textOf(row, firstTextColumn) : "";
}

function rawStatus(row) {
  const taskId = textOf(row, "task_id");
  return taskId ? state.statusByTaskId[taskId] || "" : "";
}

function statusLabel(status) {
  const normalized = String(status || "").trim().toUpperCase();
  if (!normalized) {
    return "未发配";
  }
  if (["COMPLETED", "DONE", "SUCCESS", "SUCCEEDED"].includes(normalized)) {
    return "已完成";
  }
  if (["FAILED", "ERROR", "CANCELED", "CANCELLED"].includes(normalized)) {
    return "失败";
  }
  if (["CREATED", "PENDING", "QUEUED", "READY", "DRAFT"].includes(normalized)) {
    return "未发配";
  }
  return "生成中";
}

function statusTone(status) {
  const label = statusLabel(status);
  if (label === "已完成") {
    return "done";
  }
  if (label === "失败") {
    return "failed";
  }
  if (label === "生成中") {
    return "running";
  }
  return "idle";
}

function applyFilter() {
  const needle = elements.searchInput.value.trim().toLowerCase();
  if (!needle) {
    state.filteredRows = [...state.rows];
  } else {
    state.filteredRows = state.rows.filter((row) =>
      state.columns.some((column) => textOf(row, column).toLowerCase().includes(needle))
    );
  }
  if (state.selectedIndex >= state.filteredRows.length) {
    state.selectedIndex = 0;
  }
  renderRows();
  renderDetail();
}

function renderRows() {
  elements.rowList.classList.toggle("dense", elements.denseToggle.checked);
  if (!state.filteredRows.length) {
    elements.rowList.innerHTML = `<div class="empty-state"><p>没有匹配结果</p></div>`;
    return;
  }
  elements.rowList.innerHTML = state.filteredRows
    .map((row, index) => {
      const active = index === state.selectedIndex ? " active" : "";
      return `
        <button class="row-card${active}" type="button" data-index="${index}">
          <div class="row-title">
            <span>${escapeHtml(rowTitle(row, index))}</span>
            <span class="row-badges">
              <span class="status-badge ${statusTone(rawStatus(row))}">${escapeHtml(statusLabel(rawStatus(row)))}</span>
              <span class="badge">#${index + 1}</span>
            </span>
          </div>
          <div class="row-summary">${escapeHtml(rowSummary(row))}</div>
        </button>
      `;
    })
    .join("");
}

function renderDetail() {
  const row = state.filteredRows[state.selectedIndex];
  if (!row) {
    elements.detailContent.innerHTML = "";
    return;
  }
  const orderedColumns = [
    ...primaryFields().filter((field) => state.columns.includes(field)),
    ...state.columns.filter((field) => !primaryFields().includes(field))
  ];
  elements.detailContent.innerHTML = orderedColumns
    .map((column) => `
      <section class="field-block">
        <div class="field-name">${escapeHtml(column)}</div>
        <div class="field-value">${highlight(textOf(row, column))}</div>
      </section>
    `)
    .join("");
}

function renderDataset() {
  const total = state.rows.length;
  elements.datasetTitle.textContent = state.displayLabel || state.sourceName || "已导入数据";
  const fileText = state.sourceName ? ` · ${state.sourceName}` : "";
  const statusText = state.statusDatabase ? ` · 状态库 ${state.statusDatabase}` : "";
  elements.datasetMeta.textContent = `${state.sourceType || "数据"} · ${total} 行 · ${state.columns.length} 列${fileText}${statusText}`;
  elements.emptyState.classList.add("hidden");
  elements.reviewGrid.classList.remove("hidden");
  applyFilter();
}

function renderCategoryControls() {
  elements.categoryControls.innerHTML = categoryEntries()
    .map(([key, category]) => `
      <div class="category-row">
        <label class="category-label">
          <input type="checkbox" data-category-toggle="${escapeHtml(key)}" ${category.enabled ? "checked" : ""} />
          <span class="swatch" style="background:${category.color}"></span>
          <span>${escapeHtml(category.label)}</span>
        </label>
        <input type="color" value="${category.color}" data-category-color="${escapeHtml(key)}" />
      </div>
    `)
    .join("");

  elements.customCategory.innerHTML = categoryEntries()
    .map(([key, category]) => `<option value="${escapeHtml(key)}">${escapeHtml(category.label)}</option>`)
    .join("");
}

function renderCustomList() {
  if (!state.settings.customTerms.length) {
    elements.customList.innerHTML = `<div class="status-line">尚未添加自定义短语</div>`;
    return;
  }
  elements.customList.innerHTML = state.settings.customTerms
    .map((item, index) => {
      const category = state.settings.categories[item.category] || state.settings.categories.custom;
      return `
        <div class="chip">
          <span><span class="swatch" style="background:${category.color}"></span> ${escapeHtml(item.term)}</span>
          <button type="button" data-remove-custom="${index}">删除</button>
        </div>
      `;
    })
    .join("");
}

function renderSettings() {
  renderCategoryControls();
  renderCustomList();
  renderRows();
  renderDetail();
}

function openCsvText(name, text, statusByTaskId = {}, statusDatabase = "", displayLabel = "") {
  const parsed = parseCsv(text.replace(/^\uFEFF/, ""));
  state.sourceName = name;
  state.sourceType = "CSV";
  state.columns = parsed.columns;
  state.rows = parsed.rows;
  state.statusByTaskId = statusByTaskId;
  state.statusDatabase = statusDatabase;
  state.displayLabel = displayLabel || noteSummary(parsed.rows) || name;
  state.selectedIndex = 0;
  elements.dbPanel.classList.add("hidden");
  elements.sourceStatus.textContent = `已导入 CSV：${state.displayLabel}`;
  renderDataset();
}

async function openCsv(file) {
  openCsvText(file.name, await file.text(), {}, "");
}

async function openSourceCsv(file) {
  elements.sourceStatus.textContent = `正在读取 CSV：${file.name}`;
  const url = new URL("/api/source/csv", window.location.origin);
  url.searchParams.set("id", file.id);
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "CSV 读取失败");
  }
  state.activeSourceId = file.id;
  openCsvText(
    payload.name || file.name,
    payload.text || "",
    payload.status_by_task_id || {},
    payload.database || "",
    payload.label || file.label || ""
  );
  renderDailySources();
}

function renderDailySources() {
  if (!state.sourceFiles.length) {
    elements.dailySourceList.innerHTML = `<div class="status-line">没有找到 CSV 文件</div>`;
    return;
  }
  const groups = new Map();
  for (const file of state.sourceFiles) {
    if (!groups.has(file.date)) {
      groups.set(file.date, []);
    }
    groups.get(file.date).push(file);
  }
  elements.dailySourceList.innerHTML = [...groups.entries()]
    .map(([date, files]) => `
      <section class="source-date-group">
        <div class="source-date">${escapeHtml(date)}</div>
        ${files.map((file) => `
          <button class="source-file${file.id === state.activeSourceId ? " active" : ""}" type="button" data-source-id="${escapeHtml(file.id)}">
            <span class="source-type">${escapeHtml(file.type)}</span>
            <span>
              <span class="source-file-title">${escapeHtml(file.label || file.name)}</span>
              <span class="source-file-name">${escapeHtml(file.name)}</span>
              <span class="source-file-meta">${formatBytes(file.size)} · ${formatModified(file.modified)}${file.database ? ` · 状态库 ${escapeHtml(file.database.name)}` : ""}</span>
            </span>
          </button>
        `).join("")}
      </section>
    `)
    .join("");
}

async function loadDailySources() {
  elements.dailySourceList.innerHTML = `<div class="status-line">正在扫描目录...</div>`;
  try {
    const response = await fetch("/api/sources");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "目录扫描失败");
    }
    state.sourceFiles = payload.files || [];
    elements.sourceRoot.textContent = payload.root || elements.sourceRoot.textContent;
    renderDailySources();
  } catch (error) {
    elements.dailySourceList.innerHTML = `<div class="error">${escapeHtml(error.message)}</div>`;
  }
}

async function loadActiveTable() {
  const url = new URL("/api/sqlite/table", window.location.origin);
  url.searchParams.set("id", state.databaseId);
  url.searchParams.set("table", state.activeTable);
  url.searchParams.set("limit", String(state.pageLimit));
  url.searchParams.set("offset", String(state.pageOffset));
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "SQLite 表读取失败");
  }
  state.columns = payload.columns || [];
  state.rows = payload.rows || [];
  state.selectedIndex = 0;
  renderDataset();
}

function downloadJson(filename, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

elements.fileInput.addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) {
    return;
  }
  try {
    state.activeSourceId = "";
    const lowerName = file.name.toLowerCase();
    if (lowerName.endsWith(".csv")) {
      await openCsv(file);
    } else {
      throw new Error("只支持 CSV 文件");
    }
  } catch (error) {
    elements.sourceStatus.innerHTML = `<span class="error">${escapeHtml(error.message)}</span>`;
  } finally {
    elements.fileInput.value = "";
  }
});

elements.refreshSources.addEventListener("click", loadDailySources);

elements.dailySourceList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-source-id]");
  if (!button) {
    return;
  }
  const file = state.sourceFiles.find((item) => item.id === button.dataset.sourceId);
  if (!file) {
    return;
  }
  try {
    await openSourceCsv(file);
  } catch (error) {
    elements.sourceStatus.innerHTML = `<span class="error">${escapeHtml(error.message)}</span>`;
  }
});

elements.rowList.addEventListener("click", (event) => {
  const card = event.target.closest("[data-index]");
  if (!card) {
    return;
  }
  state.selectedIndex = Number(card.dataset.index);
  renderRows();
  renderDetail();
});

elements.searchInput.addEventListener("input", applyFilter);
elements.highlightToggle.addEventListener("change", () => {
  renderRows();
  renderDetail();
});
elements.denseToggle.addEventListener("change", renderRows);

elements.categoryControls.addEventListener("change", (event) => {
  const target = event.target;
  const toggleKey = target.dataset.categoryToggle;
  const colorKey = target.dataset.categoryColor;
  if (toggleKey) {
    state.settings.categories[toggleKey].enabled = target.checked;
  }
  if (colorKey) {
    state.settings.categories[colorKey].color = target.value;
  }
  saveSettings();
  renderSettings();
});

elements.customForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const term = elements.customTerm.value.trim();
  const category = elements.customCategory.value;
  if (!term) {
    return;
  }
  state.settings.customTerms.push({ term, category });
  elements.customTerm.value = "";
  saveSettings();
  renderSettings();
});

elements.customList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-remove-custom]");
  if (!button) {
    return;
  }
  state.settings.customTerms.splice(Number(button.dataset.removeCustom), 1);
  saveSettings();
  renderSettings();
});

elements.resetSettings.addEventListener("click", () => {
  state.settings = clone(DEFAULT_SETTINGS);
  saveSettings();
  renderSettings();
});

elements.exportSettings.addEventListener("click", () => {
  downloadJson("skill-reviewer-highlight-settings.json", state.settings);
});

elements.settingsInput.addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) {
    return;
  }
  try {
    const imported = JSON.parse(await file.text());
    if (!imported.categories) {
      throw new Error("配置文件缺少 categories");
    }
    state.settings = imported;
    saveSettings();
    renderSettings();
  } catch (error) {
    elements.sourceStatus.innerHTML = `<span class="error">${escapeHtml(error.message)}</span>`;
  } finally {
    elements.settingsInput.value = "";
  }
});

elements.tableSelect.addEventListener("change", async () => {
  state.activeTable = elements.tableSelect.value;
  state.pageOffset = 0;
  await loadActiveTable();
});

elements.prevPage.addEventListener("click", async () => {
  state.pageOffset = Math.max(0, state.pageOffset - state.pageLimit);
  await loadActiveTable();
});

elements.nextPage.addEventListener("click", async () => {
  state.pageOffset += state.pageLimit;
  await loadActiveTable();
});

renderSettings();
loadDailySources();

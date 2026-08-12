const STORAGE_KEY = "promptEngineeringSkillReviewerSettingsV1";
const WORKBENCH_STORAGE_KEY = "promptEngineeringSkillReviewerWorkbenchV1";
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
    referenceImage: {
      label: "参考图",
      color: "#fdba74",
      enabled: true,
      terms: [
        "reference_image_uri", "reference_image_url", "reference_image_pid", "参考图",
        "素材 URI", "签名 URL", "images[]"
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

Object.assign(elements, {
  workbenchToggle: document.getElementById("workbench-toggle"),
  workbenchSubtitle: document.getElementById("workbench-subtitle"),
  learningRefresh: document.getElementById("learning-refresh"),
  learningStatusFilter: document.getElementById("learning-status-filter"),
  learningMediaPanel: document.getElementById("learning-media-panel"),
  learningMediaDate: document.getElementById("learning-media-date"),
  learningMediaRefresh: document.getElementById("learning-media-refresh"),
  learningMediaRoot: document.getElementById("learning-media-root"),
  learningMediaSelectAll: document.getElementById("learning-media-select-all"),
  learningMediaCount: document.getElementById("learning-media-count"),
  learningMediaList: document.getElementById("learning-media-list"),
  learningMediaTranscribe: document.getElementById("learning-media-transcribe"),
  learningMediaStatus: document.getElementById("learning-media-status"),
  learningCopyBrowser: document.getElementById("learning-copy-browser"),
  learningAddPersonPanel: document.getElementById("learning-add-person-panel"),
  learningNewSource: document.getElementById("learning-new-source"),
  learningNewPrompt: document.getElementById("learning-new-prompt"),
  learningAddPerson: document.getElementById("learning-add-person"),
  learningAddStatus: document.getElementById("learning-add-status"),
  learningList: document.getElementById("learning-list"),
  learningDetail: document.getElementById("learning-detail")
});

const learningState = {
  workbench: localStorage.getItem(WORKBENCH_STORAGE_KEY) === "learning" ? "learning" : "task",
  kind: "copy",
  candidates: [],
  fieldOptions: {},
  selectedId: "",
  media: [],
  selectedMediaIds: new Set(),
  previewMediaId: "",
  mediaLoading: false,
  mediaError: "",
  transcribing: false
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
    "avatar_prompt", "copywriting_prompt", "title", "notes", "task_id",
    "reference_image_uri", "reference_image_url", "reference_image_pid"
  ];
}

function referenceImageFields(row) {
  return {
    uri: textOf(row, "reference_image_uri").trim(),
    url: textOf(row, "reference_image_url").trim(),
    pid: textOf(row, "reference_image_pid").trim()
  };
}

function hasReferenceImage(row) {
  const fields = referenceImageFields(row);
  return Boolean(fields.uri || fields.url || fields.pid);
}

function referenceImageLabel(row) {
  if (!state.columns.some((column) => column.startsWith("reference_image_"))) {
    return "";
  }
  return hasReferenceImage(row) ? "参考图" : "默认图";
}

function isHttpUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

function renderReferenceImageCard(row) {
  if (!state.columns.some((column) => column.startsWith("reference_image_"))) {
    return "";
  }
  const fields = referenceImageFields(row);
  const hasImage = Boolean(fields.uri || fields.url || fields.pid);
  const canPreview = isHttpUrl(fields.url);
  const stateText = hasImage ? "已配置参考图" : "未配置参考图";
  const hint = hasImage
    ? "人物图片生成会携带参考图约束商品外观。"
    : "下游会按默认文生图流程生成数字人图片。";
  return `
    <section class="reference-card${hasImage ? "" : " muted-card"}">
      <div class="reference-card-head">
        <div>
          <div class="reference-card-title">${escapeHtml(stateText)}</div>
          <div class="reference-card-hint">${escapeHtml(hint)}</div>
        </div>
        <span class="reference-pill">${escapeHtml(hasImage ? "images[]" : "empty")}</span>
      </div>
      <div class="reference-card-body">
        ${
          canPreview
            ? `<a class="reference-preview" href="${escapeHtml(fields.url)}" target="_blank" rel="noreferrer">
                 <img src="${escapeHtml(fields.url)}" alt="参考图预览" loading="lazy" />
               </a>`
            : `<div class="reference-preview placeholder">
                 <span>${escapeHtml(hasImage ? "运行时补取签名 URL" : "无参考图")}</span>
               </div>`
        }
        <div class="reference-meta">
          <div><span>URI</span><strong>${escapeHtml(fields.uri || "未填写")}</strong></div>
          <div><span>URL</span><strong>${escapeHtml(fields.url || "未填写")}</strong></div>
          <div><span>PID</span><strong>${escapeHtml(fields.pid || "未填写")}</strong></div>
          ${canPreview ? `<a class="reference-link" href="${escapeHtml(fields.url)}" target="_blank" rel="noreferrer">打开参考图</a>` : ""}
        </div>
      </div>
    </section>
  `;
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
              ${referenceImageLabel(row) ? `<span class="reference-badge ${hasReferenceImage(row) ? "active" : "idle"}">${escapeHtml(referenceImageLabel(row))}</span>` : ""}
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
  elements.detailContent.innerHTML = renderReferenceImageCard(row) + orderedColumns
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

function setWorkbench(value) {
  learningState.workbench = value;
  localStorage.setItem(WORKBENCH_STORAGE_KEY, value);
  const learning = value === "learning";
  document.querySelectorAll(".task-workbench").forEach((element) => element.classList.toggle("hidden", learning));
  document.querySelectorAll(".learning-workbench").forEach((element) => element.classList.toggle("hidden", !learning));
  elements.workbenchToggle.textContent = learning ? "返回任务审核" : "切换到学习审核";
  elements.workbenchSubtitle.textContent = learning ? "学习审核" : "CSV 审核与状态预览";
  if (learning) {
    renderLearningHeader();
    updateLearningPanelVisibility();
    loadLearningCandidates();
    if (learningState.kind === "copy") loadLearningMedia();
  } else {
    renderDatasetHeaderForTask();
  }
}

function renderLearningHeader() {
  elements.datasetTitle.textContent = learningState.kind === "copy" ? "学习审核 · 视频文案" : "学习审核 · 人物 Prompt";
  elements.datasetMeta.textContent = "原始内容只读，所有保存使用 revision 冲突保护";
}

function renderDatasetHeaderForTask() {
  const total = state.rows.length;
  elements.datasetTitle.textContent = state.displayLabel || state.sourceName || "还没有数据";
  elements.datasetMeta.textContent = total
    ? `${state.sourceType || "数据"} · ${total} 行 · ${state.columns.length} 列`
    : "导入后会自动识别字段并高亮可审核内容";
}

function updateLearningPanelVisibility() {
  const learning = learningState.workbench === "learning";
  elements.learningAddPersonPanel.classList.toggle("hidden", !(learning && learningState.kind === "person"));
  elements.learningMediaPanel.classList.toggle("hidden", !(learning && learningState.kind === "copy"));
  elements.learningCopyBrowser.classList.toggle("hidden", !(learning && learningState.kind === "copy"));
}

function learningStatusTone(status) {
  if (status === "published" || status === "approved") return "done";
  if (status === "rejected") return "failed";
  if (status === "ready_for_review") return "running";
  return "idle";
}

function learningStatusHelp() {
  return `<span class="status-help" aria-label="查看学习状态说明">
    <span class="status-help-icon" aria-hidden="true">?</span>
    <span class="status-help-tooltip" role="tooltip">
      <span><strong>pending / editing：</strong>本地已保存，但还不能用。</span>
      <span><strong>ready_for_review：</strong>已提交审核，但还不能用。</span>
      <span><strong>approved：</strong>已批准，等待 Codex 拆解并发布，仍不能用。</span>
      <span><strong>published：</strong>已进入正式学习资源，可以用于后续生成。</span>
    </span>
  </span>`;
}

function positionLearningStatusTooltip(help) {
  const tooltip = help.querySelector(".status-help-tooltip");
  if (!tooltip) return;
  const margin = 12;
  const gap = 8;
  const anchor = help.getBoundingClientRect();
  const width = Math.min(360, window.innerWidth - margin * 2);
  tooltip.style.width = `${width}px`;
  const height = tooltip.getBoundingClientRect().height || 150;
  const left = Math.min(
    Math.max(margin, anchor.right - width),
    window.innerWidth - width - margin
  );
  const below = anchor.bottom + gap;
  const top = below + height <= window.innerHeight - margin
    ? below
    : Math.max(margin, anchor.top - height - gap);
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
}

async function learningRequest(url, options = {}) {
  let response;
  try {
    response = await fetch(url, {
      ...options,
      cache: "no-store",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) }
    });
  } catch (_error) {
    throw new Error("无法连接审核台服务，请确认 tools/skill_reviewer/run.sh 正在运行");
  }
  let payload;
  try {
    payload = await response.json();
  } catch (_error) {
    throw new Error("审核台服务响应异常，请重启 tools/skill_reviewer/run.sh 后刷新页面");
  }
  if (!response.ok) {
    const error = new Error(payload.error || "学习审核请求失败");
    error.status = response.status;
    throw error;
  }
  return payload;
}

function localDateValue() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function renderLearningMedia() {
  const mediaIds = new Set(learningState.media.map((item) => item.id));
  learningState.selectedMediaIds = new Set(
    [...learningState.selectedMediaIds].filter((mediaId) => mediaIds.has(mediaId))
  );
  if (!mediaIds.has(learningState.previewMediaId)) learningState.previewMediaId = "";
  elements.learningMediaCount.textContent = `${learningState.media.length} 个媒体 · 已选 ${learningState.selectedMediaIds.size}`;
  elements.learningMediaSelectAll.checked = Boolean(learningState.media.length)
    && learningState.selectedMediaIds.size === learningState.media.length;
  elements.learningMediaSelectAll.indeterminate = learningState.selectedMediaIds.size > 0
    && learningState.selectedMediaIds.size < learningState.media.length;
  elements.learningMediaTranscribe.disabled = learningState.transcribing
    || learningState.mediaLoading || learningState.selectedMediaIds.size === 0;
  elements.learningMediaRefresh.disabled = learningState.mediaLoading;
  elements.learningMediaRefresh.textContent = learningState.mediaLoading ? "扫描中..." : "扫描";
  if (learningState.mediaLoading) {
    elements.learningMediaList.innerHTML = `<div class="status-line">正在扫描当天目录...</div>`;
    return;
  }
  if (learningState.mediaError) {
    elements.learningMediaList.innerHTML = `<div class="error media-error">${escapeHtml(learningState.mediaError)}</div>`;
    return;
  }
  if (!learningState.media.length) {
    elements.learningMediaList.innerHTML = `<div class="status-line">当天目录没有发现受支持的视频或音频</div>`;
    return;
  }
  elements.learningMediaList.innerHTML = learningState.media.map((item) => {
    const candidate = item.candidate;
    const candidateBadge = candidate
      ? `<span class="status-badge ${learningStatusTone(candidate.status)}">${escapeHtml(candidate.status)} · r${candidate.revision}</span>`
      : `<span class="status-badge idle">未识别</span>`;
    const active = item.id === learningState.previewMediaId ? " active" : "";
    return `<label class="learning-media-item${active}">
      <input type="checkbox" data-learning-media-id="${escapeHtml(item.id)}" ${learningState.selectedMediaIds.has(item.id) ? "checked" : ""} />
      <span class="learning-media-info">
        <span class="learning-media-title">${escapeHtml(item.name)}</span>
        <span class="source-file-meta">${formatBytes(item.size)} · ${formatModified(item.modified)}</span>
      </span>
      ${candidateBadge}
    </label>`;
  }).join("");
}

async function loadLearningMedia() {
  if (learningState.kind !== "copy" || learningState.workbench !== "learning") return;
  if (learningState.mediaLoading) return;
  const url = new URL("/api/learning/media", window.location.origin);
  url.searchParams.set("date", elements.learningMediaDate.value || localDateValue());
  learningState.mediaLoading = true;
  learningState.mediaError = "";
  elements.learningMediaStatus.classList.remove("error");
  elements.learningMediaStatus.textContent = "正在扫描当天目录...";
  renderLearningMedia();
  try {
    const payload = await learningRequest(url);
    learningState.media = payload.media || [];
    elements.learningMediaRoot.textContent = payload.root || elements.learningMediaRoot.textContent;
    elements.learningMediaStatus.textContent = payload.exists
      ? `扫描完成：发现 ${learningState.media.length} 个媒体`
      : "当天素材目录不存在";
  } catch (error) {
    learningState.media = [];
    learningState.mediaError = error.status === 404
      ? "当前审核台服务版本过旧，请关闭后重新运行 tools/skill_reviewer/run.sh"
      : error.message;
    elements.learningMediaStatus.textContent = `扫描失败：${learningState.mediaError}`;
    elements.learningMediaStatus.classList.add("error");
  } finally {
    learningState.mediaLoading = false;
    renderLearningMedia();
    renderLearningDetail();
  }
}

async function transcribeSelectedLearningMedia() {
  if (!learningState.selectedMediaIds.size || learningState.transcribing) return;
  learningState.transcribing = true;
  elements.learningMediaStatus.classList.remove("error");
  elements.learningMediaStatus.textContent = `正在识别 ${learningState.selectedMediaIds.size} 个媒体，请保持页面打开...`;
  renderLearningMedia();
  try {
    const result = await learningRequest("/api/learning/transcribe", {
      method: "POST",
      body: JSON.stringify({
        date: elements.learningMediaDate.value || localDateValue(),
        media_ids: [...learningState.selectedMediaIds]
      })
    });
    const completion = `完成：新建 ${result.succeeded}，缓存复用 ${result.reused}，失败 ${result.failed}`;
    const failures = Array.isArray(result.failures) ? result.failures : [];
    const failedNames = new Set(failures.map((failure) => failure.name));
    learningState.selectedMediaIds = new Set(
      learningState.media
        .filter((item) => failedNames.has(item.name))
        .map((item) => item.id)
    );
    if (result.candidate_ids?.length) {
      learningState.selectedId = result.candidate_ids[0];
      learningState.previewMediaId = "";
    }
    await Promise.all([loadLearningCandidates(), loadLearningMedia()]);
    if (failures.length) {
      const details = failures.map((failure) => `<li><strong>${escapeHtml(failure.name || "未知素材")}</strong><br />${escapeHtml(failure.error || "识别失败")}</li>`).join("");
      elements.learningMediaStatus.innerHTML = `<div>${escapeHtml(completion)}</div><ul class="learning-failure-list">${details}</ul><div>失败素材已保留勾选，可修复后直接重试。</div>`;
      elements.learningMediaStatus.classList.add("error");
    } else {
      elements.learningMediaStatus.textContent = completion;
    }
  } catch (error) {
    elements.learningMediaStatus.textContent = error.message;
    elements.learningMediaStatus.classList.add("error");
  } finally {
    learningState.transcribing = false;
    renderLearningMedia();
  }
}

async function loadLearningCandidates() {
  const url = new URL("/api/learning/candidates", window.location.origin);
  url.searchParams.set("kind", learningState.kind);
  if (elements.learningStatusFilter.value) {
    url.searchParams.set("status", elements.learningStatusFilter.value);
  }
  elements.learningList.innerHTML = `<div class="status-line">正在加载候选...</div>`;
  try {
    const payload = await learningRequest(url);
    learningState.candidates = payload.candidates || [];
    learningState.fieldOptions = payload.field_options || {};
    if (!learningState.candidates.some((item) => item.candidate_id === learningState.selectedId)) {
      learningState.selectedId = learningState.candidates[0]?.candidate_id || "";
    }
    renderLearningList();
    renderLearningDetail();
  } catch (error) {
    elements.learningList.innerHTML = `<div class="error">${escapeHtml(error.message)}</div>`;
  }
}

function renderLearningList() {
  if (!learningState.candidates.length) {
    elements.learningList.innerHTML = `<div class="empty-state compact-empty"><p>暂无候选</p></div>`;
    return;
  }
  elements.learningList.innerHTML = learningState.candidates.map((candidate) => {
    const active = candidate.candidate_id === learningState.selectedId ? " active" : "";
    const summary = learningState.kind === "copy" ? candidate.edited_transcript : candidate.edited_prompt;
    const source = learningState.kind === "copy" ? candidate.source_date : candidate.source_label;
    const canDelete = !["approved", "published"].includes(candidate.status);
    const deleteAction = canDelete
      ? `<button type="button" class="row-delete danger-action" data-learning-delete-id="${escapeHtml(candidate.candidate_id)}" aria-label="删除候选 ${escapeHtml(candidate.candidate_id)}">删除</button>`
      : "";
    return `<div class="row-card-shell${active}">
      <button type="button" class="row-card" data-learning-id="${escapeHtml(candidate.candidate_id)}">
      <div class="row-title"><span>${escapeHtml(source || candidate.candidate_id)}</span>
      <span class="learning-status"><span class="status-badge ${learningStatusTone(candidate.status)}">${escapeHtml(candidate.status)}</span>${learningStatusHelp()}</span></div>
      <div class="row-summary">revision ${candidate.revision} · ${escapeHtml(summary || "")}</div>
      </button>${deleteAction}</div>`;
  }).join("");
}

function structuredField(name, label, candidate, enabled = true) {
  const value = Array.isArray(candidate[name]) ? candidate[name].join("，") : (candidate[name] || "");
  return `<label class="learning-field"><span>${escapeHtml(label)}</span>
    <input class="field" data-learning-field="${escapeHtml(name)}" value="${escapeHtml(value)}" ${enabled ? "" : "disabled"} /></label>`;
}

function learningSelectField(name, label, candidate, enabled) {
  const options = learningState.fieldOptions[name] || [];
  const selected = candidate[name] || "";
  const selectedOption = options.find((option) => option.value === selected);
  const rendered = options.map((option) => `<option value="${escapeHtml(option.value)}" ${option.value === selected ? "selected" : ""}>${escapeHtml(option.label)}</option>`).join("");
  return `<label class="learning-field"><span>${escapeHtml(label)}</span>
    <select class="field" data-learning-field="${escapeHtml(name)}" ${enabled ? "" : "disabled"}>${rendered}</select>
    <small data-learning-description-for="${escapeHtml(name)}">${escapeHtml(selectedOption?.description || "请从列表中选择")}</small></label>`;
}

function learningMultiChoiceField(name, label, candidate, enabled) {
  const options = learningState.fieldOptions[name] || [];
  const selected = new Set(Array.isArray(candidate[name]) ? candidate[name] : []);
  const choices = options.map((option) => `<label class="learning-choice">
    <input type="checkbox" data-learning-choice="${escapeHtml(name)}" value="${escapeHtml(option.value)}" ${selected.has(option.value) ? "checked" : ""} ${enabled ? "" : "disabled"} />
    <span><strong>${escapeHtml(option.label)}</strong><small>${escapeHtml(option.description)}</small></span>
  </label>`).join("");
  return `<fieldset class="learning-field learning-choice-field"><legend>${escapeHtml(label)}</legend>
    <div class="learning-choice-group">${choices}</div></fieldset>`;
}

function renderLearningDetail() {
  const preview = learningState.kind === "copy"
    ? learningState.media.find((item) => item.id === learningState.previewMediaId) : null;
  if (preview) {
    const previewUrl = `/api/learning/media-content?date=${encodeURIComponent(elements.learningMediaDate.value || localDateValue())}&id=${encodeURIComponent(preview.id)}`;
    const audio = [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"].includes(preview.suffix);
    const player = audio
      ? `<audio class="learning-media-player audio-player" controls preload="metadata" src="${previewUrl}"></audio>`
      : `<video class="learning-media-player" controls preload="metadata" playsinline src="${previewUrl}"></video>`;
    elements.learningDetail.innerHTML = `<article class="learning-preview">
      <div class="learning-preview-heading">
        <div><div class="field-name">素材预览</div><h2>${escapeHtml(preview.name)}</h2></div>
        <span class="status-badge idle">${audio ? "音频" : "视频"}</span>
      </div>
      ${player}
      <div class="field-value">${formatBytes(preview.size)} · ${formatModified(preview.modified)}</div>
      <div class="helper-text">预览只读取已扫描素材，不会启动 ASR。勾选其他素材可切换预览。</div>
    </article>`;
    return;
  }
  const candidate = learningState.candidates.find((item) => item.candidate_id === learningState.selectedId);
  if (!candidate) {
    elements.learningDetail.innerHTML = `<div class="empty-state compact-empty"><p>选择一条学习候选查看详情</p></div>`;
    return;
  }
  const isCopy = learningState.kind === "copy";
  const raw = isCopy ? candidate.raw_transcript : candidate.raw_prompt;
  const edited = isCopy ? candidate.edited_transcript : candidate.edited_prompt;
  const canSave = ["pending", "editing", "rejected"].includes(candidate.status);
  const copyMetadataComplete = Boolean(candidate.category_family && candidate.consumption_need
    && Array.isArray(candidate.source_usage) && candidate.source_usage.length);
  const canSubmit = ["pending", "editing"].includes(candidate.status)
    && (!isCopy || copyMetadataComplete);
  const canDelete = !["approved", "published"].includes(candidate.status);
  const structured = isCopy
    ? [
        learningSelectField("category_family", "品类族", candidate, canSave),
        learningSelectField("consumption_need", "消费需求", candidate, canSave),
        learningSelectField("season", "季节限制", candidate, canSave),
        learningMultiChoiceField("source_usage", "来源块用途（可多选）", candidate, canSave)
      ]
    : [
        structuredField("identity_traits", "人物身份（逗号分隔）", candidate, canSave),
        structuredField("hair_traits", "发型（逗号分隔）", candidate, canSave),
        structuredField("outfit_traits", "服装（逗号分隔）", candidate, canSave),
        structuredField("scene_traits", "场景（逗号分隔）", candidate, canSave),
        structuredField("forbidden_traits", "禁止复用（逗号分隔）", candidate, canSave)
      ];
  const sourceMeta = isCopy
    ? `媒体：${escapeHtml(candidate.source_media)}<br />指纹：${escapeHtml(candidate.source_fingerprint)}<br />识别：${escapeHtml(candidate.provider)} · ${escapeHtml(candidate.model)}`
    : `来源：${escapeHtml(candidate.source_label)}`;
  const publicationHint = candidate.status === "approved"
    ? `<div class="publication-hint">待 Codex 生成发布清单并通过 CLI 发布</div>` : "";
  const draftHint = isCopy
    ? `<span class="helper-text">初始稿只整理中文逐字空格和明显重复标点；不会改字、猜测标点或改变原始时间轴。</span>`
    : "";
  const metadataHint = isCopy && !copyMetadataComplete
    ? `<div class="classification-hint">先选择品类族、消费需求和至少一种来源块用途并保存，才可提交学习。</div>`
    : "";
  elements.learningDetail.innerHTML = `<article class="learning-form" data-candidate-id="${escapeHtml(candidate.candidate_id)}" data-revision="${candidate.revision}">
    <div class="learning-meta"><strong>${escapeHtml(candidate.candidate_id)}</strong><span>revision ${candidate.revision} · ${escapeHtml(candidate.status)}</span></div>
    <div class="field-value">${sourceMeta}</div>
    <section class="field-block"><div class="field-name">不可变原文</div><div class="field-value raw-content">${escapeHtml(raw)}</div></section>
    <label class="field-block"><span class="field-name">可编辑稿</span><textarea id="learning-edited-text" class="field textarea" rows="10" ${canSave ? "" : "disabled"}>${escapeHtml(edited)}</textarea>${draftHint}</label>
    <div class="learning-structured${isCopy ? " copy-learning-structured" : ""}">${structured.join("")}</div>
    <section class="field-block"><div class="field-name">风险</div><div class="field-value">${escapeHtml((candidate.risk_tags || []).join("、") || "无")}</div></section>
    <section class="field-block"><div class="field-name">相似项</div><div class="field-value">${escapeHtml((candidate.similarity_hits || []).join("、") || "无")}</div></section>
    ${publicationHint}
    ${metadataHint}
    <div class="learning-actions">
      <div class="learning-actions-primary">
        <button type="button" data-learning-action="save" ${canSave ? "" : "disabled"}>保存修改</button>
        <button type="button" data-learning-action="submit-learning" title="确认内容并交给 Codex 发布" ${canSubmit ? "" : "disabled"}>提交学习</button>
      </div>
      <button type="button" class="danger-action" data-learning-action="delete" ${canDelete ? "" : "disabled"}>删除候选</button>
    </div>
    ${canDelete ? `<div class="helper-text">删除只把候选移入回收目录，不删除源素材；删除后可以重新创建。</div>` : `<div class="helper-text">已批准或已发布的候选不能删除。</div>`}
    <div id="learning-action-status" class="status-line"></div>
  </article>`;
}

function splitStructuredValue(value) {
  return value.split(/[，,\n]/).map((item) => item.trim()).filter(Boolean);
}

async function runLearningAction(action) {
  const candidate = learningState.candidates.find((item) => item.candidate_id === learningState.selectedId);
  if (!candidate) return;
  const status = document.getElementById("learning-action-status");
  const base = `/api/learning/candidates/${learningState.kind}/${encodeURIComponent(candidate.candidate_id)}`;
  let url = base;
  let method = "POST";
  let body = { expected_revision: candidate.revision };
  if (action === "save") {
    method = "PUT";
    body.edited_text = document.getElementById("learning-edited-text").value;
    document.querySelectorAll("[data-learning-field]").forEach((input) => {
      const listFields = ["source_usage", "identity_traits", "hair_traits", "outfit_traits", "scene_traits", "forbidden_traits"];
      body[input.dataset.learningField] = listFields.includes(input.dataset.learningField)
        ? splitStructuredValue(input.value) : input.value.trim();
    });
    document.querySelectorAll("[data-learning-choice]").forEach((input) => {
      const field = input.dataset.learningChoice;
      if (!Array.isArray(body[field])) body[field] = [];
      if (input.checked) body[field].push(input.value);
    });
  } else if (action === "delete") {
    const copyMessage = "删除后该素材会恢复为未识别，并可重新创建 ASR 候选。候选将移入回收目录，源素材不会删除。确定删除？";
    const personMessage = "候选将移入回收目录，原始输入不会写入正式学习资源。确定删除？";
    if (!window.confirm(learningState.kind === "copy" ? copyMessage : personMessage)) return;
    method = "DELETE";
  } else if (action === "submit-learning") {
    url += "/submit-learning";
  } else {
    return;
  }
  status.textContent = "正在提交...";
  try {
    const updated = await learningRequest(url, { method, body: JSON.stringify(body) });
    if (action === "delete") {
      const deletedMedia = learningState.media.find((item) => item.candidate?.candidate_id === candidate.candidate_id);
      learningState.selectedId = "";
      learningState.previewMediaId = "";
      await Promise.all([loadLearningCandidates(), loadLearningMedia()]);
      if (deletedMedia) {
        learningState.selectedId = "";
        learningState.selectedMediaIds.add(deletedMedia.id);
        learningState.previewMediaId = deletedMedia.id;
        elements.learningMediaStatus.textContent = "候选已移入回收目录；素材已重新勾选，可直接点击“创建 ASR 候选”。";
      }
      renderLearningMedia();
      renderLearningDetail();
      return;
    }
    const index = learningState.candidates.findIndex((item) => item.candidate_id === updated.candidate_id);
    learningState.candidates[index] = updated;
    renderLearningList();
    renderLearningDetail();
  } catch (error) {
    if (error.status === 409) {
      window.alert("revision 冲突：候选已被其他操作更新，请重新加载后再保存。");
      await loadLearningCandidates();
      return;
    }
    status.textContent = error.message;
    status.classList.add("error");
  }
}

elements.workbenchToggle.addEventListener("click", () => setWorkbench(learningState.workbench === "task" ? "learning" : "task"));
document.querySelectorAll('input[name="learning-kind"]').forEach((radio) => radio.addEventListener("change", () => {
  learningState.kind = radio.value;
  learningState.selectedId = "";
  learningState.previewMediaId = "";
  renderLearningHeader();
  updateLearningPanelVisibility();
  loadLearningCandidates();
  if (learningState.kind === "copy") loadLearningMedia();
}));
elements.learningStatusFilter.addEventListener("change", loadLearningCandidates);
elements.learningRefresh.addEventListener("click", () => {
  loadLearningCandidates();
  if (learningState.kind === "copy") loadLearningMedia();
});
elements.learningMediaRefresh.addEventListener("click", loadLearningMedia);
elements.learningMediaDate.addEventListener("change", () => {
  learningState.selectedMediaIds.clear();
  loadLearningMedia();
});
elements.learningMediaSelectAll.addEventListener("change", () => {
  learningState.selectedMediaIds = elements.learningMediaSelectAll.checked
    ? new Set(learningState.media.map((item) => item.id)) : new Set();
  learningState.previewMediaId = elements.learningMediaSelectAll.checked
    ? (learningState.media[0]?.id || "") : "";
  renderLearningMedia();
  renderLearningDetail();
});
elements.learningMediaList.addEventListener("change", (event) => {
  const checkbox = event.target.closest("[data-learning-media-id]");
  if (!checkbox) return;
  if (checkbox.checked) {
    learningState.selectedMediaIds.add(checkbox.dataset.learningMediaId);
    learningState.previewMediaId = checkbox.dataset.learningMediaId;
    learningState.selectedId = "";
  } else {
    learningState.selectedMediaIds.delete(checkbox.dataset.learningMediaId);
    if (learningState.previewMediaId === checkbox.dataset.learningMediaId) {
      learningState.previewMediaId = [...learningState.selectedMediaIds].at(-1) || "";
    }
  }
  renderLearningMedia();
  renderLearningDetail();
});
elements.learningMediaTranscribe.addEventListener("click", transcribeSelectedLearningMedia);
document.addEventListener("pointerover", (event) => {
  const help = event.target.closest(".status-help");
  if (help) positionLearningStatusTooltip(help);
});
elements.learningList.addEventListener("click", (event) => {
  const deleteButton = event.target.closest("[data-learning-delete-id]");
  if (deleteButton) {
    learningState.previewMediaId = "";
    learningState.selectedId = deleteButton.dataset.learningDeleteId;
    renderLearningList();
    renderLearningDetail();
    runLearningAction("delete");
    return;
  }
  const button = event.target.closest("[data-learning-id]");
  if (!button) return;
  learningState.previewMediaId = "";
  learningState.selectedId = button.dataset.learningId;
  renderLearningList();
  renderLearningDetail();
});
elements.learningDetail.addEventListener("click", (event) => {
  const button = event.target.closest("[data-learning-action]");
  if (button && !button.disabled) runLearningAction(button.dataset.learningAction);
});
elements.learningDetail.addEventListener("change", (event) => {
  const select = event.target.closest("select[data-learning-field]");
  if (!select) return;
  const option = (learningState.fieldOptions[select.dataset.learningField] || [])
    .find((item) => item.value === select.value);
  const hint = elements.learningDetail.querySelector(`[data-learning-description-for="${select.dataset.learningField}"]`);
  if (hint) hint.textContent = option?.description || "请从列表中选择";
});
elements.learningAddPerson.addEventListener("click", async () => {
  const text = elements.learningNewPrompt.value.trim();
  if (!text) {
    elements.learningAddStatus.textContent = "请输入人物 Prompt 正文";
    return;
  }
  try {
    const created = await learningRequest("/api/learning/person-candidates", {
      method: "POST",
      body: JSON.stringify({ text, source_label: elements.learningNewSource.value.trim() || "用户人工样本" })
    });
    elements.learningNewPrompt.value = "";
    learningState.selectedId = created.candidate_id;
    await loadLearningCandidates();
  } catch (error) {
    elements.learningAddStatus.textContent = error.message;
  }
});

renderSettings();
loadDailySources();
elements.learningMediaDate.value = localDateValue();
setWorkbench(learningState.workbench);

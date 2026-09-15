/**
 * Docker Monitor card — a Lovelace custom card that lists the containers
 * exposed by the `docker_monitor` integration, showing each container's health
 * check status, CPU usage and memory usage.
 *
 * Zero-build vanilla web component (no Lit/bundler). Styles are driven entirely
 * by Home Assistant design tokens so the card follows the active theme and
 * light/dark mode automatically.
 *
 * Containers are discovered from the entity registry: every device that owns
 * `docker_monitor` entities is a container, and its entities (cpu, memory,
 * health) are matched by their integration translation keys — so discovery is
 * language independent.
 *
 * Config:
 *   type: custom:docker-monitor-card
 *   title: Containers          # optional; defaults to a localized "Containers"
 *   devices: [...]             # optional: device ids to show (default: all)
 *   mode: all                  # all | problems (default all)
 *   sort: name                 # name | cpu | memory | health (default name)
 *   columns: 2                 # max columns (1-6, default 2); wraps down on
 *                              #   narrow widths so it stays responsive
 *   cpu_warning: 80            # CPU % at or above which a container is flagged
 *   memory_warning: 80         # memory % (of the limit) at or above which a
 *                              #   container is flagged
 *   show_unavailable: true     # include stopped containers (default true)
 */

const DEFAULT_MODE = "all";
const DEFAULT_SORT = "name";
const DEFAULT_COLUMNS = 2;
const MAX_COLUMNS = 6;
const DEFAULT_CPU_WARNING = 80;
const DEFAULT_MEMORY_WARNING = 80;
const MIN_COLUMN_WIDTH = "240px";
const MODE_OPTIONS = ["all", "problems"];
const SORT_OPTIONS = ["name", "cpu", "memory", "health"];
const UNKNOWN_STATES = ["unavailable", "unknown"];

const HEALTH_ORDER = { unhealthy: 0, stopped: 1, healthy: 2, none: 3 };

const TRANSLATIONS = {
  en: {
    "card.default_title": "Containers",
    "card.filter": "Filter",
    "card.all": "All",
    "card.problems": "Problems",
    "card.cpu": "CPU",
    "card.memory": "Memory",
    "card.health_healthy": "Healthy",
    "card.health_unhealthy": "Unhealthy",
    "card.health_none": "No health check",
    "card.health_stopped": "Stopped",
    "card.empty_all_ok": "All containers OK",
    "card.empty_none": "No containers found",
    "editor.title": "Title",
    "editor.devices": "Containers to show (leave empty for all)",
    "editor.mode": "Display",
    "editor.mode_all": "All containers",
    "editor.mode_problems": "Only containers with problems",
    "editor.sort": "Sort by",
    "editor.sort_name": "Name",
    "editor.sort_cpu": "CPU usage",
    "editor.sort_memory": "Memory usage",
    "editor.sort_health": "Health",
    "editor.columns": "Maximum columns",
    "editor.cpu_warning": "CPU warning threshold",
    "editor.memory_warning": "Memory warning threshold",
    "editor.show_unavailable": "Show stopped containers",
  },
  "pt-BR": {
    "card.default_title": "Contêineres",
    "card.filter": "Filtro",
    "card.all": "Todos",
    "card.problems": "Problemas",
    "card.cpu": "CPU",
    "card.memory": "Memória",
    "card.health_healthy": "Saudável",
    "card.health_unhealthy": "Com problema",
    "card.health_none": "Sem health check",
    "card.health_stopped": "Parado",
    "card.empty_all_ok": "Todos os contêineres OK",
    "card.empty_none": "Nenhum contêiner encontrado",
    "editor.title": "Título",
    "editor.devices": "Contêineres a exibir (vazio = todos)",
    "editor.mode": "Exibição",
    "editor.mode_all": "Todos os contêineres",
    "editor.mode_problems": "Somente contêineres com problema",
    "editor.sort": "Ordenar por",
    "editor.sort_name": "Nome",
    "editor.sort_cpu": "Uso de CPU",
    "editor.sort_memory": "Uso de memória",
    "editor.sort_health": "Saúde",
    "editor.columns": "Máximo de colunas",
    "editor.cpu_warning": "Limite de aviso de CPU",
    "editor.memory_warning": "Limite de aviso de memória",
    "editor.show_unavailable": "Mostrar contêineres parados",
  },
};

const EDITOR_LABEL_KEYS = {
  title: "editor.title",
  devices: "editor.devices",
  mode: "editor.mode",
  sort: "editor.sort",
  columns: "editor.columns",
  cpu_warning: "editor.cpu_warning",
  memory_warning: "editor.memory_warning",
  show_unavailable: "editor.show_unavailable",
};

/** The active HA UI language, or a supported fallback (base lang, then "en"). */
function resolveLang(hass) {
  const lang = (hass && (hass.locale?.language || hass.language || hass.selectedLanguage)) || "en";
  if (TRANSLATIONS[lang]) return lang;
  if (lang.split("-")[0] === "pt") return "pt-BR";
  return "en";
}

/** Translate a dotted key for the active language; English is the fallback. */
function localize(hass, key) {
  const lang = resolveLang(hass);
  return TRANSLATIONS[lang]?.[key] ?? TRANSLATIONS.en[key] ?? key;
}

/** Escape a string for safe interpolation into innerHTML (text and attributes). */
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );
}

/** Parse a numeric sensor state, or null when it carries no value. */
function parseNumber(state) {
  if (!state || UNKNOWN_STATES.includes(state.state)) return null;
  const value = Number(state.state);
  return Number.isFinite(value) ? value : null;
}

/** Validate an optional percentage config value, falling back to a default. */
function percentage(value, fallback, name) {
  if (value == null) return fallback;
  if (typeof value !== "number" || value < 0 || value > 100) {
    throw new Error(`docker-monitor-card: "${name}" must be a number between 0 and 100`);
  }
  return value;
}

/** Format a memory amount in MB as a compact string with a unit. */
function formatMemory(megabytes) {
  if (megabytes === null) return "—";
  if (megabytes >= 1024) return `${(megabytes / 1024).toFixed(2)} GB`;
  return `${megabytes >= 100 ? Math.round(megabytes) : megabytes.toFixed(1)} MB`;
}

/** Format a CPU percentage as a compact string. */
function formatCpu(percent) {
  if (percent === null) return "—";
  return `${percent >= 100 ? Math.round(percent) : percent.toFixed(1)}%`;
}

class DockerMonitorCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._runtimeMode = null;
    this._signature = null;
  }

  static getConfigElement() {
    return document.createElement("docker-monitor-card-editor");
  }

  static getStubConfig() {
    return {
      type: "custom:docker-monitor-card",
      mode: DEFAULT_MODE,
      sort: DEFAULT_SORT,
      columns: DEFAULT_COLUMNS,
      cpu_warning: DEFAULT_CPU_WARNING,
      memory_warning: DEFAULT_MEMORY_WARNING,
      show_unavailable: true,
    };
  }

  setConfig(config) {
    const mode = config.mode ?? DEFAULT_MODE;
    if (!MODE_OPTIONS.includes(mode)) {
      throw new Error(`docker-monitor-card: "mode" must be one of ${MODE_OPTIONS.join(", ")}`);
    }
    const sort = config.sort ?? DEFAULT_SORT;
    if (!SORT_OPTIONS.includes(sort)) {
      throw new Error(`docker-monitor-card: "sort" must be one of ${SORT_OPTIONS.join(", ")}`);
    }
    const columns = Number.parseInt(config.columns, 10);
    const devices =
      Array.isArray(config.devices) && config.devices.length ? config.devices.slice() : null;
    this._config = {
      title: config.title ?? null,
      mode,
      sort,
      columns: Number.isFinite(columns) ? Math.min(MAX_COLUMNS, Math.max(1, columns)) : DEFAULT_COLUMNS,
      cpuWarning: percentage(config.cpu_warning, DEFAULT_CPU_WARNING, "cpu_warning"),
      memoryWarning: percentage(config.memory_warning, DEFAULT_MEMORY_WARNING, "memory_warning"),
      showUnavailable: config.show_unavailable ?? true,
      devices,
    };
    this._runtimeMode = null;
    this._signature = null;
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 4;
  }

  getGridOptions() {
    return { min_columns: 6, min_rows: 3 };
  }

  _effectiveMode() {
    return this._runtimeMode ?? this._config.mode;
  }

  /**
   * Discover containers from the entity registry.
   *
   * Every docker_monitor device is a container; its entities are matched by
   * their integration translation keys (cpu, memory, health).
   */
  _collect() {
    const hass = this._hass;
    const entities = hass.entities || {};
    const devices = hass.devices || {};

    const byDevice = {};
    for (const entry of Object.values(entities)) {
      if (entry.platform !== "docker_monitor" || !entry.device_id) continue;
      (byDevice[entry.device_id] ??= []).push(entry);
    }

    const wanted = this._config.devices ? new Set(this._config.devices) : null;
    const items = [];

    for (const [deviceId, list] of Object.entries(byDevice)) {
      if (wanted && !wanted.has(deviceId)) continue;

      const byKey = {};
      for (const entry of list) {
        if (entry.translation_key) byKey[entry.translation_key] = entry.entity_id;
      }
      if (!byKey.cpu) continue;

      const device = devices[deviceId] || {};
      const cpuState = hass.states[byKey.cpu];
      const memoryState = byKey.memory ? hass.states[byKey.memory] : null;
      const healthState = byKey.health ? hass.states[byKey.health] : null;

      const available = Boolean(cpuState) && cpuState.state !== "unavailable";
      const cpu = parseNumber(cpuState);
      const memory = parseNumber(memoryState);
      const memoryLimit = Number(memoryState?.attributes?.memory_limit_mb);
      const memoryPercent =
        memory !== null && Number.isFinite(memoryLimit) && memoryLimit > 0
          ? Math.min(100, (memory / memoryLimit) * 100)
          : null;

      let health = "none";
      if (!available) health = "stopped";
      else if (healthState?.state === "on") health = "unhealthy";
      else if (healthState?.state === "off") health = "healthy";

      const cpuHigh = cpu !== null && cpu >= this._config.cpuWarning;
      const memoryHigh = memoryPercent !== null && memoryPercent >= this._config.memoryWarning;

      items.push({
        deviceId,
        moreInfoEntity: byKey.cpu,
        name: device.name_by_user || device.name || cpuState?.attributes?.friendly_name || byKey.cpu,
        image: device.sw_version || "",
        available,
        health,
        cpu,
        cpuHigh,
        memory,
        memoryPercent,
        memoryHigh,
        problem: !available || health === "unhealthy" || cpuHigh || memoryHigh,
      });
    }

    const filtered = this._config.showUnavailable ? items : items.filter((i) => i.available);
    const collator = new Intl.Collator(undefined, { sensitivity: "base", numeric: true });
    filtered.sort((a, b) => {
      if (a.available !== b.available) return a.available ? -1 : 1;
      switch (this._config.sort) {
        case "cpu":
          return (b.cpu ?? -1) - (a.cpu ?? -1) || collator.compare(a.name, b.name);
        case "memory":
          return (b.memory ?? -1) - (a.memory ?? -1) || collator.compare(a.name, b.name);
        case "health":
          return HEALTH_ORDER[a.health] - HEALTH_ORDER[b.health] || collator.compare(a.name, b.name);
        default:
          return collator.compare(a.name, b.name);
      }
    });
    return filtered;
  }

  _healthColor(item) {
    if (!item.available) return "var(--secondary-text-color)";
    if (item.health === "unhealthy") return "var(--error-color)";
    if (item.health === "healthy") return "var(--success-color)";
    return "var(--primary-color)";
  }

  _metricColor(high) {
    return high ? "var(--warning-color)" : "var(--primary-color)";
  }

  _render() {
    if (!this._hass) return;
    const hass = this._hass;
    const t = (key) => localize(hass, key);
    const lang = resolveLang(hass);
    const mode = this._effectiveMode();
    const title = this._config.title ?? t("card.default_title");
    const items = this._collect();
    const shown = mode === "problems" ? items.filter((i) => i.problem) : items;

    const signature = JSON.stringify([
      lang,
      mode,
      title,
      this._config.sort,
      this._config.columns,
      shown.map((i) => [i.deviceId, i.name, i.image, i.health, i.cpu, i.memory, i.memoryPercent, i.cpuHigh, i.memoryHigh]),
    ]);
    if (signature === this._signature) return;
    this._signature = signature;

    const rows = shown
      .map((item) => {
        const healthColor = this._healthColor(item);
        const cpuColor = this._metricColor(item.cpuHigh);
        const memoryColor = this._metricColor(item.memoryHigh);
        const cpuWidth = item.cpu === null ? 0 : Math.max(0, Math.min(100, item.cpu));
        const memoryWidth = item.memoryPercent ?? 0;
        const tooltip = item.image ? `${item.name} · ${item.image}` : item.name;
        return `
          <div class="item ${item.available ? "" : "is-stopped"}" data-entity="${esc(item.moreInfoEntity)}" title="${esc(tooltip)}">
            <div class="head">
              <div class="badge" style="color:${healthColor};background:color-mix(in srgb, ${healthColor} 18%, transparent)">
                <ha-icon icon="mdi:docker"></ha-icon>
              </div>
              <div class="name">${esc(item.name)}</div>
              <div class="health" style="color:${healthColor}">${esc(t(`card.health_${item.health}`))}</div>
            </div>
            <div class="metric">
              <span class="label">${esc(t("card.cpu"))}</span>
              <div class="bar"><div class="fill" style="width:${cpuWidth}%;background:${cpuColor}"></div></div>
              <span class="value" style="color:${cpuColor}">${esc(formatCpu(item.cpu))}</span>
            </div>
            <div class="metric">
              <span class="label">${esc(t("card.memory"))}</span>
              <div class="bar"><div class="fill" style="width:${memoryWidth}%;background:${memoryColor}"></div></div>
              <span class="value" style="color:${memoryColor}">${esc(formatMemory(item.memory))}</span>
            </div>
          </div>`;
      })
      .join("");

    const empty =
      mode === "problems"
        ? `<div class="empty"><ha-icon icon="mdi:check-circle-outline"></ha-icon><span>${esc(t("card.empty_all_ok"))}</span></div>`
        : `<div class="empty"><ha-icon icon="mdi:docker"></ha-icon><span>${esc(t("card.empty_none"))}</span></div>`;

    this.shadowRoot.innerHTML = `
      <style>${DockerMonitorCard.styles}</style>
      <ha-card>
        <div class="header">
          <div class="title">${esc(title)}</div>
          <div class="toggle" role="group" aria-label="${esc(t("card.filter"))}">
            <button data-mode="all" class="${mode === "all" ? "active" : ""}">${esc(t("card.all"))}</button>
            <button data-mode="problems" class="${mode === "problems" ? "active" : ""}">${esc(t("card.problems"))}</button>
          </div>
        </div>
        <div class="grid" style="--cols:${this._config.columns}">${shown.length ? rows : empty}</div>
      </ha-card>`;

    this.shadowRoot.querySelectorAll("[data-mode]").forEach((button) => {
      button.addEventListener("click", () => {
        this._runtimeMode = button.dataset.mode;
        this._signature = null;
        this._render();
      });
    });

    this.shadowRoot.querySelectorAll(".item").forEach((item) => {
      item.addEventListener("click", () => this._showMore(item.dataset.entity));
    });
  }

  /** Open the more-info dialog for an entity (standard HA behaviour). */
  _showMore(entityId) {
    if (!entityId) return;
    this.dispatchEvent(
      new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true })
    );
  }

  static get styles() {
    return `
      :host { display: block; }
      ha-card { padding: 12px 16px 16px; }
      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 12px;
        flex-wrap: wrap;
      }
      .title {
        font-size: 1.25rem;
        font-weight: 500;
        color: var(--primary-text-color);
        line-height: 1.4;
      }
      .toggle {
        display: inline-flex;
        border: 1px solid var(--divider-color, rgba(0,0,0,.12));
        border-radius: 999px;
        overflow: hidden;
      }
      .toggle button {
        appearance: none;
        border: 0;
        background: transparent;
        color: var(--secondary-text-color);
        font: inherit;
        font-size: 0.8125rem;
        padding: 4px 14px;
        cursor: pointer;
      }
      .toggle button.active {
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
      }
      .grid {
        --cols: 1;
        --gap: 12px;
        display: grid;
        gap: var(--gap);
        grid-template-columns: repeat(
          auto-fill,
          minmax(max(${MIN_COLUMN_WIDTH}, calc((100% - (var(--cols) - 1) * var(--gap)) / var(--cols))), 1fr)
        );
      }
      .item {
        display: flex;
        flex-direction: column;
        gap: 8px;
        cursor: pointer;
        padding: 12px 14px;
        box-sizing: border-box;
        border-radius: 12px;
        background: var(--ha-card-background, var(--card-background-color, #fff));
        border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
        transition: background .2s ease, border-color .2s ease;
      }
      .item:hover {
        background: var(--secondary-background-color);
        border-color: var(--primary-color);
      }
      .item.is-stopped { opacity: 0.55; }
      .head {
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 0;
      }
      .badge {
        flex: 0 0 auto;
        width: 34px;
        height: 34px;
        border-radius: 10px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
      }
      .badge ha-icon { --mdc-icon-size: 20px; }
      .name {
        flex: 1 1 auto;
        min-width: 0;
        color: var(--primary-text-color);
        font-size: 1rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .health {
        flex: 0 0 auto;
        font-size: 0.8125rem;
        font-weight: 500;
        white-space: nowrap;
      }
      .metric {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .label {
        flex: 0 0 52px;
        color: var(--secondary-text-color);
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.02em;
      }
      .bar {
        flex: 1 1 auto;
        height: 6px;
        border-radius: 3px;
        background: var(--divider-color, rgba(0,0,0,.1));
        overflow: hidden;
      }
      .fill {
        height: 100%;
        border-radius: 3px;
        transition: width .3s ease;
      }
      .value {
        flex: 0 0 68px;
        text-align: right;
        font-size: 0.8125rem;
        font-weight: 600;
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
      }
      .empty {
        grid-column: 1 / -1;
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--secondary-text-color);
        padding: 16px 4px;
      }
    `;
  }
}

class DockerMonitorCardEditor extends HTMLElement {
  constructor() {
    super();
    this._config = {};
    this._hass = null;
  }

  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _schema() {
    const t = (key) => localize(this._hass, key);
    return [
      { name: "title", selector: { text: {} } },
      {
        name: "devices",
        selector: {
          device: {
            multiple: true,
            filter: { integration: "docker_monitor" },
          },
        },
      },
      {
        name: "mode",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "all", label: t("editor.mode_all") },
              { value: "problems", label: t("editor.mode_problems") },
            ],
          },
        },
      },
      {
        name: "sort",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "name", label: t("editor.sort_name") },
              { value: "cpu", label: t("editor.sort_cpu") },
              { value: "memory", label: t("editor.sort_memory") },
              { value: "health", label: t("editor.sort_health") },
            ],
          },
        },
      },
      {
        name: "columns",
        selector: { number: { min: 1, max: MAX_COLUMNS, mode: "box" } },
      },
      {
        name: "cpu_warning",
        selector: { number: { min: 0, max: 100, mode: "box", unit_of_measurement: "%" } },
      },
      {
        name: "memory_warning",
        selector: { number: { min: 0, max: 100, mode: "box", unit_of_measurement: "%" } },
      },
      { name: "show_unavailable", selector: { boolean: {} } },
    ];
  }

  _labels(schema) {
    return localize(this._hass, EDITOR_LABEL_KEYS[schema.name] ?? schema.name);
  }

  _render() {
    if (!this._hass) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (schema) => this._labels(schema);
      this._form.addEventListener("value-changed", (ev) => {
        // Spread the stored config first so keys outside the form schema
        // survive an editor round-trip; drop cleared fields so an empty title
        // falls back to the localized default instead of freezing blank.
        const config = { type: "custom:docker-monitor-card", ...this._config, ...ev.detail.value };
        for (const [key, value] of Object.entries(config)) {
          if (value === "" || value == null) delete config[key];
        }
        this.dispatchEvent(
          new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true })
        );
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = this._schema();
    this._form.data = {
      title: this._config.title ?? "",
      devices: this._config.devices ?? [],
      mode: this._config.mode ?? DEFAULT_MODE,
      sort: this._config.sort ?? DEFAULT_SORT,
      columns: this._config.columns ?? DEFAULT_COLUMNS,
      cpu_warning: this._config.cpu_warning ?? DEFAULT_CPU_WARNING,
      memory_warning: this._config.memory_warning ?? DEFAULT_MEMORY_WARNING,
      show_unavailable: this._config.show_unavailable ?? true,
    };
  }
}

// The module runs once per URL it is served from, and the card URL carries the
// integration version. Upgrading the integration without restarting Home
// Assistant leaves the previous version's URL registered alongside the new one,
// so the module is evaluated twice. Without this guard the second run throws on
// the already-taken tag name and registers a duplicate card picker entry.
if (!customElements.get("docker-monitor-card")) {
  customElements.define("docker-monitor-card", DockerMonitorCard);
  customElements.define("docker-monitor-card-editor", DockerMonitorCardEditor);

  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "docker-monitor-card",
    name: "Docker Monitor Card",
    description: "Lists Docker containers with their health check status, CPU and memory usage.",
    preview: true,
    documentationURL: "https://github.com/roquerodrigo/ha-docker-monitor",
  });

  // eslint-disable-next-line no-console
  console.info("%c docker-monitor-card ", "background:#2496ED;color:#fff;border-radius:3px", "loaded");
}

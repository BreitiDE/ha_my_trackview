/* My TrackView – Frontend */
(() => {
"use strict";

// ------------------------------------------------------------------ Zustand
const S = {
  info: null, lang: "de", tz: "UTC", settings: {}, stats: null,
  route: "trips",
  list: {
    trips: { page: 1, size: null, sort: "start", order: "desc" },
    unassigned: { page: 1, size: null, sort: "start", order: "desc" },
    trash: { page: 1, size: null, sort: "deleted", order: "desc" },
  },
  rows: [], total: 0,
  sel: new Set(), selScope: null,
  wasImporting: false, pollTimer: null, logTimer: null, logLast: 0,
};
const PAGE_SIZES = [10, 25, 50, 100, 0];

// ------------------------------------------------------------------ Helfer
const $ = (q, el = document) => el.querySelector(q);
const $$ = (q, el = document) => Array.from(el.querySelectorAll(q));
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function t(key, vars) {
  const d = window.I18N[S.lang] || window.I18N.de;
  let s = d[key] ?? window.I18N.en[key] ?? key;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(v);
  return s;
}

async function api(path, opts = {}) {
  const o = { headers: {}, ...opts };
  if (o.body && typeof o.body !== "string") {
    o.body = JSON.stringify(o.body);
    o.headers["Content-Type"] = "application/json";
  }
  const r = await fetch(path, o);
  let data = null;
  try { data = await r.json(); } catch (_) { /* leer */ }
  if (!r.ok) {
    const err = new Error((data && (data.detail || data.error)) || `HTTP ${r.status}`);
    err.code = data && data.error; err.data = data; err.status = r.status;
    throw err;
  }
  return data;
}

function errText(e) {
  if (e.code === "no_home") return t("err_no_home");
  if (e.code === "file_missing") return t("err_file_missing", { d: (e.data && e.data.detail) || "" });
  if (e.code === "import_running") return t("imp_running");
  return t("err_generic", { e: e.message });
}

const ICON = {
  refresh: '<path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/>',
  sync: '<path d="M3 12a9 9 0 0 1 15.36-6.36L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15.36 6.36L3 16"/><path d="M3 21v-5h5"/>',
  map: '<path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2z"/><path d="M9 4v14M15 6v14"/>',
  file: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/>',
  pdf: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/><path d="M9 15h6M9 18h4"/>',
  trash: '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  up: '<path d="M12 19V5M5 12l7-7 7 7"/>',
  down: '<path d="M12 5v14M19 12l-7 7-7-7"/>',
  scissors: '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.12 15.88M14.47 14.48 20 20M8.12 8.12 12 12"/>',
  restore: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
  merge: '<path d="M8 3v5a4 4 0 0 0 4 4h0a4 4 0 0 1 4 4v5"/><path d="M16 3v5a4 4 0 0 1-4 4"/>',
  route: '<circle cx="6" cy="19" r="2"/><circle cx="18" cy="5" r="2"/><path d="M8 19h7.5a3.5 3.5 0 0 0 0-7h-7a3.5 3.5 0 0 1 0-7H16"/>',
  home: '<path d="m3 11 9-8 9 8"/><path d="M5 10v10h14V10"/>',
  left: '<path d="m15 18-6-6 6-6"/>', right: '<path d="m9 18 6-6-6-6"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  db: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
};
const ic = (n, cls = "i") => `<svg class="${cls}" viewBox="0 0 24 24">${ICON[n] || ""}</svg>`;

// ---- Formatierung (Zeitzone von Home Assistant)
function dtParts(ts) {
  const d = new Date(ts * 1000);
  const f = new Intl.DateTimeFormat("en-GB", { timeZone: S.tz, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", weekday: "short", hourCycle: "h23" });
  const p = {};
  for (const x of f.formatToParts(d)) p[x.type] = x.value;
  return p;
}
const WD = { de: { Mon: "Mo", Tue: "Di", Wed: "Mi", Thu: "Do", Fri: "Fr", Sat: "Sa", Sun: "So" } };
function fmtDate(ts, withWd = false) {
  const p = dtParts(ts);
  const wd = withWd ? ((WD[S.lang] || {})[p.weekday] || p.weekday) + " " : "";
  return S.lang === "de" ? `${wd}${p.day}.${p.month}.${p.year}` : `${wd}${p.year}-${p.month}-${p.day}`;
}
function fmtShortDate(ts) { const p = dtParts(ts); return S.lang === "de" ? `${p.day}.${p.month}.` : `${p.month}-${p.day}`; }
function fmtTime(ts) { const p = dtParts(ts); return `${p.hour}:${p.minute}`; }
function sameDay(a, b) { return fmtDate(a) === fmtDate(b); }
function fmtEnd(r) { return sameDay(r.start_ts, r.end_ts) ? fmtTime(r.end_ts) : `${fmtShortDate(r.end_ts)} ${fmtTime(r.end_ts)}`; }
function fmtDur(s) {
  s = Math.max(0, Math.round(s));
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  if (d) return `${d} ${t("unit_d")} ${h} ${t("unit_h")}`;
  if (h) return `${h} ${t("unit_h")} ${String(m).padStart(2, "0")} ${t("unit_min")}`;
  return `${m} ${t("unit_min")}`;
}
function fmtNum(v, digits = 1) {
  return new Intl.NumberFormat(S.lang === "de" ? "de-DE" : "en-GB", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(v);
}
function distVal(m) { return S.settings.distance_unit === "mi" ? m / 1609.344 : m / 1000; }
function fmtDist(m, unit = true) { return fmtNum(distVal(m)) + (unit ? " " + (S.settings.distance_unit || "km") : ""); }
function fmtBytes(b) {
  if (b > 1e9) return fmtNum(b / 1e9) + " GB";
  if (b > 1e6) return fmtNum(b / 1e6) + " MB";
  return fmtNum(b / 1e3, 0) + " kB";
}
function fmtAgo(ts) {
  if (!ts) return t("s_never");
  const now = Date.now() / 1000;
  if (sameDay(ts, now)) return fmtTime(ts);
  return `${fmtShortDate(ts)} ${fmtTime(ts)}`;
}

// ---- Toasts & Dialoge
function toast(msg, kind = "") {
  const el = document.createElement("div");
  el.className = "toast " + kind;
  el.textContent = msg;
  $("#toasts").appendChild(el);
  setTimeout(() => el.remove(), kind === "err" ? 9000 : 4500);
}

function modal(html, { cls = "", onClose } = {}) {
  const bg = document.createElement("div");
  bg.className = "modal-bg";
  bg.innerHTML = `<div class="modal ${cls}" role="dialog" aria-modal="true">${html}</div>`;
  document.body.appendChild(bg);
  const close = () => {
    document.removeEventListener("keydown", onKey);
    bg.remove();
    if (onClose) onClose();
  };
  const onKey = (e) => { if (e.key === "Escape") close(); };
  document.addEventListener("keydown", onKey);
  bg.addEventListener("mousedown", (e) => { if (e.target === bg) close(); });
  return { el: $(".modal", bg), close };
}

function confirmDlg(text, { ok = t("ok"), danger = false } = {}) {
  return new Promise((resolve) => {
    let done = false;
    const m = modal(`<p>${esc(text)}</p><div class="btns"><button class="btn" data-a="no">${t("cancel")}</button>
      <button class="btn ${danger ? "danger solid" : "primary"}" data-a="yes">${esc(ok)}</button></div>`,
    { onClose: () => { if (!done) resolve(false); } });
    m.el.addEventListener("click", (e) => {
      const a = e.target.closest("[data-a]");
      if (!a) return;
      done = true; m.close(); resolve(a.dataset.a === "yes");
    });
    $("[data-a=yes]", m.el).focus();
  });
}

// ------------------------------------------------------------------ Kopf
const ROUTES = ["trips", "unassigned", "trash", "settings", "log", "help"];

function renderMenu() {
  const st = S.stats || {};
  const badge = (n) => (n ? `<span class="badge">${n}</span>` : "");
  const items = [
    ["trips", t("nav_trips"), ""],
    ["unassigned", t("nav_unassigned"), badge(st.unassigned)],
    ["trash", t("nav_trash"), badge(st.trash)],
    ["settings", t("nav_settings"), ""],
    ["log", t("nav_log"), ""],
    ["help", t("nav_help"), ""],
  ];
  $("#menu").innerHTML = items.map(([r, l, b]) => `<a href="#/${r}" class="${S.route === r ? "active" : ""}">${l}${b}</a>`).join("");
  let dot = "ok", txt = S.settings.import_interval_min > 0 ? t("st_auto") : t("st_manual");
  if (st.import_status && st.import_status.running) { dot = "warn pulse"; txt = t("st_importing"); }
  else if (st.last_result && st.last_result.error) { dot = "err"; txt = t("st_error"); }
  else if (st.tiles_online === false) { dot = "warn"; txt = t("st_offline"); }
  $("#topStatus").innerHTML = `<span class="dot ${dot}"></span>${esc(txt)}<span class="muted">· v${esc(S.info.version)}</span>`;
}

// ------------------------------------------------------------------ Stats
async function refreshStats() {
  try {
    S.stats = await api("api/stats");
  } catch (e) { return; }
  const running = S.stats.import_status && S.stats.import_status.running;
  if (S.wasImporting && !running) onImportFinished();
  S.wasImporting = running;
  renderMenu();
  if (["trips", "unassigned", "trash"].includes(S.route)) { renderStats(); renderNotices(); }
  schedulePoll(running ? 1500 : 20000);
}
function schedulePoll(ms) {
  clearTimeout(S.pollTimer);
  S.pollTimer = setTimeout(refreshStats, ms);
}

function onImportFinished() {
  const r = S.stats.last_result || {};
  if (r.error) toast(errText({ code: r.error, data: { detail: r.detail }, message: r.detail || r.error }), "err");
  else {
    toast(t("imp_done", { ins: r.inserted ?? 0, upd: r.updated ?? 0 }), "ok");
    if (r.overlap) toast(t("imp_overlap", { n: r.overlap }));
  }
  if (["trips", "unassigned", "trash"].includes(S.route)) loadList();
}

function renderStats() {
  const el = $("#stats");
  if (!el || !S.stats) return;
  const s = S.stats;
  const run = s.running;
  const lr = s.last_result || {};
  const tiles = [
    [t("s_trips"), s.trips, s.last_start ? t("s_trips_sub", { date: fmtDate(s.last_start) }) : t("s_trips_none")],
    [t("s_running"), run ? t("s_running_yes") : t("s_running_no"), run ? t("s_running_since", { date: `${fmtShortDate(run.start_ts)} ${fmtTime(run.start_ts)}` }) : t("s_home"), !!run],
    [t("s_distance"), fmtDist(s.distance_m), s.trips ? t("s_avg", { v: fmtDist(s.distance_m / s.trips) }) : "–"],
    [t("s_driving"), fmtDur(s.driving_s), t("s_stages", { n: s.stages })],
    [t("s_unassigned"), s.unassigned, s.unassigned ? t("s_unassigned_sub") : t("s_unassigned_none"), s.unassigned > 0],
    [t("s_last_import"), fmtAgo(s.last_import), lr.error ? t("s_failed") : (s.last_import ? t("s_new", { n: lr.inserted ?? 0 }) : "–")],
  ];
  el.innerHTML = tiles.map(([l, v, sub, attn]) => `<div class="stat ${attn ? "attn" : ""}"><div class="lbl">${esc(l)}</div><div class="val">${esc(v)}</div><div class="sub">${esc(sub)}</div></div>`).join("");
}

function renderNotices() {
  const el = $("#notices");
  if (!el || !S.stats) return;
  const s = S.stats;
  const out = [];
  if (!s.configured) out.push(`<div class="notice info"><div class="grow">${t("n_setup")}</div><a class="btn sm" href="#/settings">${t("n_setup_btn")}</a></div>`);
  else if (!s.file_exists) out.push(`<div class="notice err"><div class="grow">${esc(t("n_file", { p: S.settings.gps_file }))}</div><a class="btn sm" href="#/settings">${t("n_setup_btn")}</a></div>`);
  if (s.params_changed && s.trips + s.unassigned > 0) out.push(`<div class="notice"><div class="grow">${t("n_params")}</div><button class="btn sm" data-act="reimport">${t("n_params_btn")}</button></div>`);
  el.innerHTML = out.join("");
}

// ------------------------------------------------------------------ Listen
function shell(scope) {
  const intro = { unassigned: t("un_intro"), trash: t("trash_intro") }[scope] || "";
  const title = { trips: [t("trips_title"), t("trips_sub")], unassigned: [t("un_title"), t("un_sub")], trash: [t("trash_title"), t("trash_sub")] }[scope];
  const ls = S.list[scope];
  return `
  <div class="toolbar">
    <button class="btn primary lg" data-act="import">${ic("refresh")}${t("btn_import_now")}</button>
    <button class="btn lg" data-act="reimport">${ic("sync")}${t("btn_reimport")}</button>
    <div class="filebox">${ic("file")}<span class="hide-sm">${t("gps_file")}</span><code title="${esc(S.settings.gps_file)}">${esc(S.settings.gps_file)}</code><a href="#/settings">${t("change")}</a></div>
  </div>
  <div id="notices"></div>
  <div class="stats" id="stats"></div>
  <section class="panel">
    <div class="panel-head">
      <h2>${title[0]}</h2><span class="sub">${title[1]}</span>
      <div class="right">
        ${scope === "trash" ? `<button class="btn sm danger" data-act="purge-all">${ic("trash")}${t("trash_empty_btn")}</button>` : ""}
        <label class="muted" for="pageSize">${t("per_page")}</label>
        <select id="pageSize">${PAGE_SIZES.map((n) => `<option value="${n}" ${n === ls.size ? "selected" : ""}>${n || t("all")}</option>`).join("")}</select>
      </div>
    </div>
    ${intro ? `<p class="intro">${intro}</p>` : ""}
    <div id="selbar"></div>
    <div class="table-wrap"><table class="list" id="list"></table></div>
    <div class="pager" id="pager"></div>
  </section>`;
}

async function viewList(scope) {
  const ls = S.list[scope];
  if (ls.size === null) {
    let saved = null;
    try { saved = localStorage.getItem("tv_pagesize"); } catch (_) { /* privat */ }
    ls.size = saved !== null && PAGE_SIZES.includes(+saved) ? +saved : (PAGE_SIZES.includes(+S.settings.page_size) ? +S.settings.page_size : 25);
  }
  if (S.selScope !== scope) { S.sel.clear(); S.selScope = scope; }
  $("#view").innerHTML = shell(scope);
  renderStats(); renderNotices();
  $("#pageSize").addEventListener("change", (e) => {
    const v = +e.target.value;
    for (const k of Object.keys(S.list)) { S.list[k].size = v; S.list[k].page = 1; }
    try { localStorage.setItem("tv_pagesize", String(v)); } catch (_) { /* privat */ }
    loadList();
  });
  await loadList();
}

async function loadList() {
  const scope = S.route;
  const ls = S.list[scope];
  if (!ls) return;
  let data;
  try {
    data = await api(`api/tracks?scope=${scope}&page=${ls.page}&size=${ls.size}&sort=${ls.sort}&order=${ls.order}`);
  } catch (e) { toast(errText(e), "err"); return; }
  if (S.route !== scope) return;
  if (data.rows.length === 0 && ls.page > 1 && data.total > 0) { ls.page = Math.max(1, Math.ceil(data.total / (ls.size || data.total))); return loadList(); }
  S.rows = data.rows; S.total = data.total;
  renderTable(scope);
  renderPager(scope);
  renderSelbar(scope);
}

function sortTh(scope, key, label, cls = "") {
  const ls = S.list[scope];
  const on = ls.sort === key;
  return `<th class="sortable ${cls}" data-sort="${key}">${label}${on ? `<span class="arrow">${ls.order === "asc" ? "▲" : "▼"}</span>` : ""}</th>`;
}

function thumb(r) {
  const v = encodeURIComponent(`${r.updated_at}-${r.color_eff}`);
  return `<button class="thumb-btn" data-view="${r.id}" title="${esc(t("act_view"))}"><img loading="lazy" alt="" src="api/tracks/${r.id}/thumb.png?v=${v}"></button>`;
}

function dateCell(r) {
  let sub = "";
  if (r.name) sub = `<div class="t-sub">${esc(r.name)}</div>`;
  const pill = r.status === "running" ? ` <span class="pill run"><span class="dot ok pulse"></span>${t("running")}</span>` : "";
  return `<div class="t-main">${esc(fmtDate(r.start_ts, true))}${pill}</div>${sub}`;
}

function renderTable(scope) {
  const tbl = $("#list");
  const allSel = S.rows.length > 0 && S.rows.every((r) => S.sel.has(r.id));
  const distLabel = S.settings.distance_unit === "mi" ? t("col_distance_mi") : t("col_distance");
  let head = `<th class="cb"><input type="checkbox" id="selAll" ${allSel ? "checked" : ""} aria-label="all"></th><th></th>`;
  if (scope === "trips") {
    head += sortTh(scope, "start", t("col_date")) + `<th class="num">${t("col_start")}</th><th class="num">${t("col_end")}</th>` +
      sortTh(scope, "duration", t("col_duration"), "num") + sortTh(scope, "driving", t("col_driving"), "num hide-sm") +
      sortTh(scope, "distance", distLabel, "num") + `<th class="num hide-sm">${t("col_stages")}</th><th class="num">${t("col_actions")}</th>`;
  } else if (scope === "unassigned") {
    head += `<th>${t("col_reason")}</th>` + sortTh(scope, "start", t("col_date")) + `<th class="num">${t("col_start")}</th><th class="num">${t("col_end")}</th>` +
      sortTh(scope, "duration", t("col_duration"), "num") + sortTh(scope, "distance", distLabel, "num") +
      `<th class="num hide-sm">${t("col_stages")}</th><th class="num">${t("col_actions")}</th>`;
  } else {
    head += sortTh(scope, "start", t("col_date")) + `<th>${t("col_status")}</th><th class="num">${t("col_end")}</th>` +
      sortTh(scope, "distance", distLabel, "num") + sortTh(scope, "deleted", t("col_deleted"), "num") + `<th class="num">${t("col_actions")}</th>`;
  }
  const cols = (head.match(/<th/g) || []).length;
  let body = "";
  if (!S.rows.length) {
    const msg = { trips: `${t("empty_trips")}<br><span class="muted">${t("empty_trips_hint")}</span>`, unassigned: t("empty_unassigned"), trash: t("empty_trash") }[scope];
    body = `<tr><td colspan="${cols}" class="empty">${ic(scope === "trash" ? "trash" : "route")}${msg}</td></tr>`;
  }
  for (const r of S.rows) {
    const sel = S.sel.has(r.id);
    let tr = `<td class="cb"><input type="checkbox" data-sel="${r.id}" ${sel ? "checked" : ""}></td><td class="thumb">${thumb(r)}</td>`;
    if (scope === "trips") {
      tr += `<td>${dateCell(r)}</td><td class="num">${fmtTime(r.start_ts)}</td><td class="num">${esc(fmtEnd(r))}</td>
        <td class="num">${fmtDur(r.duration_s)}</td><td class="num hide-sm">${fmtDur(r.driving_s)}</td>
        <td class="num"><b>${fmtDist(r.distance_m, false)}</b></td><td class="num hide-sm">${r.stage_count}</td>
        <td class="actions"><button class="icon-btn" data-pdf="${r.id}" title="${t("act_pdf")}">${ic("pdf")}</button><button class="icon-btn danger" data-del="${r.id}" title="${t("act_delete")}">${ic("trash")}</button></td>`;
    } else if (scope === "unassigned") {
      const reason = r.status === "running" ? t("running") : t("reason_" + (r.reason || "manual"));
      tr += `<td><span class="pill warn">${esc(reason)}</span></td><td>${dateCell(r)}</td><td class="num">${fmtTime(r.start_ts)}</td><td class="num">${esc(fmtEnd(r))}</td>
        <td class="num">${fmtDur(r.duration_s)}</td><td class="num"><b>${fmtDist(r.distance_m, false)}</b></td><td class="num hide-sm">${r.stage_count}</td>
        <td class="actions">
          <button class="icon-btn" data-assign="${r.id}" title="${t("act_assign")}">${ic("check")}</button>
          <button class="icon-btn" data-mprev="${r.id}" title="${t("act_merge_prev")}">${ic("up")}</button>
          <button class="icon-btn" data-mnext="${r.id}" title="${t("act_merge_next")}">${ic("down")}</button>
          ${r.stage_count > 1 ? `<button class="icon-btn" data-split="${r.id}" title="${t("act_split")}">${ic("scissors")}</button>` : ""}
          <button class="icon-btn danger" data-del="${r.id}" title="${t("act_delete")}">${ic("trash")}</button></td>`;
    } else {
      const st = r.status === "unassigned" ? t("reason_" + (r.reason || "manual")) : (r.status === "running" ? t("running") : t("v_trip"));
      tr += `<td>${dateCell(r)}<div class="t-sub">${fmtTime(r.start_ts)}</div></td><td><span class="pill">${esc(st)}</span></td><td class="num">${esc(fmtEnd(r))}</td>
        <td class="num"><b>${fmtDist(r.distance_m, false)}</b></td><td class="num">${r.deleted_at ? `${fmtShortDate(r.deleted_at)} ${fmtTime(r.deleted_at)}` : "–"}</td>
        <td class="actions"><button class="icon-btn" data-restore="${r.id}" title="${t("act_restore")}">${ic("restore")}</button><button class="icon-btn danger" data-purge="${r.id}" title="${t("act_purge")}">${ic("x")}</button></td>`;
    }
    body += `<tr class="${sel ? "sel" : ""}">${tr}</tr>`;
  }
  tbl.innerHTML = `<thead><tr>${head}</tr></thead><tbody>${body}</tbody>`;
}

function renderPager(scope) {
  const ls = S.list[scope];
  const el = $("#pager");
  const size = ls.size || S.total || 1;
  const pages = Math.max(1, Math.ceil(S.total / size));
  const a = S.total ? (ls.page - 1) * size + 1 : 0;
  const b = Math.min(S.total, ls.page * size);
  let html = `<span class="info">${S.total ? t("page_info", { a, b, n: S.total }) : t("page_info_empty")}</span>`;
  if (pages > 1) {
    html += `<button data-page="${ls.page - 1}" ${ls.page <= 1 ? "disabled" : ""} aria-label="prev">‹</button>`;
    const nums = new Set([1, pages, ls.page - 1, ls.page, ls.page + 1, ls.page - 2, ls.page + 2].filter((n) => n >= 1 && n <= pages));
    let last = 0;
    for (const n of [...nums].sort((x, y) => x - y)) {
      if (n - last > 1) html += `<span class="muted">…</span>`;
      html += `<button data-page="${n}" class="${n === ls.page ? "cur" : ""}">${n}</button>`;
      last = n;
    }
    html += `<button data-page="${ls.page + 1}" ${ls.page >= pages ? "disabled" : ""} aria-label="next">›</button>`;
  }
  el.innerHTML = html;
}

function renderSelbar(scope) {
  const el = $("#selbar");
  if (!el) return;
  const n = S.sel.size;
  if (!n) { el.innerHTML = ""; return; }
  let btns = "";
  if (scope === "trash") {
    btns = `<button class="btn sm" data-bulk="restore">${ic("restore")}${t("sel_restore")}</button><button class="btn sm danger" data-bulk="purge">${ic("x")}${t("sel_purge")}</button>`;
  } else {
    btns = `<button class="btn sm primary" data-bulk="show">${ic("map")}${t("sel_show")}</button><button class="btn sm" data-bulk="pdf">${ic("pdf")}${t("sel_pdf")}</button>`;
    if (scope === "unassigned") btns += `<button class="btn sm" data-bulk="assign">${ic("check")}${t("sel_assign")}</button>`;
    if (n >= 2) btns += `<button class="btn sm" data-bulk="merge">${ic("merge")}${t("sel_merge")}</button>`;
    btns += `<button class="btn sm danger" data-bulk="delete">${ic("trash")}${t("sel_delete")}</button>`;
  }
  el.innerHTML = `<div class="selbar"><span class="count">${t("sel_count", { n })}</span>${btns}<button class="btn sm" data-bulk="clear">${t("sel_clear")}</button></div>`;
}

// ---- Aktionen
async function doImport(mode = "incremental", restore = false) {
  try {
    await api("api/import", { method: "POST", body: { mode, restore_deleted: restore } });
    toast(t("imp_started"));
    S.wasImporting = true;
    schedulePoll(800);
  } catch (e) { toast(errText(e), "err"); }
}

function reimportDialog(preselect = "reconcile") {
  const m = modal(`<h3>${t("ri_title")}</h3>
    <label class="opt"><input type="radio" name="rm" value="reconcile" ${preselect === "reconcile" ? "checked" : ""}><div><b>${t("ri_reconcile")}</b><div class="d">${t("ri_reconcile_d")}</div>
      <label class="chk" style="margin-top:8px"><input type="checkbox" id="riRestore"> ${t("ri_restore")}</label></div></label>
    <label class="opt"><input type="radio" name="rm" value="rebuild" ${preselect === "rebuild" ? "checked" : ""}><div><b>${t("ri_rebuild")}</b><div class="d">${t("ri_rebuild_d")}</div></div></label>
    <div class="btns"><button class="btn" data-a="no">${t("cancel")}</button><button class="btn primary" data-a="go">${t("start")}</button></div>`);
  m.el.addEventListener("click", async (e) => {
    const a = e.target.closest("[data-a]");
    if (!a) return;
    if (a.dataset.a === "no") return m.close();
    const mode = $("input[name=rm]:checked", m.el).value;
    const restore = $("#riRestore", m.el).checked;
    m.close();
    if (mode === "rebuild" && !(await confirmDlg(t("ri_rebuild_d"), { ok: t("ri_rebuild"), danger: true }))) return;
    doImport(mode, restore);
  });
}

async function bulk(action, ids) {
  ids = ids.map(Number);
  try {
    if (action === "delete") {
      if (!(await confirmDlg(t("confirm_delete", { n: ids.length }), { ok: t("sel_delete"), danger: true }))) return;
      await api("api/tracks/delete", { method: "POST", body: { ids } });
    } else if (action === "restore") {
      await api("api/tracks/restore", { method: "POST", body: { ids } });
    } else if (action === "purge") {
      if (!(await confirmDlg(t("confirm_purge", { n: ids.length }), { ok: t("sel_purge"), danger: true }))) return;
      await api("api/tracks/purge", { method: "POST", body: { ids } });
    } else if (action === "assign") {
      await api("api/tracks/assign", { method: "POST", body: { ids } });
    } else if (action === "merge") {
      if (!(await confirmDlg(t("confirm_merge", { n: ids.length }), { ok: t("sel_merge") }))) return;
      await api("api/tracks/merge", { method: "POST", body: { ids } });
    }
    ids.forEach((i) => S.sel.delete(i));
    toast(t("done"), "ok");
    await loadList();
    refreshStats();
  } catch (e) { toast(errText(e), "err"); }
}

async function mergeNeighbour(id, dir) {
  try {
    const d = await api(`api/tracks/${id}`);
    const other = dir === "prev" ? d.prev_id : d.next_id;
    if (!other) return toast(t("merge_none"));
    await bulk("merge", [id, other]);
  } catch (e) { toast(errText(e), "err"); }
}

async function splitDialog(id) {
  let d;
  try { d = await api(`api/tracks/${id}`); } catch (e) { return toast(errText(e), "err"); }
  const opts = d.stages.slice(1).map((s, i) => `<option value="${i + 1}">${t("v_stage")} ${i + 2} – ${fmtShortDate(s.start_ts)} ${fmtTime(s.start_ts)} (${fmtDist(s.distance_m)})</option>`).join("");
  const m = modal(`<h3>${t("split_title")}</h3><p class="ink2">${esc(fmtDate(d.start_ts, true))} · ${fmtDist(d.distance_m)} · ${d.stage_count} ${t("col_stages")}</p>
    <label>${t("split_text")}</label><br><select id="splitAt" style="margin-top:6px;width:100%">${opts}</select>
    <div class="btns"><button class="btn" data-a="no">${t("cancel")}</button><button class="btn primary" data-a="go">${ic("scissors")}${t("split_btn")}</button></div>`);
  m.el.addEventListener("click", async (e) => {
    const a = e.target.closest("[data-a]");
    if (!a) return;
    if (a.dataset.a === "no") return m.close();
    const stage = +$("#splitAt", m.el).value;
    m.close();
    try {
      await api(`api/tracks/${id}/split`, { method: "POST", body: { stage } });
      toast(t("done"), "ok");
      loadList(); refreshStats();
    } catch (err) { toast(errText(err), "err"); }
  });
}

function pdfUrl(ids, stages = false, color = null) {
  let u = `api/pdf?ids=${ids.join(",")}&stages=${stages ? 1 : 0}&dl=1`;
  if (color) u += `&color=${encodeURIComponent(color)}`;
  return u;
}
function downloadPdf(ids, stages, color) {
  const a = document.createElement("a");
  a.href = pdfUrl(ids, stages, color);
  a.download = "";
  document.body.appendChild(a);
  a.click();
  a.remove();
  toast("PDF …");
}

// globale Klick-Behandlung für Listen
document.addEventListener("click", async (e) => {
  const el = e.target.closest("[data-act],[data-view],[data-pdf],[data-del],[data-restore],[data-purge],[data-assign],[data-mprev],[data-mnext],[data-split],[data-bulk],[data-page],[data-sort]");
  if (!el || el.closest(".modal")) return;
  const d = el.dataset;
  if (d.act === "import") return doImport("incremental");
  if (d.act === "reimport") return reimportDialog(S.stats && S.stats.params_changed ? "rebuild" : "reconcile");
  if (d.act === "purge-all") {
    if (await confirmDlg(t("confirm_purge_all"), { ok: t("trash_empty_btn"), danger: true })) {
      try { await api("api/tracks/purge", { method: "POST", body: { all: true } }); toast(t("done"), "ok"); loadList(); refreshStats(); } catch (err) { toast(errText(err), "err"); }
    }
    return;
  }
  if (d.view) return openViewer([+d.view]);
  if (d.pdf) return downloadPdf([+d.pdf], false, null);
  if (d.del) return bulk("delete", [d.del]);
  if (d.restore) return bulk("restore", [d.restore]);
  if (d.purge) return bulk("purge", [d.purge]);
  if (d.assign) return bulk("assign", [d.assign]);
  if (d.mprev) return mergeNeighbour(+d.mprev, "prev");
  if (d.mnext) return mergeNeighbour(+d.mnext, "next");
  if (d.split) return splitDialog(+d.split);
  if (d.page) { S.list[S.route].page = +d.page; return loadList(); }
  if (d.sort) {
    const ls = S.list[S.route];
    if (ls.sort === d.sort) ls.order = ls.order === "asc" ? "desc" : "asc";
    else { ls.sort = d.sort; ls.order = "desc"; }
    ls.page = 1;
    return loadList();
  }
  if (d.bulk) {
    const ids = [...S.sel];
    if (d.bulk === "clear") { S.sel.clear(); renderTable(S.route); renderSelbar(S.route); return; }
    if (d.bulk === "show") return openViewer(ids);
    if (d.bulk === "pdf") return downloadPdf(ids, false, null);
    return bulk(d.bulk, ids);
  }
});

document.addEventListener("change", (e) => {
  const el = e.target;
  if (el.closest(".modal")) return;
  if (el.dataset.sel) {
    const id = +el.dataset.sel;
    if (el.checked) S.sel.add(id); else S.sel.delete(id);
    el.closest("tr").classList.toggle("sel", el.checked);
    const all = $("#selAll");
    if (all) all.checked = S.rows.length > 0 && S.rows.every((r) => S.sel.has(r.id));
    renderSelbar(S.route);
  } else if (el.id === "selAll") {
    for (const r of S.rows) { if (el.checked) S.sel.add(r.id); else S.sel.delete(r.id); }
    renderTable(S.route); renderSelbar(S.route);
  }
});

// ------------------------------------------------------------------ Kartenansicht
function osmLayer() {
  return L.tileLayer("api/tiles/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>',
  });
}
function paletteColor(i) {
  const p = S.info.palette;
  if (i < p.length) return p[i];
  const h = (i * 0.618033988749895 * 360) % 360;
  return `hsl(${Math.round(h)} 65% 45%)`;
}
const pinIcon = (cls) => L.divIcon({ className: `pin ${cls}`, iconSize: [14, 14] });

function drawTrack(group, geometry, colors) {
  const layers = [];
  geometry.forEach((seg, i) => {
    if (seg.length < 2) return;
    const c = colors[Math.min(i, colors.length - 1)];
    L.polyline(seg, { color: "#ffffff", weight: 7, opacity: 0.75, interactive: false }).addTo(group);
    layers.push(L.polyline(seg, { color: c, weight: 4, opacity: 0.95 }).addTo(group));
  });
  const first = geometry.find((s) => s.length);
  const last = [...geometry].reverse().find((s) => s.length);
  if (first) L.marker(first[0], { icon: pinIcon("start"), interactive: false }).addTo(group);
  if (last) L.marker(last[last.length - 1], { icon: pinIcon("end"), interactive: false }).addTo(group);
  return layers;
}

async function openViewer(ids) {
  ids = ids.map(Number).filter(Boolean);
  if (!ids.length) return;
  const single = ids.length === 1;
  let data;
  try {
    data = single ? await api(`api/tracks/${ids[0]}`) : await api(`api/geometry?ids=${ids.join(",")}`);
  } catch (e) { return toast(errText(e), "err"); }
  let changed = false;
  const m = modal(`<div class="viewer-head"></div><div class="viewer-body"><div class="viewer-map"><div class="map"></div></div><div class="viewer-side"></div></div>`,
    { cls: "viewer", onClose: () => { closed = true; try { map.stop(); map.off(); map.remove(); } catch (_) { /* Animation lief noch */ } if (changed) loadList(); } });
  let closed = false;
  const map = L.map($(".map", m.el), { zoomControl: true, attributionControl: true });
  osmLayer().addTo(map);
  const group = L.featureGroup().addTo(map);

  if (single) {
    const tr = data;
    let color = tr.color_eff;
    let byStage = false;
    const head = $(".viewer-head", m.el);
    const side = $(".viewer-side", m.el);
    const nav = (S.route === "trips" || S.route === "unassigned");
    head.innerHTML = `
      <div>
        <div class="title">${ic("route")}${t("v_trip")} ${esc(fmtDate(tr.start_ts, true))}${tr.status === "running" ? ` <span class="pill run"><span class="dot ok pulse"></span>${t("running")}</span>` : ""}</div>
        <div class="facts">
          <span>${t("col_date")} <b>${esc(fmtDate(tr.start_ts))}</b></span>
          <span>${t("col_start")} <b>${fmtTime(tr.start_ts)}</b></span>
          <span>${t("col_end")} <b>${esc(sameDay(tr.start_ts, tr.end_ts) ? fmtTime(tr.end_ts) : fmtDate(tr.end_ts) + " " + fmtTime(tr.end_ts))}</b></span>
          <span>${t("col_duration")} <b>${fmtDur(tr.duration_s)}</b></span>
          <span>${t("col_driving")} <b>${fmtDur(tr.driving_s)}</b></span>
          <span>${S.settings.distance_unit === "mi" ? t("col_distance_mi") : t("col_distance")} <b>${fmtDist(tr.distance_m)}</b></span>
          <span>${t("col_stages")} <b>${tr.stage_count}</b></span>
        </div>
      </div>
      <div class="tools">
        <div class="swatches" id="sw">${[S.settings.default_color, ...S.info.palette.slice(1)].map((c) => `<button class="swatch" data-c="${c}" style="background:${c}" title="${c}"></button>`).join("")}
          <input type="color" id="colorPick" value="${color}" title="${t("v_color")}"></div>
        ${tr.stage_count > 1 ? `<label class="chk"><input type="checkbox" id="byStage"> ${t("v_stages")}</label>` : ""}
        <button class="btn primary" id="vPdf">${ic("pdf")}${t("v_pdf")}</button>
        ${nav ? `<button class="icon-btn" id="vPrev" title="${t("v_prev")}" ${tr.prev_id ? "" : "disabled"}>${ic("left")}</button><button class="icon-btn" id="vNext" title="${t("v_next")}" ${tr.next_id ? "" : "disabled"}>${ic("right")}</button>` : ""}
        <button class="icon-btn" id="vSide" title="${t("v_side")}">${ic("list")}</button>
        <button class="icon-btn" id="vClose" title="${t("v_close")}">${ic("x")}</button>
      </div>`;
    let stageLayers = [];
    const draw = () => {
      group.clearLayers();
      const colors = byStage ? tr.geometry.map((_, i) => paletteColor(i)) : [color];
      stageLayers = drawTrack(group, tr.geometry, colors);
      $$(".swatch", head).forEach((s) => s.classList.toggle("on", !byStage && s.dataset.c.toLowerCase() === color.toLowerCase()));
      $$(".leg .sw", side).forEach((s, i) => { s.style.background = colors[Math.min(i, colors.length - 1)]; });
    };
    side.innerHTML = `<h4>${t("v_name")}</h4><input type="text" class="name-input" id="vName" value="${esc(tr.name || "")}" maxlength="120" style="width:100%">
      ${tr.stages.length > 1 ? `<h4 style="margin-top:16px">${t("col_stages")}</h4>` + tr.stages.map((s, i) => `
        <div class="leg click" data-stage="${i}"><span class="sw"></span><span><b>${t("v_stage")} ${i + 1}</b><br><span class="muted">${fmtShortDate(s.start_ts)} ${fmtTime(s.start_ts)} – ${sameDay(s.start_ts, s.end_ts) ? "" : fmtShortDate(s.end_ts) + " "}${fmtTime(s.end_ts)}</span></span>
        <span class="num">${fmtDist(s.distance_m)}<br><span class="muted">${fmtDur(s.duration_s)}</span></span></div>`).join("") : ""}`;
    draw();
    const b = group.getBounds();
    if (b.isValid()) map.fitBounds(b, { padding: [30, 30] });

    let saveTimer = null;
    const setColor = (c) => {
      color = c; byStage = false;
      const bs = $("#byStage", head); if (bs) bs.checked = false;
      $("#colorPick", head).value = c;
      draw();
      clearTimeout(saveTimer);
      saveTimer = setTimeout(async () => {
        try { await api(`api/tracks/${tr.id}`, { method: "PATCH", body: { color: c } }); changed = true; } catch (e) { toast(errText(e), "err"); }
      }, 400);
    };
    head.addEventListener("click", (e) => {
      const sw = e.target.closest(".swatch");
      if (sw) return setColor(sw.dataset.c);
      if (e.target.closest("#vPdf")) return downloadPdf([tr.id], byStage, byStage ? null : color);
      if (e.target.closest("#vClose")) return m.close();
      if (e.target.closest("#vSide")) return side.classList.toggle("mobile-open");
      const pv = e.target.closest("#vPrev"), nx = e.target.closest("#vNext");
      if ((pv && tr.prev_id) || (nx && tr.next_id)) { m.close(); openViewer([pv ? tr.prev_id : tr.next_id]); }
    });
    $("#colorPick", head).addEventListener("input", (e) => setColor(e.target.value));
    const bs = $("#byStage", head);
    if (bs) bs.addEventListener("change", () => { byStage = bs.checked; draw(); });
    $("#vName", side).addEventListener("change", async (e) => {
      try { await api(`api/tracks/${tr.id}`, { method: "PATCH", body: { name: e.target.value } }); changed = true; toast(t("saved"), "ok"); } catch (err) { toast(errText(err), "err"); }
    });
    side.addEventListener("click", (e) => {
      const st = e.target.closest("[data-stage]");
      if (!st) return;
      const l = stageLayers[+st.dataset.stage];
      if (l) map.fitBounds(l.getBounds(), { padding: [30, 30] });
    });
  } else {
    const tracks = data.tracks;
    const used = new Set(tracks.filter((x) => x.color).map((x) => x.color.toLowerCase()));
    let k = 0;
    tracks.forEach((x) => {
      if (x.color) { x._c = x.color; return; }
      while (used.has(String(paletteColor(k)).toLowerCase())) k++;
      x._c = paletteColor(k++);
    });
    const head = $(".viewer-head", m.el);
    const side = $(".viewer-side", m.el);
    const sum = (f) => tracks.reduce((a, x) => a + x[f], 0);
    head.innerHTML = `<div><div class="title">${ic("map")}${t("v_trips", { n: tracks.length })}</div>
      <div class="facts"><span>${esc(fmtDate(tracks[0].start_ts))} – ${esc(fmtDate(tracks[tracks.length - 1].end_ts))}</span>
      <span>${t("col_duration")} <b>${fmtDur(sum("duration_s"))}</b></span><span>${t("col_driving")} <b>${fmtDur(sum("driving_s"))}</b></span>
      <span>${S.settings.distance_unit === "mi" ? t("col_distance_mi") : t("col_distance")} <b>${fmtDist(sum("distance_m"))}</b></span>
      <span>${t("col_stages")} <b>${sum("stage_count")}</b></span></div></div>
      <div class="tools"><button class="btn primary" id="vPdf">${ic("pdf")}${t("v_pdf")}</button>
      <button class="icon-btn" id="vSide" title="${t("v_side")}">${ic("list")}</button><button class="icon-btn" id="vClose" title="${t("v_close")}">${ic("x")}</button></div>`;
    const groups = tracks.map((x) => { const g = L.featureGroup(); drawTrack(g, x.geometry, [x._c]); g.addTo(group); return g; });
    side.innerHTML = `<h4>${t("v_legend")}</h4>` + tracks.map((x, i) => `
      <div class="leg"><input type="checkbox" checked data-tog="${i}"><span class="click" data-zoom="${i}" style="cursor:pointer"><span class="sw" style="display:inline-block;background:${x._c};margin-right:6px;vertical-align:-1px"></span><b>${esc(fmtDate(x.start_ts, true))}</b>${x.name ? `<br><span class="muted">${esc(x.name)}</span>` : ""}</span>
      <span class="num">${fmtDist(x.distance_m)}<br><span class="muted">${fmtDur(x.duration_s)}</span></span></div>`).join("");
    const b = group.getBounds();
    if (b.isValid()) map.fitBounds(b, { padding: [30, 30] });
    head.addEventListener("click", (e) => {
      if (e.target.closest("#vPdf")) return downloadPdf(tracks.map((x) => x.id), false, null);
      if (e.target.closest("#vClose")) return m.close();
      if (e.target.closest("#vSide")) side.classList.toggle("mobile-open");
    });
    side.addEventListener("change", (e) => {
      const i = e.target.dataset.tog;
      if (i === undefined) return;
      if (e.target.checked) groups[i].addTo(group); else group.removeLayer(groups[i]);
    });
    side.addEventListener("click", (e) => {
      const z = e.target.closest("[data-zoom]");
      if (z) map.fitBounds(groups[+z.dataset.zoom].getBounds(), { padding: [30, 30] });
    });
  }
  setTimeout(() => { if (!closed) map.invalidateSize(); }, 50);
}

// ------------------------------------------------------------------ Einstellungen
const FIELDS = [
  { sec: "set_file", items: [
    { k: "gps_file", type: "text", label: "set_path", help: "set_path_h", extra: "CHECK" },
    { k: "file_timezone", type: "select", label: "set_tz", help: "set_tz_h", opts: [["utc", "set_tz_utc"], ["local", "set_tz_local"]] },
    { k: "import_interval_min", type: "number", label: "set_interval", help: "set_interval_h", step: 1, min: 0 },
  ]},
  { sec: "set_home", id: "homeSec", items: [
    { k: "home_lat", type: "number", label: "set_lat", step: "any" },
    { k: "home_lon", type: "number", label: "set_lon", step: "any" },
    { k: "home_radius_m", type: "number", label: "set_radius", help: "set_radius_h", step: 10, min: 10 },
  ]},
  { sec: "set_detect", items: [
    { k: "leave_points", type: "number", label: "set_leave", help: "set_leave_h", step: 1, min: 1 },
    { k: "stage_gap_min", type: "number", label: "set_gap", help: "set_gap_h", step: 1, min: 1 },
    { k: "min_trip_km", type: "number", label: "set_min", help: "set_min_h", step: 0.1, min: 0 },
    { k: "max_speed_kmh", type: "number", label: "set_vmax", help: "set_vmax_h", step: 10, min: 20 },
    { k: "jump_km", type: "number", label: "set_jump", help: "set_jump_h", step: 0.5, min: 0.1 },
  ]},
  { sec: "set_view", items: [
    { k: "language", type: "select", label: "set_lang", opts: [["auto", "set_lang_auto"], ["de", "Deutsch"], ["en", "English"]] },
    { k: "distance_unit", type: "select", label: "set_unit", opts: [["km", "Kilometer / km"], ["mi", "Meilen / miles"]] },
    { k: "default_color", type: "color", label: "set_color" },
    { k: "page_size", type: "select", label: "set_pagesize", opts: PAGE_SIZES.map((n) => [String(n), n ? String(n) : "all"]) },
  ]},
  { sec: "set_tiles", items: [
    { k: "tile_url", type: "text", label: "set_tile_url", help: "set_tile_url_h" },
    { k: "tile_cache_days", type: "number", label: "set_cache_days", help: "set_cache_days_h", step: 1, min: 0 },
    { k: "tile_cache_max_mb", type: "number", label: "set_cache_mb", help: "set_cache_mb_h", step: 50, min: 20 },
  ]},
];

function fieldHtml(f) {
  const v = S.settings[f.k];
  let ctl;
  if (f.type === "select") {
    ctl = `<select name="${f.k}">${f.opts.map(([val, lab]) => `<option value="${val}" ${String(v) === val ? "selected" : ""}>${esc(window.I18N.de[lab] || window.I18N.en[lab] ? t(lab) : lab)}</option>`).join("")}</select>`;
  } else if (f.type === "color") {
    ctl = `<input type="color" name="${f.k}" value="${esc(v)}">`;
  } else {
    ctl = `<input type="${f.type}" name="${f.k}" value="${v === null || v === undefined ? "" : esc(v)}" ${f.step ? `step="${f.step}"` : ""} ${f.min !== undefined ? `min="${f.min}"` : ""}>`;
  }
  return `<div class="field" data-f="${f.k}"><label>${t(f.label)}</label><div class="ctl">${ctl}${f.extra === "CHECK" ? `<button class="btn sm" type="button" id="chkFile">${t("set_check")}</button>` : ""}</div>${f.help ? `<div class="help">${esc(t(f.help))}</div>` : ""}</div>`;
}

async function viewSettings() {
  try { S.settings = await api("api/settings"); } catch (e) { toast(errText(e), "err"); }
  const secs = FIELDS.map((s) => `<section class="panel ${s.id === "homeSec" ? "" : ""}" ${s.id ? `id="${s.id}"` : ""}><div class="panel-head"><h2>${t(s.sec)}</h2></div>
    ${s.items.map(fieldHtml).join("")}
    ${s.sec === "set_file" ? `<div id="fileResult"></div>` : ""}
    ${s.id === "homeSec" ? `<div class="ctl" style="margin-top:10px"><button class="btn sm" type="button" id="fromHa">${ic("home")}${t("set_from_ha")}</button></div><div class="home-map" id="homeMap"></div><div class="help muted" style="margin-top:6px">${t("set_map_h")}</div>` : ""}
    ${s.sec === "set_tiles" ? `<div class="field"><label></label><div class="ctl"><span class="muted" id="cacheInfo">…</span><button class="btn sm" type="button" id="cacheClear">${t("set_cache_clear")}</button></div></div>` : ""}
  </section>`).join("");
  $("#view").innerHTML = `<form id="setForm" autocomplete="off" onsubmit="return false"><div class="settings-grid">${secs}
    <section class="panel"><div class="panel-head"><h2>${t("set_db")}</h2></div>
      <p class="intro">${t("set_backup_h")}</p>
      <div class="ctl" style="display:flex;gap:10px;flex-wrap:wrap"><button class="btn" type="button" id="doBackup">${ic("db")}${t("set_backup")}</button>
      <button class="btn danger" type="button" id="doRebuild">${ic("sync")}${t("set_rebuild")}</button></div></section>
  </div>
  <div class="savebar"><span class="grow" id="saveState"></span><button class="btn primary lg" type="button" id="saveBtn">${t("save")}</button></div></form>`;

  const form = $("#setForm");
  const val = (k) => { const el = form.elements[k]; return el ? el.value : undefined; };
  form.addEventListener("input", () => { $("#saveState").textContent = t("set_unsaved"); });

  // Heimkarte
  const hm = L.map("homeMap");
  osmLayer().addTo(hm);
  let marker = null, circle = null;
  const syncMap = (fit) => {
    const lat = parseFloat(val("home_lat")), lon = parseFloat(val("home_lon")), r = parseFloat(val("home_radius_m")) || 200;
    if (isNaN(lat) || isNaN(lon)) { hm.setView([51.16, 10.45], 5); return; }
    if (!marker) {
      hm.setView([lat, lon], 16);
      marker = L.marker([lat, lon], { draggable: true, icon: L.divIcon({ className: "home-marker", iconSize: [18, 18] }) }).addTo(hm);
      circle = L.circle([lat, lon], { radius: r, color: "#ce6c00", weight: 2, fillOpacity: 0.12 }).addTo(hm);
      marker.on("drag", () => { const p = marker.getLatLng(); circle.setLatLng(p); });
      marker.on("dragend", () => { const p = marker.getLatLng(); setPos(p.lat, p.lng, false); });
    } else { marker.setLatLng([lat, lon]); circle.setLatLng([lat, lon]); circle.setRadius(r); }
    if (fit) hm.fitBounds(circle.getBounds(), { padding: [40, 40], maxZoom: 17 });
  };
  const setPos = (lat, lon, fit = true) => {
    form.elements.home_lat.value = lat.toFixed(7);
    form.elements.home_lon.value = lon.toFixed(7);
    $("#saveState").textContent = t("set_unsaved");
    syncMap(fit);
  };
  hm.on("click", (e) => setPos(e.latlng.lat, e.latlng.lng, false));
  ["home_lat", "home_lon", "home_radius_m"].forEach((k) => form.elements[k].addEventListener("change", () => syncMap(true)));
  setTimeout(() => { hm.invalidateSize(); syncMap(true); }, 60);

  $("#fromHa").addEventListener("click", async () => {
    try {
      const p = await api("api/ha/location");
      if (p.lat != null && p.lon != null) setPos(p.lat, p.lon, true);
    } catch (e) { toast(errText(e), "err"); }
  });

  const checkFile = async () => {
    const box = $("#fileResult");
    try {
      const r = await api(`api/file/check?path=${encodeURIComponent(val("gps_file"))}`);
      box.innerHTML = r.exists
        ? `<div class="notice info" style="margin:8px 0 0"><div class="grow">${esc(t("chk_ok", { s: fmtBytes(r.size), ok: r.parsed, n: r.checked }))}<pre class="sample">${esc(r.sample.join("\n"))}</pre></div></div>`
        : `<div class="notice err" style="margin:8px 0 0"><div class="grow">${t("chk_missing")} ${r.dir_exists ? t("chk_dir") : ""}</div></div>`;
    } catch (e) { box.innerHTML = `<div class="notice err"><div class="grow">${esc(errText(e))}</div></div>`; }
  };
  $("#chkFile").addEventListener("click", checkFile);
  checkFile();

  const loadCache = async () => {
    try { const c = await api("api/tiles/info"); $("#cacheInfo").textContent = t("set_cache_info", { s: fmtBytes(c.bytes), n: c.count }); } catch (_) { /* egal */ }
  };
  loadCache();
  $("#cacheClear").addEventListener("click", async () => {
    try { await api("api/tiles/clear", { method: "POST" }); toast(t("done"), "ok"); loadCache(); } catch (e) { toast(errText(e), "err"); }
  });
  $("#doBackup").addEventListener("click", async () => {
    try { const r = await api("api/backup", { method: "POST" }); toast(t("backup_done", { p: r.path }), "ok"); } catch (e) { toast(errText(e), "err"); }
  });
  $("#doRebuild").addEventListener("click", () => reimportDialog("rebuild"));

  $("#saveBtn").addEventListener("click", async () => {
    const body = {};
    for (const s of FIELDS) for (const f of s.items) body[f.k] = val(f.k);
    $$(".field.err", form).forEach((x) => x.classList.remove("err"));
    try {
      const r = await api("api/settings", { method: "POST", body });
      const langChanged = r.settings.language !== S.settings.language;
      S.settings = r.settings;
      $("#saveState").textContent = "";
      toast(t("saved"), "ok");
      if (langChanged) { await loadInfo(); viewSettings(); renderMenu(); renderFoot(); }
      refreshStats();
      if (r.rebuild_recommended && (await confirmDlg(t("set_rebuild_q"), { ok: t("ri_rebuild") }))) doImport("rebuild");
    } catch (e) {
      if (e.code === "invalid_settings") {
        (e.data.fields || []).forEach((k) => { const f = $(`.field[data-f="${k}"]`, form); if (f) f.classList.add("err"); });
        toast(t("set_invalid"), "err");
      } else toast(errText(e), "err");
    }
  });
}

// ------------------------------------------------------------------ Log
async function viewLog() {
  S.logLast = 0;
  $("#view").innerHTML = `<section class="panel"><div class="panel-head"><h2>${t("log_title")}</h2><span class="sub">${t("log_sub")}</span>
    <div class="right"><label class="muted">${t("log_level")}</label><select id="logLevel"><option value="debug">Debug</option><option value="info" selected>Info</option><option value="warning">Warning</option><option value="error">Error</option></select>
    <label class="chk"><input type="checkbox" id="logAuto" checked> ${t("log_auto")}</label></div></div>
    <div class="table-wrap"><table class="list log"><thead><tr><th>${t("col_time")}</th><th>${t("col_level")}</th><th>${t("col_source")}</th><th>${t("col_msg")}</th></tr></thead><tbody id="logBody"></tbody></table></div></section>`;
  const load = async () => {
    try {
      const r = await api(`api/log?level=${$("#logLevel").value}`);
      const rows = r.rows.slice().reverse();
      $("#logBody").innerHTML = rows.length ? rows.map((x) => `<tr><td class="num">${fmtShortDate(x.ts)} ${new Intl.DateTimeFormat("en-GB", { timeZone: S.tz, hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }).format(new Date(x.ts * 1000))}</td>
        <td><span class="lvl ${x.level}">${x.level}</span></td><td>${esc(x.logger)}</td><td class="msg">${esc(x.msg)}</td></tr>`).join("") : `<tr><td colspan="4" class="empty">${t("log_empty")}</td></tr>`;
    } catch (_) { /* egal */ }
  };
  $("#logLevel").addEventListener("change", load);
  await load();
  clearInterval(S.logTimer);
  S.logTimer = setInterval(() => { if (S.route === "log" && $("#logAuto") && $("#logAuto").checked) load(); }, 4000);
}

function viewHelp() {
  $("#view").innerHTML = `<section class="panel doc"><div class="panel-head"><h2>${t("help_title")}</h2></div>${window.HELP[S.lang] || window.HELP.en}</section>`;
}

// ------------------------------------------------------------------ Router
function renderFoot() {
  $("#foot").innerHTML = `My TrackView ${esc(S.info.version)} · ${t("foot").replace("OpenStreetMap", '<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>')}`;
}

async function route() {
  const r = (location.hash.replace(/^#\/?/, "") || "trips").split("?")[0];
  S.route = ROUTES.includes(r) ? r : "trips";
  if (S.route !== "log") clearInterval(S.logTimer);
  renderMenu();
  window.scrollTo(0, 0);
  if (["trips", "unassigned", "trash"].includes(S.route)) await viewList(S.route);
  else if (S.route === "settings") await viewSettings();
  else if (S.route === "log") await viewLog();
  else viewHelp();
}

async function loadInfo() {
  S.info = await api("api/info");
  S.settings = S.info.settings;
  S.tz = S.info.tz || "UTC";
  try { new Intl.DateTimeFormat("en", { timeZone: S.tz }); } catch (_) { S.tz = Intl.DateTimeFormat().resolvedOptions().timeZone; }
  S.lang = S.info.lang || ((navigator.language || "de").startsWith("de") ? "de" : "en");
  document.documentElement.lang = S.lang;
}

async function init() {
  try {
    await loadInfo();
  } catch (e) {
    $("#view").innerHTML = `<div class="notice err"><div class="grow">My TrackView: ${esc(e.message)}</div></div>`;
    return;
  }
  renderFoot();
  window.addEventListener("hashchange", route);
  await refreshStats();
  await route();
}

init();
})();

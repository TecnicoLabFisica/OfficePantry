/* Office Pantry — reads the CSV ledger and renders it.
 *
 * Money rule: every amount becomes an integer number of cents the moment it is
 * parsed, and stays an integer until it is formatted for display. Summing
 * float dollars drifts, and this page exists to be trusted about money.
 */

const Pantry = (() => {
  'use strict';

  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'];

  /* ---------- parsing ---------- */

  // Minimal RFC-4180-ish parser: handles quoted fields, embedded commas,
  // escaped quotes and CRLF. Descriptions like "Water, snacks" need this.
  function parseCSV(text) {
    const rows = [];
    let row = [], field = '', quoted = false;

    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (quoted) {
        if (c === '"') {
          if (text[i + 1] === '"') { field += '"'; i++; }
          else quoted = false;
        } else field += c;
      } else if (c === '"') {
        quoted = true;
      } else if (c === ',') {
        row.push(field); field = '';
      } else if (c === '\n' || c === '\r') {
        if (c === '\r' && text[i + 1] === '\n') i++;
        row.push(field); rows.push(row); row = []; field = '';
      } else field += c;
    }
    if (field !== '' || row.length) { row.push(field); rows.push(row); }

    const clean = rows.filter(r =>
      r.some(v => v.trim() !== '') && !r[0].trim().startsWith('#'));
    if (!clean.length) return [];

    const header = clean[0].map(h => h.trim());
    return clean.slice(1).map(r => {
      const o = {};
      header.forEach((h, i) => { o[h] = (r[i] ?? '').trim(); });
      return o;
    });
  }

  function toCents(value) {
    const n = parseFloat(String(value).replace(/[^0-9.\-]/g, ''));
    return Number.isFinite(n) ? Math.round(n * 100) : 0;
  }

  /* ---------- formatting ---------- */

  let symbol = '$';

  function money(cents) {
    const sign = cents < 0 ? '-' : '';
    const abs = Math.abs(cents);
    return `${sign}${symbol}${Math.floor(abs / 100)}.${String(abs % 100).padStart(2, '0')}`;
  }

  function monthLabel(key) {           // "2026-09" -> "September 2026"
    const [y, m] = String(key).split('-');
    return `${MONTHS[parseInt(m, 10) - 1] ?? m} ${y}`;
  }

  function dayLabel(iso) {             // "2026-09-03" -> "September 3"
    const [y, m, d] = String(iso).split('-');
    return `${MONTHS[parseInt(m, 10) - 1] ?? m} ${parseInt(d, 10) || d}`;
  }

  function currentMonthKey() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  /* ---------- loading ---------- */

  async function fetchText(url) {
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) throw new Error(`${res.status} fetching ${url}`);
    return res.text();
  }

  let configPromise = null;
  function loadConfig() {
    if (!configPromise) {
      configPromise = fetchText('data/config.json')
        .then(t => JSON.parse(t))
        .then(cfg => { symbol = cfg.currencySymbol || '$'; return cfg; });
    }
    return configPromise;
  }

  async function loadLedger() {
    const [cText, eText] = await Promise.all([
      fetchText('data/contributions.csv'),
      fetchText('data/expenses.csv'),
    ]);

    const contributions = parseCSV(cText).map(r => ({
      date: r.date,
      name: r.name,
      month: r.month || String(r.date).slice(0, 7),
      cents: toCents(r.amount),
    }));

    const expenses = parseCSV(eText).map(r => ({
      date: r.date,
      description: r.description,
      category: r.category || 'other',
      month: String(r.date).slice(0, 7),
      cents: toCents(r.amount),
    }));

    return { contributions, expenses };
  }

  /* ---------- derivations (never a stored balance) ---------- */

  const sum = rows => rows.reduce((t, r) => t + r.cents, 0);

  function balance(ledger) {
    return sum(ledger.contributions) - sum(ledger.expenses);
  }

  function byCategory(expenses) {
    const totals = new Map();
    for (const e of expenses) {
      totals.set(e.category, (totals.get(e.category) || 0) + e.cents);
    }
    return [...totals.entries()]
      .map(([category, cents]) => ({ category, cents }))
      .sort((a, b) => b.cents - a.cents);
  }

  /* ---------- rendering ---------- */

  function setPeriod(text) {
    const el = document.querySelector('[data-period]');
    if (el) el.textContent = text;
  }

  function showBalance(el, cents, note) {
    el.textContent = money(cents);
    el.classList.toggle('is-negative', cents < 0);
    const noteEl = document.querySelector('[data-balance-note]');
    if (noteEl && note) noteEl.textContent = note;
  }

  function fail(el, message) {
    el.innerHTML = `<p class="state is-error">${escapeHtml(message)}</p>`;
  }

  async function initIndex() {
    setPeriod(monthLabel(currentMonthKey()));
    const amountEl = document.querySelector('[data-balance]');
    if (!amountEl) return;

    try {
      await loadConfig();
      const ledger = await loadLedger();
      const monthKey = currentMonthKey();
      const spent = sum(ledger.expenses.filter(e => e.month === monthKey));
      showBalance(amountEl, balance(ledger),
        spent ? `${money(spent)} spent this month` : 'Nothing spent yet this month');
    } catch (err) {
      amountEl.textContent = '—';
      const noteEl = document.querySelector('[data-balance-note]');
      if (noteEl) noteEl.textContent = "Couldn't load the ledger.";
      console.error(err);
    }
  }

  async function initBudget() {
    const amountEl = document.querySelector('[data-balance]');
    const monthEl = document.querySelector('[data-month-summary]');
    const catEl = document.querySelector('[data-breakdown]');
    const histEl = document.querySelector('[data-history]');
    setPeriod(monthLabel(currentMonthKey()));

    let cfg = {};
    try { cfg = await loadConfig(); } catch (e) { console.error(e); }

    let ledger;
    try {
      ledger = await loadLedger();
    } catch (err) {
      console.error(err);
      if (amountEl) amountEl.textContent = '—';
      [monthEl, catEl, histEl].forEach(el =>
        el && fail(el, 'Could not load the ledger files.'));
      return;
    }

    const monthKey = currentMonthKey();
    const inThisMonth = sum(ledger.contributions.filter(c => c.month === monthKey));
    const outThisMonth = sum(ledger.expenses.filter(e => e.month === monthKey));

    if (amountEl) showBalance(amountEl, balance(ledger), 'Carried across every month');

    if (monthEl) {
      monthEl.innerHTML = `
        <div class="row">
          <div class="row-main"><span class="row-title">Contributions in</span></div>
          <span class="amount is-in">+${money(inThisMonth)}</span>
        </div>
        <div class="row">
          <div class="row-main"><span class="row-title">Spent</span></div>
          <span class="amount is-out">-${money(outThisMonth)}</span>
        </div>
        <div class="row is-total">
          <div class="row-main"><span class="row-title">Net this month</span></div>
          <span class="amount">${money(inThisMonth - outThisMonth)}</span>
        </div>`;
    }

    if (catEl) {
      const cats = byCategory(ledger.expenses);
      const max = cats.length ? cats[0].cents : 0;
      catEl.innerHTML = cats.length ? cats.map(({ category, cents }) => {
        const meta = (cfg.categories || {})[category] || {};
        const label = meta.label || category;
        const emoji = meta.emoji || '•';
        const width = max ? Math.max(2, Math.round((cents / max) * 100)) : 0;
        return `
          <div class="row">
            <div class="row-main">
              <span class="row-title">${escapeHtml(emoji)} ${escapeHtml(label)}</span>
              <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
            </div>
            <span class="amount">${money(cents)}</span>
          </div>`;
      }).join('') : '<p class="state">No spending recorded yet.</p>';
    }

    if (histEl) {
      const entries = [
        ...ledger.contributions.map(c => ({
          date: c.date, title: `${c.name} paid in`, meta: monthLabel(c.month),
          cents: c.cents, dir: 'in',
        })),
        ...ledger.expenses.map(e => {
          const meta = (cfg.categories || {})[e.category] || {};
          return {
            date: e.date, title: e.description,
            meta: `${meta.emoji || ''} ${meta.label || e.category}`.trim(),
            cents: e.cents, dir: 'out',
          };
        }),
      ].sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));

      histEl.innerHTML = entries.length ? entries.map(e => `
        <div class="row">
          <div class="row-main">
            <span class="row-title">${escapeHtml(e.title)}</span>
            <span class="row-meta">${escapeHtml(dayLabel(e.date))} · ${escapeHtml(e.meta)}</span>
          </div>
          <span class="amount is-${e.dir}">${e.dir === 'in' ? '+' : '-'}${money(e.cents)}</span>
        </div>`).join('') : '<p class="state">Nothing recorded yet.</p>';
    }
  }

  async function initSuggestions() {
    setPeriod(monthLabel(currentMonthKey()));
    const formEl = document.querySelector('[data-form]');
    const listEl = document.querySelector('[data-suggestions]');

    let cfg = {};
    try { cfg = await loadConfig(); } catch (e) { console.error(e); }

    if (formEl) {
      if (cfg.suggestionFormUrl) {
        formEl.innerHTML =
          `<iframe class="form-embed" src="${escapeHtml(cfg.suggestionFormUrl)}"
             height="620" loading="lazy" title="Suggest something"></iframe>`;
      } else {
        formEl.innerHTML =
          '<p class="state">The suggestion form has not been linked yet. ' +
          'Add its URL to <code>data/config.json</code>.</p>';
      }
    }

    if (!listEl) return;

    if (!cfg.suggestionSheetCsvUrl) {
      listEl.innerHTML = '<p class="state">Suggestions will appear here once the ' +
        'response sheet is published.</p>';
      return;
    }

    // Google's published-CSV endpoint is the one piece outside this repo's
    // control. If it will not load, the form above still works — degrade to a
    // link rather than showing a broken page.
    try {
      const rows = parseCSV(await fetchText(cfg.suggestionSheetCsvUrl));
      if (!rows.length) {
        listEl.innerHTML = '<p class="state">No suggestions yet. Be the first.</p>';
        return;
      }
      const key = k => Object.keys(rows[0]).find(h => h.toLowerCase().includes(k));
      const productKey = key('product') || key('suggest') || Object.keys(rows[0])[1];
      const categoryKey = key('categor');

      listEl.innerHTML = rows.slice().reverse().map(r => {
        const product = r[productKey] || '(blank)';
        const cat = categoryKey ? r[categoryKey] : '';
        const meta = (cfg.categories || {})[String(cat).toLowerCase()] || {};
        const label = cat ? `${meta.emoji || ''} ${meta.label || cat}`.trim() : '';
        return `
          <div class="row">
            <div class="row-main">
              <span class="row-title">${escapeHtml(product)}</span>
              ${label ? `<span class="row-meta">${escapeHtml(label)}</span>` : ''}
            </div>
          </div>`;
      }).join('');
    } catch (err) {
      console.error(err);
      listEl.innerHTML =
        '<p class="state">The live list could not be loaded, but your suggestion ' +
        'above still goes through.</p>';
    }
  }

  return { parseCSV, toCents, money, balance, byCategory, loadLedger,
    initIndex, initBudget, initSuggestions };
})();

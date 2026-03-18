/* ── Helpers ──────────────────────────────────────────────────────────────── */
const API = '';

function maskWallet(addr) {
  if (!addr || addr.length < 10) return addr || '—';
  return addr.slice(0, 6) + '…' + addr.slice(-4);
}

function fmtDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleString('ru-RU');
}

function sideTag(side) {
  const s = (side || '').toUpperCase();
  const cls = s === 'BUY' ? 'tag-buy' : 'tag-sell';
  return `<span class="tag ${cls}">${s}</span>`;
}

function statusTag(st) {
  const s = (st || '').toLowerCase();
  let cls = 'tag-pending';
  if (s === 'success' || s === 'live' || s === 'matched') cls = 'tag-success';
  else if (s === 'error' || s === 'cancelled') cls = 'tag-error';
  return `<span class="tag ${cls}">${st}</span>`;
}

/* ── Toast ────────────────────────────────────────────────────────────────── */
function toast(msg, type = 'ok') {
  const c = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  c.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

/* ── API calls ────────────────────────────────────────────────────────────── */
async function apiGet(path) {
  const r = await fetch(API + path);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

async function apiPost(path, body = {}) {
  const r = await fetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`${r.status}: ${text}`);
  }
  return r.json();
}

/* ── Status refresh ───────────────────────────────────────────────────────── */
async function refreshStatus() {
  try {
    const s = await apiGet('/api/status');
    const dot  = document.getElementById('status-dot');
    const text = document.getElementById('status-text');
    dot.className = 'dot ' + (s.running ? 'running' : 'stopped');
    text.textContent = s.running ? 'Работает' : 'Остановлен';

    document.getElementById('stat-copied').textContent     = s.copied_count ?? 0;
    document.getElementById('stat-errors').textContent     = s.error_count  ?? 0;
    document.getElementById('stat-interval').textContent   = (s.poll_interval ?? '—') + ' с';
    document.getElementById('stat-multiplier').textContent = s.copy_multiplier ?? '—';
    document.getElementById('stat-last-poll').textContent  = fmtDate(s.last_poll);

    // Pre-fill form if empty
    const ta = document.getElementById('target-address');
    if (!ta.value && s.target_wallet) ta.value = s.target_wallet;
    const mi = document.getElementById('multiplier');
    if (mi.value === '1' || mi.value === '1.0') mi.value = s.copy_multiplier;
    const ii = document.getElementById('interval');
    if (ii.value === '10' && s.poll_interval) ii.value = s.poll_interval;

    document.getElementById('btn-start').disabled = s.running;
    document.getElementById('btn-stop').disabled  = !s.running;
  } catch (e) {
    document.getElementById('status-text').textContent = 'Нет связи';
  }
}

/* ── Order tables ─────────────────────────────────────────────────────────── */
function setTableRows(tableId, rows) {
  const tbody = document.querySelector(`#${tableId} tbody`);
  tbody.innerHTML = rows.length
    ? rows.join('')
    : '<tr><td colspan="99" style="text-align:center;color:var(--muted)">Нет данных</td></tr>';
}

async function refreshTargetOrders() {
  try {
    const orders = await apiGet('/api/orders/target');
    const rows = (orders || []).map(o => `
      <tr>
        <td title="${o.id || ''}">${maskWallet(o.id)}</td>
        <td>${o.market || o.token_id || '—'}</td>
        <td>${sideTag(o.side)}</td>
        <td>${o.price ?? '—'}</td>
        <td>${o.original_size ?? o.size ?? '—'}</td>
        <td>${statusTag(o.status)}</td>
      </tr>`);
    setTableRows('table-target', rows);
  } catch (e) {
    toast('Ошибка загрузки ордеров цели: ' + e.message, 'err');
  }
}

async function refreshCopiedOrders() {
  try {
    const orders = await apiGet('/api/orders/copied');
    const rows = (orders || []).map(o => `
      <tr>
        <td title="${o.original_order_id}">${maskWallet(o.original_order_id)}</td>
        <td title="${o.copied_order_id || ''}">${maskWallet(o.copied_order_id)}</td>
        <td>${o.token_id || '—'}</td>
        <td>${sideTag(o.side)}</td>
        <td>${o.price ?? '—'}</td>
        <td>${o.size ?? '—'}</td>
        <td>${statusTag(o.status)}</td>
        <td>${fmtDate(o.copied_at)}</td>
      </tr>`);
    setTableRows('table-copied', rows);
  } catch (e) {
    toast('Ошибка загрузки скопированных ордеров: ' + e.message, 'err');
  }
}

async function refreshOwnOrders() {
  try {
    const orders = await apiGet('/api/orders/own');
    const rows = (orders || []).map(o => `
      <tr>
        <td title="${o.id || ''}">${maskWallet(o.id)}</td>
        <td>${o.asset_id || o.token_id || '—'}</td>
        <td>${sideTag(o.side)}</td>
        <td>${o.price ?? '—'}</td>
        <td>${o.original_size ?? o.size ?? '—'}</td>
        <td>${statusTag(o.status)}</td>
      </tr>`);
    setTableRows('table-own', rows);
  } catch (e) {
    toast('Ошибка загрузки своих ордеров: ' + e.message, 'err');
  }
}

/* ── Button handlers ──────────────────────────────────────────────────────── */
document.getElementById('btn-save').addEventListener('click', async () => {
  const body = {
    target_wallet_address: document.getElementById('target-address').value.trim(),
    copy_multiplier:       parseFloat(document.getElementById('multiplier').value),
    poll_interval_seconds: parseInt(document.getElementById('interval').value, 10),
  };
  try {
    await apiPost('/api/config', body);
    toast('Настройки сохранены', 'ok');
    refreshStatus();
  } catch (e) {
    toast('Ошибка сохранения: ' + e.message, 'err');
  }
});

document.getElementById('btn-start').addEventListener('click', async () => {
  try {
    const r = await apiPost('/api/start');
    toast('Бот запущен: ' + r.status, 'ok');
    refreshStatus();
  } catch (e) {
    toast('Ошибка запуска: ' + e.message, 'err');
  }
});

document.getElementById('btn-stop').addEventListener('click', async () => {
  try {
    const r = await apiPost('/api/stop');
    toast('Бот остановлен: ' + r.status, 'ok');
    refreshStatus();
  } catch (e) {
    toast('Ошибка остановки: ' + e.message, 'err');
  }
});

document.getElementById('btn-cancel').addEventListener('click', async () => {
  if (!confirm('Отменить все открытые ордера?')) return;
  try {
    const r = await apiPost('/api/cancel-all');
    toast(r.success ? 'Все ордера отменены' : 'Не удалось отменить ордера', r.success ? 'ok' : 'err');
    refreshOwnOrders();
  } catch (e) {
    toast('Ошибка отмены: ' + e.message, 'err');
  }
});

document.getElementById('btn-refresh-target').addEventListener('click', refreshTargetOrders);
document.getElementById('btn-refresh-own').addEventListener('click', refreshOwnOrders);

/* ── Auto-refresh ─────────────────────────────────────────────────────────── */
async function fullRefresh() {
  await refreshStatus();
  await refreshCopiedOrders();
}

fullRefresh();
refreshTargetOrders();
refreshOwnOrders();
setInterval(fullRefresh, 10000);
setInterval(refreshTargetOrders, 30000);
setInterval(refreshOwnOrders, 30000);

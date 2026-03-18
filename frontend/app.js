/* app.js — Polymarket Copy Trader frontend */

const API = '';          // same origin
let autoRefreshTimer = null;
let currentStatus = null;

// =====================================================================
// Utility helpers
// =====================================================================

function maskAddress(addr) {
  if (!addr || addr.length < 12) return addr || '—';
  return addr.slice(0, 6) + '…' + addr.slice(-4);
}

function formatTime(ts) {
  if (!ts) return '—';
  const d = new Date(ts);
  if (isNaN(d)) return ts;
  return d.toLocaleString();
}

function sideBadge(side) {
  const s = (side || '').toLowerCase();
  return `<span class="badge badge-${s}">${(side || '').toUpperCase()}</span>`;
}

function statusBadge(status) {
  const s = (status || '').toLowerCase();
  return `<span class="badge badge-${s}">${status || '—'}</span>`;
}

// =====================================================================
// Toast notifications
// =====================================================================

let toastTimer;

function showToast(msg, type = 'info') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast ${type} show`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.classList.remove('show');
  }, 3500);
}

// =====================================================================
// API calls
// =====================================================================

async function apiFetch(path, options = {}) {
  try {
    const res = await fetch(API + path, options);
    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch (parseErr) {
      console.warn('Response is not JSON:', parseErr, text);
      data = text;
    }
    if (!res.ok) {
      const msg = (data && data.detail) ? data.detail : `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return data;
  } catch (err) {
    throw err;
  }
}

// =====================================================================
// Status
// =====================================================================

async function loadStatus() {
  try {
    const s = await apiFetch('/api/status');
    currentStatus = s;
    updateStatusUI(s);
  } catch (err) {
    console.error('Status fetch failed:', err);
  }
}

function updateStatusUI(s) {
  // Header badge
  const dot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  if (s.is_running) {
    dot.classList.add('running');
    statusText.textContent = 'Running';
  } else {
    dot.classList.remove('running');
    statusText.textContent = 'Stopped';
  }

  // Toggle button
  const btn = document.getElementById('toggleBotBtn');
  if (s.is_running) {
    btn.textContent = '⏹ Stop Bot';
    btn.className = 'btn btn-danger';
  } else {
    btn.textContent = '▶ Start Bot';
    btn.className = 'btn btn-success';
  }

  // Stats
  document.getElementById('statStatus').textContent = s.is_running ? '🟢 Running' : '🔴 Stopped';
  document.getElementById('statTarget').textContent = maskAddress(s.target_address);
  document.getElementById('statMultiplier').textContent = s.copy_multiplier != null ? `×${s.copy_multiplier}` : '—';
  document.getElementById('statInterval').textContent = s.poll_interval ? `${s.poll_interval}s` : '—';
  document.getElementById('statTotal').textContent = s.total_copied ?? 0;
  document.getElementById('statLastPoll').textContent = formatTime(s.last_poll_time);

  // Populate config inputs (don't override if user is typing)
  const targetInput = document.getElementById('targetAddress');
  if (document.activeElement !== targetInput) {
    targetInput.value = s.target_address || '';
  }
  const multInput = document.getElementById('copyMultiplier');
  if (document.activeElement !== multInput) {
    multInput.value = s.copy_multiplier ?? 1.0;
  }
  const pollInput = document.getElementById('pollInterval');
  if (document.activeElement !== pollInput) {
    pollInput.value = s.poll_interval ?? 10;
  }

  // Auto-refresh
  if (s.is_running) {
    startAutoRefresh();
  } else {
    stopAutoRefresh();
  }
}

// =====================================================================
// Bot control
// =====================================================================

async function toggleBot() {
  const btn = document.getElementById('toggleBotBtn');
  btn.disabled = true;
  try {
    if (currentStatus && currentStatus.is_running) {
      await apiFetch('/api/stop', { method: 'POST' });
      showToast('Bot stopped', 'info');
    } else {
      await apiFetch('/api/start', { method: 'POST' });
      showToast('Bot started', 'success');
    }
    await loadStatus();
  } catch (err) {
    showToast('Error: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

async function saveConfig() {
  const targetAddress = document.getElementById('targetAddress').value.trim();
  const copyMultiplier = parseFloat(document.getElementById('copyMultiplier').value);
  const pollInterval = parseInt(document.getElementById('pollInterval').value, 10);

  if (!targetAddress) { showToast('Target address is required', 'error'); return; }
  if (isNaN(copyMultiplier) || copyMultiplier <= 0) { showToast('Invalid copy multiplier', 'error'); return; }
  if (isNaN(pollInterval) || pollInterval < 5) { showToast('Poll interval must be ≥ 5 seconds', 'error'); return; }

  const btn = document.getElementById('saveConfigBtn');
  btn.disabled = true;
  try {
    await apiFetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_address: targetAddress, copy_multiplier: copyMultiplier, poll_interval: pollInterval }),
    });
    showToast('Configuration saved', 'success');
    await loadStatus();
  } catch (err) {
    showToast('Error: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

async function cancelAllOrders() {
  if (!confirm('Cancel ALL open orders? This cannot be undone.')) return;
  const btn = document.getElementById('cancelAllBtn');
  btn.disabled = true;
  try {
    await apiFetch('/api/cancel-all', { method: 'POST' });
    showToast('All orders cancelled', 'success');
    loadOwnOrders();
  } catch (err) {
    showToast('Error: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

// =====================================================================
// Orders tables
// =====================================================================

async function loadTargetOrders() {
  const tbody = document.getElementById('targetOrdersBody');
  tbody.innerHTML = '<tr><td colspan="6" class="empty-row">Loading…</td></tr>';
  try {
    const orders = await apiFetch('/api/orders/target');
    renderTargetOrders(orders);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-row">Error: ${err.message}</td></tr>`;
  }
}

function renderTargetOrders(orders) {
  const tbody = document.getElementById('targetOrdersBody');
  if (!orders || orders.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-row">No orders found</td></tr>';
    return;
  }
  tbody.innerHTML = orders.map(o => `
    <tr>
      <td class="mono">${maskAddress(o.id || o.order_id || '—')}</td>
      <td>${o.market_slug || o.market || '—'}</td>
      <td>${sideBadge(o.side)}</td>
      <td>${(o.price != null) ? Number(o.price).toFixed(4) : '—'}</td>
      <td>${(o.original_size || o.size) != null ? Number(o.original_size || o.size).toFixed(4) : '—'}</td>
      <td>${statusBadge(o.status)}</td>
    </tr>
  `).join('');
}

async function loadCopiedOrders() {
  const tbody = document.getElementById('copiedOrdersBody');
  tbody.innerHTML = '<tr><td colspan="9" class="empty-row">Loading…</td></tr>';
  try {
    const orders = await apiFetch('/api/orders/copied');
    renderCopiedOrders(orders);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="empty-row">Error: ${err.message}</td></tr>`;
  }
}

function renderCopiedOrders(orders) {
  const tbody = document.getElementById('copiedOrdersBody');
  if (!orders || orders.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" class="empty-row">No copied orders yet</td></tr>';
    return;
  }
  const sorted = [...orders].reverse();
  tbody.innerHTML = sorted.map(o => `
    <tr>
      <td class="mono">${maskAddress(o.original_order_id)}</td>
      <td class="mono">${maskAddress(o.copied_order_id) || '—'}</td>
      <td class="mono">${maskAddress(o.token_id)}</td>
      <td>${sideBadge(o.side)}</td>
      <td>${Number(o.price).toFixed(4)}</td>
      <td>${Number(o.original_size).toFixed(4)}</td>
      <td>${Number(o.copied_size).toFixed(4)}</td>
      <td>${formatTime(o.timestamp)}</td>
      <td>${statusBadge(o.status)}</td>
    </tr>
  `).join('');
}

async function loadOwnOrders() {
  const tbody = document.getElementById('ownOrdersBody');
  tbody.innerHTML = '<tr><td colspan="6" class="empty-row">Loading…</td></tr>';
  try {
    const orders = await apiFetch('/api/orders/own');
    renderOwnOrders(orders);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-row">Error: ${err.message}</td></tr>`;
  }
}

function renderOwnOrders(orders) {
  const tbody = document.getElementById('ownOrdersBody');
  if (!orders || orders.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-row">No open orders</td></tr>';
    return;
  }
  tbody.innerHTML = orders.map(o => `
    <tr>
      <td class="mono">${maskAddress(o.id || o.order_id || '—')}</td>
      <td class="mono">${maskAddress(o.asset_id || o.token_id || '—')}</td>
      <td>${sideBadge(o.side)}</td>
      <td>${(o.price != null) ? Number(o.price).toFixed(4) : '—'}</td>
      <td>${(o.size || o.original_size) != null ? Number(o.size || o.original_size).toFixed(4) : '—'}</td>
      <td>${statusBadge(o.status)}</td>
    </tr>
  `).join('');
}

// =====================================================================
// Auto-refresh
// =====================================================================

function startAutoRefresh() {
  if (autoRefreshTimer) return;
  autoRefreshTimer = setInterval(() => {
    loadStatus();
    loadTargetOrders();
    loadCopiedOrders();
    loadOwnOrders();
  }, 5000);
}

function stopAutoRefresh() {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }
}

// =====================================================================
// Init
// =====================================================================

async function init() {
  await loadStatus();
  await Promise.all([loadTargetOrders(), loadCopiedOrders(), loadOwnOrders()]);
}

document.addEventListener('DOMContentLoaded', init);

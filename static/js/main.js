/* ==========================================================================
   Shared Frontend Utilities (API Wrapper, Toasts, Sidebar, Modals, Helpers)
   ========================================================================== */

window.apiFetch = async function (url, options = {}) {
  const opts = {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options
  };
  const response = await fetch(url, opts);
  let data = null;
  try {
    data = await response.json();
  } catch (_) {
    data = null;
  }
  if (!response.ok) {
    if (response.status === 401) {
      window.location.href = '/login';
      throw new Error('Authentication required');
    }
    const msg = (data && (data.error || data.message)) || `Request failed (${response.status})`;
    throw new Error(msg);
  }
  return data;
};

window.showToast = function (message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const item = document.createElement('div');
  item.className = `toast-item ${type === 'error' ? 'toast-error' : type === 'success' ? 'toast-success' : ''}`;
  item.innerHTML = `
    <span>${escapeHtml(message)}</span>
    <button type="button" class="text-slate-400 hover:text-white text-lg leading-none" aria-label="Dismiss">&times;</button>
  `;
  item.querySelector('button').addEventListener('click', () => item.remove());
  container.appendChild(item);
  setTimeout(() => item.remove(), 4200);
};

window.escapeHtml = function (str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
};

window.openModal = function (id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('active');
};

window.closeModal = function (id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('active');
};

// Close modals on backdrop click
document.addEventListener('click', (e) => {
  if (e.target.classList && e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('active');
  }
});

// Mobile sidebar drawer behavior
document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('appSidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  const openBtn = document.getElementById('openSidebarBtn');
  const closeBtn = document.getElementById('closeSidebarBtn');

  function toggleSidebar(show) {
    if (!sidebar || !backdrop) return;
    sidebar.classList.toggle('open', show);
    backdrop.classList.toggle('open', show);
  }

  openBtn?.addEventListener('click', () => toggleSidebar(true));
  closeBtn?.addEventListener('click', () => toggleSidebar(false));
  backdrop?.addEventListener('click', () => toggleSidebar(false));

  // Refresh unread reminder badge in background on authenticated pages
  if (document.getElementById('sidebarReminderBadge')) {
    refreshReminderBadge();
  }
});

window.refreshReminderBadge = async function () {
  try {
    const res = await apiFetch('/api/reminders?only_pending=1');
    const count = (res.reminders || []).filter(r => !r.is_completed).length;
    const badge = document.getElementById('sidebarReminderBadge');
    const dot = document.getElementById('topbarReminderDot');
    if (badge) {
      badge.textContent = count;
      badge.classList.toggle('hidden', count === 0);
    }
    if (dot) {
      dot.classList.toggle('hidden', count === 0);
    }
  } catch (_) {
    // Non-blocking
  }
};


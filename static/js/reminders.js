let allReminders = [];
let currentRemFilter = 'all';

document.addEventListener('DOMContentLoaded', () => {
  const todayStr = new Date().toISOString().split('T')[0];
  const dateInput = document.getElementById('remDueDateInput');
  if (dateInput) dateInput.value = todayStr;

  loadReminders();
  setupReminderEvents();
});

async function loadReminders() {
  try {
    const data = await apiFetch('/api/reminders');
    allReminders = data.reminders || [];
    renderReminders();
    refreshReminderBadge();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderReminders() {
  const container = document.getElementById('remindersListContainer');
  const filtered = currentRemFilter === 'all'
    ? allReminders
    : allReminders.filter(r => r.reminder_type === currentRemFilter);

  if (!filtered.length) {
    container.innerHTML = `
      <div class="card p-10 text-center">
        <p class="text-slate-600 font-semibold">No reminders in this category.</p>
        <p class="text-xs text-slate-400 mt-1">Click "Refresh AI Reminders" to scan upcoming exams, daily goals, and spaced revisions.</p>
      </div>`;
    return;
  }

  container.innerHTML = filtered.map(r => {
    const typeLabel = {
      exam: 'Upcoming Exam',
      daily_study: 'Daily Study',
      pending_topic: 'Pending Topic',
      revision: 'Smart Revision',
      custom: 'Custom'
    }[r.reminder_type] || r.reminder_type;

    const prioClass = r.priority === 'high' ? 'badge-rose' : r.priority === 'medium' ? 'badge-amber' : 'badge-cyan';

    return `
      <div class="card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${r.is_completed ? 'opacity-65 bg-slate-50' : ''}">
        <div class="flex items-start gap-3.5 min-w-0">
          <button type="button" onclick="toggleReminderComplete(${r.reminder_id}, ${!r.is_completed})"
            class="mt-0.5 w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 ${r.is_completed ? 'bg-emerald-500 border-emerald-500 text-white' : 'border-slate-300 bg-white hover:border-purple-500'}">
            ${r.is_completed ? '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>' : ''}
          </button>
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2 mb-1">
              <span class="badge badge-purple">${escapeHtml(typeLabel)}</span>
              <span class="badge ${prioClass}">${escapeHtml(r.priority)}</span>
              <span class="text-xs text-slate-400">Due: ${escapeHtml(r.due_date)}</span>
            </div>
            <h4 class="text-sm font-bold ${r.is_completed ? 'line-through text-slate-400' : 'text-slate-900'}">${escapeHtml(r.title)}</h4>
            <p class="text-xs text-slate-600 mt-0.5">${escapeHtml(r.message)}</p>
          </div>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <button type="button" onclick="deleteReminder(${r.reminder_id})" class="btn btn-danger-soft btn-sm text-xs">Dismiss</button>
        </div>
      </div>`;
  }).join('');
}

function setupReminderEvents() {
  document.querySelectorAll('[data-rem-filter]').forEach(btn => {
    btn.addEventListener('click', () => {
      currentRemFilter = btn.dataset.remFilter;
      document.querySelectorAll('[data-rem-filter]').forEach(b => {
        const active = b.dataset.remFilter === currentRemFilter;
        b.className = `rem-filter-btn btn btn-sm ${active ? 'btn-navy' : 'btn-outline'}`;
      });
      renderReminders();
    });
  });

  document.getElementById('syncRemindersBtn')?.addEventListener('click', async () => {
    try {
      const res = await apiFetch('/api/reminders/sync', { method: 'POST' });
      showToast(res.message || 'AI Reminders refreshed!', 'success');
      loadReminders();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  document.getElementById('openCustomReminderBtn')?.addEventListener('click', () => {
    openModal('customReminderModal');
  });

  document.getElementById('customReminderForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await apiFetch('/api/reminders', {
        method: 'POST',
        body: JSON.stringify({
          title: document.getElementById('remTitleInput').value.trim(),
          message: document.getElementById('remMessageInput').value.trim(),
          due_date: document.getElementById('remDueDateInput').value,
          priority: document.getElementById('remPriorityInput').value
        })
      });
      closeModal('customReminderModal');
      e.target.reset();
      showToast('Reminder created!', 'success');
      loadReminders();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

window.toggleReminderComplete = async function (id, completed) {
  try {
    await apiFetch(`/api/reminders/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ is_completed: completed, is_read: true })
    });
    loadReminders();
  } catch (err) {
    showToast(err.message, 'error');
  }
};

window.deleteReminder = async function (id) {
  try {
    await apiFetch(`/api/reminders/${id}`, { method: 'DELETE' });
    showToast('Reminder dismissed.', 'success');
    loadReminders();
  } catch (err) {
    showToast(err.message, 'error');
  }
};


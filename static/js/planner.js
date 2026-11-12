let schedulesData = [];
let currentPlanView = 'daily';
let timerInterval = null;
let timerSecondsLeft = 25 * 60;
let timerRunning = false;

document.addEventListener('DOMContentLoaded', () => {
  const todayStr = new Date().toISOString().split('T')[0];
  const datePicker = document.getElementById('dailyDatePicker');
  if (datePicker) datePicker.value = todayStr;

  loadPlannerData();
  setupPlannerControls();
  setupFocusTimer();
});

async function loadPlannerData() {
  try {
    const data = await apiFetch('/api/planner/schedule');
    schedulesData = data.schedules || [];
    renderRationale(data.rationale || []);
    renderDailyView();
    renderWeeklyView();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function setupPlannerControls() {
  document.querySelectorAll('[data-plan-view]').forEach(btn => {
    btn.addEventListener('click', () => {
      currentPlanView = btn.dataset.planView;
      document.querySelectorAll('[data-plan-view]').forEach(b => {
        const active = b.dataset.planView === currentPlanView;
        b.className = `plan-view-btn px-4 py-2 rounded-lg text-sm font-bold ${active ? 'bg-[#0b1437] text-white' : 'text-slate-600'}`;
      });
      document.getElementById('dailyPlannerView').classList.toggle('hidden', currentPlanView !== 'daily');
      document.getElementById('weeklyPlannerView').classList.toggle('hidden', currentPlanView !== 'weekly');
    });
  });

  document.getElementById('dailyDatePicker')?.addEventListener('change', renderDailyView);

  document.getElementById('generatePlanBtn')?.addEventListener('click', async () => {
    try {
      const payload = {
        weekday_hours: Number(document.getElementById('weekdayHoursInput').value),
        weekend_hours: Number(document.getElementById('weekendHoursInput').value),
        preferred_time: document.getElementById('preferredTimeSelect').value,
        focus_strategy: document.getElementById('focusStrategySelect').value,
        session_duration: Number(document.getElementById('sessionDurationSelect').value),
        days: 7
      };
      const res = await apiFetch('/api/planner/generate', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      showToast(res.message || 'Smart timetable generated!', 'success');
      loadPlannerData();
      refreshReminderBadge();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  document.getElementById('adaptPlanBtn')?.addEventListener('click', async () => {
    try {
      const res = await apiFetch('/api/planner/adapt', {
        method: 'POST',
        body: JSON.stringify({
          weekday_hours: Number(document.getElementById('weekdayHoursInput').value),
          weekend_hours: Number(document.getElementById('weekendHoursInput').value),
          preferred_time: document.getElementById('preferredTimeSelect').value
        })
      });
      showToast(res.message || 'Timetable adapted dynamically!', 'success');
      loadPlannerData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

function renderDailyView() {
  const selectedDate = document.getElementById('dailyDatePicker')?.value || new Date().toISOString().split('T')[0];
  const daySessions = schedulesData.filter(s => s.study_date === selectedDate);
  const totalHrs = daySessions.reduce((acc, s) => acc + Number(s.duration_hours || 0), 0);

  document.getElementById('dailyViewTitle').textContent = `Schedule for ${selectedDate}`;
  document.getElementById('dailyTotalHoursPill').textContent = `${totalHrs.toFixed(1)} hrs planned`;

  const container = document.getElementById('dailyTimelineList');
  if (!daySessions.length) {
    container.innerHTML = `
      <div class="p-8 rounded-xl bg-slate-50 border border-dashed border-slate-300 text-center">
        <p class="text-sm font-semibold text-slate-600">No study blocks scheduled on ${escapeHtml(selectedDate)}.</p>
        <p class="text-xs text-slate-400 mt-1">Click "Generate AI Timetable" above to automatically populate your 7-day plan.</p>
      </div>`;
    return;
  }

  container.innerHTML = daySessions.map(item => {
    const isDone = item.status === 'completed';
    const isMissed = item.status === 'missed';
    const cardTone = isDone
      ? 'bg-emerald-50/70 border-emerald-200'
      : isMissed
        ? 'bg-rose-50/60 border-rose-200'
        : 'bg-white border-slate-200';
    const typeBadge = item.session_type === 'revision'
      ? 'badge-cyan'
      : item.session_type === 'exam_prep'
        ? 'badge-rose'
        : 'badge-purple';

    return `
      <div class="p-4 rounded-xl border ${cardTone} flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="flex items-start gap-3.5 min-w-0">
          <div class="w-2 h-12 rounded-full shrink-0" style="background-color: ${escapeHtml(item.color_tag || '#6d28d9')}"></div>
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-xs font-bold text-slate-500 font-mono">${escapeHtml(item.start_time)} - ${escapeHtml(item.end_time)}</span>
              <span class="badge ${typeBadge}">${escapeHtml(item.session_type.replace('_', ' '))}</span>
              ${isDone ? '<span class="badge badge-emerald">Completed</span>' : ''}
              ${isMissed ? '<span class="badge badge-rose">Missed &mdash; Ready to Adapt</span>' : ''}
            </div>
            <h4 class="text-sm font-bold text-slate-900 mt-1">${escapeHtml(item.topic_name || item.subject_name)}</h4>
            <p class="text-xs text-slate-500">${escapeHtml(item.subject_name)} &middot; ${item.duration_hours} hrs ${item.notes ? '&middot; ' + escapeHtml(item.notes) : ''}</p>
          </div>
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <button type="button" onclick="selectFocusTopic('${escapeHtml(item.topic_name || item.subject_name)}')" class="btn btn-outline btn-sm text-xs">Focus</button>
          ${!isDone ? `<button type="button" onclick="updatePlanStatus(${item.schedule_id}, 'completed')" class="btn btn-primary btn-sm text-xs">Complete</button>` : `<button type="button" onclick="updatePlanStatus(${item.schedule_id}, 'scheduled')" class="btn btn-outline btn-sm text-xs">Undo</button>`}
          ${item.status === 'scheduled' ? `<button type="button" onclick="updatePlanStatus(${item.schedule_id}, 'missed')" class="btn btn-danger-soft btn-sm text-xs">Skip</button>` : ''}
        </div>
      </div>`;
  }).join('');
}

function renderWeeklyView() {
  const container = document.getElementById('weeklyGridContainer');
  const grouped = {};
  schedulesData.forEach(s => {
    if (!grouped[s.study_date]) grouped[s.study_date] = [];
    grouped[s.study_date].push(s);
  });

  const dates = Object.keys(grouped).sort();
  if (!dates.length) {
    container.innerHTML = `<div class="md:col-span-2 xl:col-span-4 card p-10 text-center text-slate-500">Generate an AI Timetable to populate your 7-day weekly grid.</div>`;
    return;
  }

  container.innerHTML = dates.map(d => {
    const dayName = new Date(d + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    const items = grouped[d];
    const total = items.reduce((a, b) => a + Number(b.duration_hours || 0), 0);

    return `
      <div class="card p-4 flex flex-col gap-3">
        <div class="flex items-center justify-between pb-2.5 border-b border-slate-200">
          <span class="text-sm font-bold text-slate-900">${dayName}</span>
          <span class="badge badge-navy">${total.toFixed(1)}h</span>
        </div>
        <div class="space-y-2.5">
          ${items.map(it => `
            <div class="p-2.5 rounded-xl border ${it.status === 'completed' ? 'bg-emerald-50 border-emerald-200' : 'bg-slate-50 border-slate-200'}">
              <div class="flex items-center justify-between text-[11px] font-semibold text-slate-500">
                <span>${escapeHtml(it.start_time)}</span>
                <span>${it.duration_hours}h</span>
              </div>
              <p class="text-xs font-bold text-slate-900 mt-0.5 truncate">${escapeHtml(it.topic_name || it.subject_name)}</p>
              <p class="text-[11px] text-slate-500 truncate">${escapeHtml(it.subject_name)}</p>
            </div>`).join('')}
        </div>
      </div>`;
  }).join('');
}

function renderRationale(rationale) {
  const container = document.getElementById('plannerRationaleList');
  if (!rationale.length) {
    container.innerHTML = '<p>Add subjects and generate your plan to inspect how AI prioritizes each topic.</p>';
    return;
  }
  container.innerHTML = rationale.map(r => `
    <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
      <div class="flex justify-between font-bold text-slate-800">
        <span>${escapeHtml(r.topic_name)}</span>
        <span class="text-purple-600">Score ${r.priority_score}</span>
      </div>
      <p class="text-[11px] text-slate-500 mt-0.5">${escapeHtml(r.reason)}</p>
    </div>`).join('');
}

window.updatePlanStatus = async function (scheduleId, status) {
  try {
    await apiFetch(`/api/schedules/${scheduleId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status })
    });
    showToast(status === 'completed' ? 'Session logged to Progress!' : status === 'missed' ? 'Marked missed. Click "Adapt Timetable" to reschedule.' : 'Updated.', 'success');
    loadPlannerData();
  } catch (err) {
    showToast(err.message, 'error');
  }
};

window.selectFocusTopic = function (name) {
  document.getElementById('timerActiveTopic').textContent = `Focusing on: ${name}`;
  showToast(`Loaded "${name}" into Focus Timer`, 'info');
};

function setupFocusTimer() {
  const display = document.getElementById('focusTimerDisplay');
  const toggleBtn = document.getElementById('timerToggleBtn');
  const resetBtn = document.getElementById('timerResetBtn');

  function updateDisplay() {
    const mins = String(Math.floor(timerSecondsLeft / 60)).padStart(2, '0');
    const secs = String(timerSecondsLeft % 60).padStart(2, '0');
    display.textContent = `${mins}:${secs}`;
  }

  toggleBtn?.addEventListener('click', () => {
    if (timerRunning) {
      clearInterval(timerInterval);
      timerRunning = false;
      toggleBtn.textContent = 'Resume Focus';
    } else {
      timerRunning = true;
      toggleBtn.textContent = 'Pause';
      timerInterval = setInterval(() => {
        if (timerSecondsLeft > 0) {
          timerSecondsLeft -= 1;
          updateDisplay();
        } else {
          clearInterval(timerInterval);
          timerRunning = false;
          toggleBtn.textContent = 'Start Focus';
          showToast('Focus sprint finished! Great job!', 'success');
        }
      }, 1000);
    }
  });

  resetBtn?.addEventListener('click', () => {
    clearInterval(timerInterval);
    timerRunning = false;
    timerSecondsLeft = 25 * 60;
    toggleBtn.textContent = 'Start Focus';
    updateDisplay();
  });
}


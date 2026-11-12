let weeklyChartInstance = null;
let cachedSubjects = [];

document.addEventListener('DOMContentLoaded', () => {
  loadDashboard();
  setupQuickLogModal();
});

async function loadDashboard() {
  try {
    const data = await apiFetch('/api/dashboard');

    // KPIs
    document.getElementById('kpiSubjects').textContent = data.kpis.total_subjects;
    document.getElementById('kpiSubjectsMeta').textContent = `${data.kpis.upcoming_exams_count} upcoming exams scheduled`;
    document.getElementById('kpiHours').textContent = `${data.kpis.total_study_hours}h`;
    document.getElementById('kpiHoursMeta').textContent = `This week: ${data.kpis.weekly_study_hours}h logged`;
    document.getElementById('kpiCompleted').textContent = data.kpis.completed_topics;
    document.getElementById('kpiCompletedMeta').textContent = `Completion rate: ${data.kpis.completion_rate}%`;
    document.getElementById('kpiPending').textContent = data.kpis.pending_topics;
    document.getElementById('kpiPendingMeta').textContent = `Weak topics flagged: ${data.kpis.weak_topics_count}`;

    // AI Briefing Header
    document.getElementById('aiHeadline').textContent = data.briefing.headline;
    document.getElementById('aiSubtext').textContent = data.briefing.subtext;

    // Daily Progress
    const dailyPct = Math.min(100, Math.round((data.daily_progress.hours_today / (data.daily_progress.goal_hours || 1)) * 100));
    document.getElementById('dailyHoursDone').textContent = data.daily_progress.hours_today.toFixed(1);
    document.getElementById('dailyHoursGoal').textContent = data.daily_progress.goal_hours.toFixed(1);
    document.getElementById('dailyPctBadge').textContent = `${dailyPct}%`;
    document.getElementById('dailyProgressBar').style.width = `${dailyPct}%`;

    renderTodayTasks(data.today_schedule || []);
    renderWeeklyChart(data.weekly_chart || { labels: [], hours: [] });
    renderUpcomingExams(data.upcoming_exams || []);
    renderAiSuggestions(data.ai_suggestions || []);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderTodayTasks(tasks) {
  const container = document.getElementById('todayTasksList');
  if (!tasks.length) {
    container.innerHTML = `
      <div class="p-4 rounded-xl bg-slate-50 border border-dashed border-slate-300 text-center">
        <p class="text-sm text-slate-600 font-medium">No study blocks scheduled for today yet.</p>
        <a href="/planner" class="inline-block mt-2 text-xs font-bold text-purple-600 hover:underline">Generate AI Timetable &rarr;</a>
      </div>`;
    return;
  }

  container.innerHTML = tasks.map(task => {
    const done = task.status === 'completed';
    return `
      <div class="p-3 rounded-xl border ${done ? 'bg-emerald-50/60 border-emerald-200' : 'bg-white border-slate-200'} flex items-center justify-between gap-3">
        <div class="flex items-center gap-3 min-w-0">
          <button type="button" onclick="toggleScheduleDone(${task.schedule_id}, '${done ? 'scheduled' : 'completed'}')"
            class="w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 transition-colors ${done ? 'bg-emerald-500 border-emerald-500 text-white' : 'border-slate-300 hover:border-purple-500'}">
            ${done ? '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>' : ''}
          </button>
          <div class="min-w-0">
            <p class="text-sm font-semibold ${done ? 'line-through text-slate-400' : 'text-slate-900'} truncate">
              ${escapeHtml(task.topic_name || task.subject_name)}
            </p>
            <p class="text-xs text-slate-500 truncate">
              ${escapeHtml(task.subject_name)} &middot; ${escapeHtml(task.start_time)} - ${escapeHtml(task.end_time)}
            </p>
          </div>
        </div>
        <span class="badge ${task.session_type === 'revision' ? 'badge-cyan' : 'badge-purple'} shrink-0">${escapeHtml(task.session_type)}</span>
      </div>`;
  }).join('');
}

window.toggleScheduleDone = async function (scheduleId, newStatus) {
  try {
    await apiFetch(`/api/schedules/${scheduleId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus })
    });
    showToast(newStatus === 'completed' ? 'Session completed & progress updated!' : 'Session reopened.', 'success');
    loadDashboard();
    refreshReminderBadge();
  } catch (err) {
    showToast(err.message, 'error');
  }
};

function renderWeeklyChart(chartData) {
  const canvas = document.getElementById('weeklyProgressChart');
  if (!canvas || typeof Chart === 'undefined') return;
  if (weeklyChartInstance) weeklyChartInstance.destroy();

  const ctx = canvas.getContext('2d');
  const gradient = ctx.createLinearGradient(0, 0, 0, 260);
  gradient.addColorStop(0, 'rgba(109, 40, 217, 0.85)');
  gradient.addColorStop(1, 'rgba(34, 211, 238, 0.45)');

  weeklyChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: chartData.labels,
      datasets: [{
        label: 'Study Hours',
        data: chartData.hours,
        backgroundColor: gradient,
        borderRadius: 10,
        borderSkipped: false,
        maxBarThickness: 40
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0b1437',
          padding: 10,
          cornerRadius: 10,
          callbacks: {
            label: (c) => ` ${c.parsed.y} hrs studied`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: '#f1f5f9' },
          ticks: { callback: (v) => `${v}h` }
        },
        x: {
          grid: { display: false }
        }
      }
    }
  });
}

function renderUpcomingExams(exams) {
  const container = document.getElementById('upcomingExamsList');
  if (!exams.length) {
    container.innerHTML = `
      <div class="p-4 rounded-xl bg-slate-50 border border-dashed border-slate-300 text-center">
        <p class="text-sm text-slate-600">No upcoming exams recorded yet.</p>
        <a href="/subjects" class="inline-block mt-2 text-xs font-bold text-purple-600 hover:underline">Add Subject Exam Date &rarr;</a>
      </div>`;
    return;
  }

  container.innerHTML = exams.map(ex => {
    const urgent = ex.days_left <= 7;
    return `
      <div class="p-3.5 rounded-xl border border-slate-200 bg-slate-50/70 flex items-center justify-between gap-3">
        <div class="flex items-center gap-3 min-w-0">
          <div class="w-11 h-11 rounded-xl ${urgent ? 'bg-rose-50 text-rose-600 border-rose-200' : 'bg-purple-50 text-purple-700 border-purple-200'} border flex flex-col items-center justify-center shrink-0">
            <span class="text-sm font-extrabold leading-none">${ex.days_left}d</span>
            <span class="text-[10px] font-semibold uppercase">left</span>
          </div>
          <div class="min-w-0">
            <p class="text-sm font-bold text-slate-900 truncate">${escapeHtml(ex.subject_name)} &mdash; ${escapeHtml(ex.exam_title)}</p>
            <p class="text-xs text-slate-500">${escapeHtml(ex.exam_date)} &middot; Readiness: <strong>${ex.preparedness_score}%</strong></p>
          </div>
        </div>
        <span class="badge ${urgent ? 'badge-rose' : 'badge-navy'} shrink-0">${urgent ? 'Urgent' : 'On Track'}</span>
      </div>`;
  }).join('');
}

function renderAiSuggestions(suggestions) {
  const container = document.getElementById('aiSuggestionsList');
  if (!suggestions.length) {
    container.innerHTML = `<p class="text-sm text-slate-500">Add subjects and topics to unlock personalized AI suggestions.</p>`;
    return;
  }

  container.innerHTML = suggestions.map(s => {
    const badgeClass = s.severity === 'high' ? 'badge-rose' : s.severity === 'medium' ? 'badge-amber' : 'badge-cyan';
    return `
      <div class="p-4 rounded-xl border border-slate-200 bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-purple-300 transition-colors">
        <div class="space-y-1">
          <div class="flex items-center gap-2">
            <span class="badge ${badgeClass}">${escapeHtml(s.category)}</span>
            <h4 class="text-sm font-bold text-slate-900">${escapeHtml(s.title)}</h4>
          </div>
          <p class="text-xs text-slate-600 leading-relaxed">${escapeHtml(s.description)}</p>
        </div>
        ${s.action_url ? `<a href="${escapeHtml(s.action_url)}" class="btn btn-outline btn-sm shrink-0">${escapeHtml(s.action_label || 'Take Action')}</a>` : ''}
      </div>`;
  }).join('');
}

async function setupQuickLogModal() {
  const openBtn = document.getElementById('quickLogOpenBtn');
  const subjectSelect = document.getElementById('logSubjectSelect');
  const topicSelect = document.getElementById('logTopicSelect');
  const form = document.getElementById('quickLogForm');

  openBtn?.addEventListener('click', async () => {
    try {
      const res = await apiFetch('/api/subjects');
      cachedSubjects = res.subjects || [];
      if (!cachedSubjects.length) {
        showToast('Please add a subject first on the Subjects page.', 'error');
        return;
      }
      subjectSelect.innerHTML = cachedSubjects.map(s => `<option value="${s.subject_id}">${escapeHtml(s.subject_name)}</option>`).join('');
      populateTopicsForLog(subjectSelect.value);
      openModal('quickLogModal');
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  subjectSelect?.addEventListener('change', () => populateTopicsForLog(subjectSelect.value));

  function populateTopicsForLog(subjectId) {
    const subj = cachedSubjects.find(s => String(s.subject_id) === String(subjectId));
    const topics = (subj && subj.topics) || [];
    topicSelect.innerHTML = '<option value="">General subject study</option>' +
      topics.map(t => `<option value="${t.topic_id}">${escapeHtml(t.chapter_name)} — ${escapeHtml(t.topic_name)}</option>`).join('');
  }

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await apiFetch('/api/progress', {
        method: 'POST',
        body: JSON.stringify({
          subject_id: Number(subjectSelect.value),
          topic_id: topicSelect.value ? Number(topicSelect.value) : null,
          hours_studied: Number(document.getElementById('logHoursInput').value),
          focus_rating: Number(document.getElementById('logFocusSelect').value),
          notes: document.getElementById('logNotesInput').value.trim()
        })
      });
      closeModal('quickLogModal');
      form.reset();
      showToast('Study session logged!', 'success');
      loadDashboard();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}


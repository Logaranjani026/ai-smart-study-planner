let progWeeklyChart = null;
let subjectHoursChart = null;
let progSubjects = [];

document.addEventListener('DOMContentLoaded', () => {
  const todayStr = new Date().toISOString().split('T')[0];
  const dateInput = document.getElementById('progDateInput');
  if (dateInput) dateInput.value = todayStr;

  loadProgressAnalytics();
  setupProgressModal();
});

async function loadProgressAnalytics() {
  try {
    const data = await apiFetch('/api/progress/analytics');

    document.getElementById('progTodayHours').textContent = `${data.summary.today_hours.toFixed(1)}h`;
    document.getElementById('progGoalMeta').textContent = `Daily goal: ${data.summary.daily_goal_hours.toFixed(1)}h`;
    document.getElementById('progWeekHours').textContent = `${data.summary.weekly_hours.toFixed(1)}h`;
    document.getElementById('progStreak').textContent = `${data.summary.streak_days} days`;
    document.getElementById('progConsistencyRate').textContent = `14-day consistency: ${data.summary.consistency_pct}%`;
    document.getElementById('progChapters').textContent = `${data.summary.completed_chapters} / ${data.summary.total_chapters}`;
    document.getElementById('progTopicsSummary').textContent = `${data.summary.completed_topics} of ${data.summary.total_topics} topics mastered`;

    renderWeeklyActivityChart(data.weekly_chart);
    renderSubjectDistributionChart(data.subject_progress);
    renderSubjectProgressBars(data.subject_progress);
    renderConsistencyHeatmap(data.consistency_14d);
    renderRecentLogs(data.recent_logs);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderWeeklyActivityChart(chartData) {
  const canvas = document.getElementById('progressWeeklyChart');
  if (!canvas || typeof Chart === 'undefined') return;
  if (progWeeklyChart) progWeeklyChart.destroy();

  progWeeklyChart = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: chartData.labels,
      datasets: [{
        label: 'Study Hours',
        data: chartData.hours,
        borderColor: '#6d28d9',
        backgroundColor: 'rgba(34, 211, 238, 0.22)',
        fill: true,
        tension: 0.35,
        pointBackgroundColor: '#06b6d4',
        pointRadius: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
        x: { grid: { display: false } }
      }
    }
  });
}

function renderSubjectDistributionChart(subjects) {
  const canvas = document.getElementById('subjectHoursChart');
  if (!canvas || typeof Chart === 'undefined') return;
  if (subjectHoursChart) subjectHoursChart.destroy();

  subjectHoursChart = new Chart(canvas.getContext('2d'), {
    type: 'bar',
    data: {
      labels: subjects.map(s => s.subject_name),
      datasets: [{
        label: 'Hours Logged',
        data: subjects.map(s => s.hours_studied),
        backgroundColor: subjects.map(s => s.color_tag || '#6d28d9'),
        borderRadius: 8
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { beginAtZero: true, grid: { color: '#f1f5f9' } },
        y: { grid: { display: false } }
      }
    }
  });
}

function renderSubjectProgressBars(subjects) {
  const container = document.getElementById('subjectProgressList');
  if (!subjects.length) {
    container.innerHTML = '<p class="text-sm text-slate-400">No subjects added yet.</p>';
    return;
  }
  container.innerHTML = subjects.map(s => `
    <div class="space-y-1.5">
      <div class="flex items-center justify-between text-sm">
        <span class="font-bold text-slate-900">${escapeHtml(s.subject_name)}</span>
        <span class="text-xs font-semibold text-slate-500">${s.completed_topics}/${s.total_topics} topics (${s.completion_pct}%) &middot; ${s.hours_studied}h</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" style="width: ${s.completion_pct}%"></div>
      </div>
    </div>`).join('');
}

function renderConsistencyHeatmap(days) {
  const container = document.getElementById('consistencyHeatmap');
  container.innerHTML = days.map(d => {
    const hrs = d.hours;
    const cls = hrs >= 4
      ? 'bg-purple-600 text-white'
      : hrs >= 2
        ? 'bg-cyan-400 text-slate-950'
        : hrs > 0
          ? 'bg-cyan-100 text-cyan-900'
          : 'bg-slate-100 text-slate-400';
    return `
      <div title="${escapeHtml(d.date)}: ${hrs} hrs" class="p-2 rounded-lg text-center ${cls}">
        <span class="text-[10px] font-bold block">${escapeHtml(d.label)}</span>
        <span class="text-xs font-extrabold">${hrs}h</span>
      </div>`;
  }).join('');
}

function renderRecentLogs(logs) {
  const container = document.getElementById('recentLogsList');
  if (!logs.length) {
    container.innerHTML = '<p class="text-xs text-slate-400">No sessions logged yet.</p>';
    return;
  }
  container.innerHTML = logs.map(l => `
    <div class="p-2.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-2 text-xs">
      <div class="min-w-0">
        <p class="font-bold text-slate-800 truncate">${escapeHtml(l.subject_name)} ${l.topic_name ? '&mdash; ' + escapeHtml(l.topic_name) : ''}</p>
        <p class="text-slate-500 truncate">${escapeHtml(l.study_date)} &middot; Focus ${l.focus_rating}/5</p>
      </div>
      <span class="badge badge-purple shrink-0">${l.hours_studied}h</span>
    </div>`).join('');
}

function setupProgressModal() {
  const openBtn = document.getElementById('openAddProgressBtn');
  const subjSelect = document.getElementById('progSubjectSelect');
  const topicSelect = document.getElementById('progTopicSelect');

  openBtn?.addEventListener('click', async () => {
    try {
      const res = await apiFetch('/api/subjects');
      progSubjects = res.subjects || [];
      if (!progSubjects.length) {
        showToast('Please add a subject first.', 'error');
        return;
      }
      subjSelect.innerHTML = progSubjects.map(s => `<option value="${s.subject_id}">${escapeHtml(s.subject_name)}</option>`).join('');
      populateProgTopics(subjSelect.value);
      openModal('progressModal');
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  subjSelect?.addEventListener('change', () => populateProgTopics(subjSelect.value));

  function populateProgTopics(subjId) {
    const subj = progSubjects.find(s => String(s.subject_id) === String(subjId));
    const topics = (subj && subj.topics) || [];
    topicSelect.innerHTML = '<option value="">General Subject Study</option>' +
      topics.map(t => `<option value="${t.topic_id}">${escapeHtml(t.topic_name)}</option>`).join('');
  }

  document.getElementById('progressLogForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await apiFetch('/api/progress', {
        method: 'POST',
        body: JSON.stringify({
          subject_id: Number(subjSelect.value),
          topic_id: topicSelect.value ? Number(topicSelect.value) : null,
          study_date: document.getElementById('progDateInput').value,
          hours_studied: Number(document.getElementById('progHoursInput').value),
          focus_rating: Number(document.getElementById('progFocusInput').value),
          notes: document.getElementById('progNotesInput').value.trim()
        })
      });
      closeModal('progressModal');
      showToast('Study session recorded!', 'success');
      loadProgressAnalytics();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}


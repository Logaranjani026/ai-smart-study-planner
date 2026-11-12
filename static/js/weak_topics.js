let weakTopicsData = [];
let currentWeakFilter = 'all';
let weaknessChartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
  loadWeakTopicsAnalysis();
  setupWeakTopicActions();
});

async function loadWeakTopicsAnalysis() {
  try {
    const data = await apiFetch('/api/weak-topics');
    weakTopicsData = data.topics || [];

    document.getElementById('weakCountVal').textContent = data.summary.weak;
    document.getElementById('avgCountVal').textContent = data.summary.average;
    document.getElementById('strongCountVal').textContent = data.summary.strong;

    renderWeaknessChart(data.summary);
    renderRevisionQueue(data.revision_recommendations || []);
    renderTopicsGrid();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderWeaknessChart(summary) {
  const canvas = document.getElementById('weaknessChart');
  if (!canvas || typeof Chart === 'undefined') return;
  if (weaknessChartInstance) weaknessChartInstance.destroy();

  weaknessChartInstance = new Chart(canvas.getContext('2d'), {
    type: 'doughnut',
    data: {
      labels: ['Weak', 'Average', 'Strong'],
      datasets: [{
        data: [summary.weak, summary.average, summary.strong],
        backgroundColor: ['#ef4444', '#f59e0b', '#10b981'],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '66%',
      plugins: {
        legend: { position: 'bottom' }
      }
    }
  });
}

function renderRevisionQueue(recs) {
  const container = document.getElementById('revisionRecommendationsList');
  if (!recs.length) {
    container.innerHTML = '<p class="text-xs text-slate-500">All topics are currently well-retained!</p>';
    return;
  }
  container.innerHTML = recs.map(r => `
    <div class="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-3">
      <div class="min-w-0">
        <p class="text-xs font-bold text-slate-900 truncate">${escapeHtml(r.topic_name)} <span class="text-slate-500 font-normal">(${escapeHtml(r.subject_name)})</span></p>
        <p class="text-[11px] text-slate-500">${escapeHtml(r.reason)} &middot; Recommended: <strong>${escapeHtml(r.recommended_date)}</strong></p>
      </div>
      <button type="button" onclick="scheduleRevision(${r.topic_id}, '${escapeHtml(r.recommended_date)}')" class="btn btn-cyan btn-sm text-xs shrink-0">Schedule</button>
    </div>`).join('');
}

function renderTopicsGrid() {
  const container = document.getElementById('topicsAnalysisGrid');
  const filtered = currentWeakFilter === 'all'
    ? weakTopicsData
    : weakTopicsData.filter(t => t.weakness_level === currentWeakFilter);

  if (!filtered.length) {
    container.innerHTML = `<p class="text-sm text-slate-500 py-8 text-center md:col-span-2">No topics found in "${escapeHtml(currentWeakFilter)}" category.</p>`;
    return;
  }

  container.innerHTML = filtered.map(t => {
    const levelBadge = t.weakness_level === 'weak' ? 'badge-rose' : t.weakness_level === 'average' ? 'badge-amber' : 'badge-emerald';
    const stars = [1, 2, 3, 4, 5].map(val => `
      <button type="button" onclick="rateTopicUnderstanding(${t.topic_id}, ${val})"
        class="w-7 h-7 rounded-lg text-xs font-bold transition-all ${val <= t.understanding_rating ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-500 hover:bg-purple-100'}">${val}</button>
    `).join('');

    return `
      <div class="p-5 rounded-2xl border border-slate-200 bg-white space-y-3.5">
        <div class="flex items-start justify-between gap-2">
          <div>
            <span class="text-[11px] font-bold uppercase tracking-wider text-purple-600">${escapeHtml(t.subject_name)} &middot; ${escapeHtml(t.chapter_name)}</span>
            <h4 class="text-base font-bold text-slate-900 mt-0.5">${escapeHtml(t.topic_name)}</h4>
          </div>
          <span class="badge ${levelBadge} uppercase">${escapeHtml(t.weakness_level)}</span>
        </div>

        <div class="grid grid-cols-3 gap-2 text-center p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-xs">
          <div>
            <span class="text-slate-400 block">Weakness Index</span>
            <strong class="text-slate-900">${t.weakness_score}/100</strong>
          </div>
          <div>
            <span class="text-slate-400 block">Avg Quiz</span>
            <strong class="text-slate-900">${t.avg_quiz_pct !== null ? t.avg_quiz_pct + '%' : 'No Quiz'}</strong>
          </div>
          <div>
            <span class="text-slate-400 block">Next Revision</span>
            <strong class="text-cyan-700">${escapeHtml(t.next_revision_date || 'Soon')}</strong>
          </div>
        </div>

        <div>
          <label class="text-xs font-semibold text-slate-600 block mb-1.5">Your Understanding Rating (1=Low, 5=Mastered):</label>
          <div class="flex items-center gap-1.5">${stars}</div>
        </div>

        <div class="flex flex-wrap gap-2 pt-1">
          <button type="button" onclick="openDiagnosticQuiz(${t.topic_id}, '${escapeHtml(t.topic_name)}')" class="btn btn-primary btn-sm text-xs">Quick Diagnostic Quiz</button>
          <button type="button" onclick="openQuizModalForTopic(${t.topic_id})" class="btn btn-outline btn-sm text-xs">Log Quiz Score</button>
          <button type="button" onclick="scheduleRevision(${t.topic_id}, '')" class="btn btn-outline btn-sm text-xs">+ Revision Slot</button>
        </div>
      </div>`;
  }).join('');
}

function setupWeakTopicActions() {
  document.querySelectorAll('[data-weak-filter]').forEach(btn => {
    btn.addEventListener('click', () => {
      currentWeakFilter = btn.dataset.weakFilter;
      document.querySelectorAll('[data-weak-filter]').forEach(b => {
        const active = b.dataset.weakFilter === currentWeakFilter;
        b.className = `weak-filter-btn btn btn-sm ${active ? 'btn-navy' : 'btn-outline'}`;
      });
      renderTopicsGrid();
    });
  });

  document.getElementById('openLogQuizBtn')?.addEventListener('click', () => openQuizModalForTopic(null));

  document.getElementById('quizScoreForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await apiFetch('/api/quizzes', {
        method: 'POST',
        body: JSON.stringify({
          topic_id: Number(document.getElementById('quizTopicSelect').value),
          quiz_title: document.getElementById('quizTitleInput').value.trim(),
          score: Number(document.getElementById('quizScoreInput').value),
          max_score: Number(document.getElementById('quizMaxInput').value),
          difficulty_feedback: document.getElementById('quizFeedbackSelect').value
        })
      });
      closeModal('quizScoreModal');
      showToast('Quiz result saved & topic strength recalculated!', 'success');
      loadWeakTopicsAnalysis();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  document.getElementById('diagnosticQuizForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const topicId = Number(document.getElementById('diagTopicIdField').value);
    const radios = document.querySelectorAll('#diagQuestionsContainer input[type="radio"]:checked');
    let score = 0;
    radios.forEach(r => { score += Number(r.value); });
    try {
      await apiFetch('/api/quizzes', {
        method: 'POST',
        body: JSON.stringify({
          topic_id: topicId,
          quiz_title: 'AI Self-Diagnostic Check',
          score: score,
          max_score: 3,
          difficulty_feedback: score === 3 ? 'Easy' : score === 2 ? 'Medium' : 'Hard'
        })
      });
      closeModal('diagnosticQuizModal');
      showToast(`Diagnostic submitted: ${score}/3 (${Math.round((score / 3) * 100)}%)`, 'success');
      loadWeakTopicsAnalysis();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

window.rateTopicUnderstanding = async function (topicId, rating) {
  try {
    await apiFetch(`/api/topics/${topicId}/rating`, {
      method: 'PATCH',
      body: JSON.stringify({ understanding_rating: rating })
    });
    showToast(`Understanding rated ${rating}/5`, 'success');
    loadWeakTopicsAnalysis();
  } catch (err) {
    showToast(err.message, 'error');
  }
};

window.openQuizModalForTopic = function (topicId) {
  const select = document.getElementById('quizTopicSelect');
  if (!weakTopicsData.length) {
    showToast('Add subjects and topics first.', 'error');
    return;
  }
  select.innerHTML = weakTopicsData.map(t =>
    `<option value="${t.topic_id}" ${t.topic_id === topicId ? 'selected' : ''}>${escapeHtml(t.subject_name)} — ${escapeHtml(t.topic_name)}</option>`
  ).join('');
  openModal('quizScoreModal');
};

window.openDiagnosticQuiz = function (topicId, topicName) {
  document.getElementById('diagTopicIdField').value = topicId;
  document.getElementById('diagQuizHeading').textContent = `Quick Check: ${topicName}`;
  const qs = [
    `1. Can you explain the core definition and purpose of "${topicName}" without looking at notes?`,
    `2. Can you solve a standard exam-level problem on "${topicName}" from scratch?`,
    `3. Do you know the common pitfalls, edge cases, or formulas related to "${topicName}"?`
  ];
  document.getElementById('diagQuestionsContainer').innerHTML = qs.map((q, idx) => `
    <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
      <p class="text-sm font-semibold text-slate-900">${escapeHtml(q)}</p>
      <div class="flex gap-4 text-xs font-medium text-slate-700">
        <label class="flex items-center gap-1.5 cursor-pointer"><input type="radio" name="dq_${idx}" value="1" required /> Yes, confidently</label>
        <label class="flex items-center gap-1.5 cursor-pointer"><input type="radio" name="dq_${idx}" value="0.5" /> Partially</label>
        <label class="flex items-center gap-1.5 cursor-pointer"><input type="radio" name="dq_${idx}" value="0" /> Not yet</label>
      </div>
    </div>`).join('');
  openModal('diagnosticQuizModal');
};

window.scheduleRevision = async function (topicId, recommendedDate) {
  try {
    const res = await apiFetch('/api/planner/revision-slot', {
      method: 'POST',
      body: JSON.stringify({ topic_id: topicId, study_date: recommendedDate || null })
    });
    showToast(res.message || 'Revision session added to your timetable!', 'success');
    refreshReminderBadge();
  } catch (err) {
    showToast(err.message, 'error');
  }
};


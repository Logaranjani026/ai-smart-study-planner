let allSubjects = [];

document.addEventListener('DOMContentLoaded', () => {
  loadSubjects();
  setupSubjectHandlers();
});

async function loadSubjects() {
  try {
    const data = await apiFetch('/api/subjects');
    allSubjects = data.subjects || [];
    renderSubjects();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderSubjects() {
  const container = document.getElementById('subjectsGrid');
  const query = (document.getElementById('subjectSearchInput')?.value || '').toLowerCase();
  const priorityFilter = document.getElementById('priorityFilterSelect')?.value || 'all';

  const filtered = allSubjects.filter(s => {
    const matchesPriority = priorityFilter === 'all' || s.priority === priorityFilter;
    if (!matchesPriority) return false;
    if (!query) return true;
    const inSubject = s.subject_name.toLowerCase().includes(query) || (s.subject_code || '').toLowerCase().includes(query);
    const inTopics = (s.topics || []).some(t =>
      t.topic_name.toLowerCase().includes(query) || t.chapter_name.toLowerCase().includes(query)
    );
    return inSubject || inTopics;
  });

  if (!filtered.length) {
    container.innerHTML = `
      <div class="card p-10 text-center">
        <p class="text-slate-600 font-semibold">No subjects match your filter yet.</p>
        <p class="text-xs text-slate-400 mt-1">Click "Add New Subject" to organize your courses, chapters, and exam dates.</p>
      </div>`;
    return;
  }

  container.innerHTML = filtered.map(subj => {
    const topics = subj.topics || [];
    const exams = subj.exams || [];
    const completedCount = topics.filter(t => t.status === 'completed').length;
    const pct = topics.length ? Math.round((completedCount / topics.length) * 100) : 0;
    const prioBadge = subj.priority === 'High' ? 'badge-rose' : subj.priority === 'Medium' ? 'badge-amber' : 'badge-emerald';

    const examsHtml = exams.length
      ? exams.map(ex => `
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-100 text-xs font-medium text-slate-700">
            <span>${escapeHtml(ex.exam_title)}: <strong>${escapeHtml(ex.exam_date)}</strong></span>
            <button type="button" onclick="deleteExam(${ex.exam_id})" class="text-rose-500 hover:text-rose-700 font-bold" title="Delete exam">&times;</button>
          </span>`).join('')
      : '<span class="text-xs text-slate-400">No exam dates set</span>';

    const topicsHtml = topics.length
      ? topics.map(t => {
          const isDone = t.status === 'completed';
          const nextStatus = isDone ? 'pending' : 'completed';
          const weakClass = t.weakness_level === 'weak' ? 'badge-rose' : t.weakness_level === 'average' ? 'badge-amber' : 'badge-emerald';
          return `
            <div class="p-3 rounded-xl border ${isDone ? 'bg-emerald-50/40 border-emerald-200' : 'bg-slate-50/70 border-slate-200'} flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
              <div class="flex items-start gap-3 min-w-0">
                <button type="button" onclick="toggleTopicStatus(${t.topic_id}, '${nextStatus}')"
                  class="mt-0.5 w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 ${isDone ? 'bg-emerald-500 border-emerald-500 text-white' : 'border-slate-300 bg-white hover:border-purple-500'}">
                  ${isDone ? '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>' : ''}
                </button>
                <div class="min-w-0">
                  <p class="text-sm font-semibold ${isDone ? 'line-through text-slate-400' : 'text-slate-900'}">${escapeHtml(t.topic_name)}</p>
                  <p class="text-xs text-slate-500">${escapeHtml(t.chapter_name)} &middot; Est. ${t.estimated_hours}h &middot; Understanding: ${t.understanding_rating}/5</p>
                </div>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <span class="badge ${weakClass}">${escapeHtml(t.weakness_level)}</span>
                <button type="button" onclick="openEditTopicModal(${t.subject_id}, ${t.topic_id})" class="btn btn-outline btn-sm py-1 px-2 text-xs">Edit</button>
                <button type="button" onclick="deleteTopic(${t.topic_id})" class="btn btn-danger-soft btn-sm py-1 px-2 text-xs">Del</button>
              </div>
            </div>`;
        }).join('')
      : `<p class="text-xs text-slate-400 py-3 text-center border border-dashed border-slate-200 rounded-xl">No chapters or topics added yet. Add your first topic above.</p>`;

    return `
      <div class="card p-6">
        <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-200">
          <div class="flex items-start gap-3.5">
            <div class="w-3 h-12 rounded-full shrink-0" style="background-color: ${escapeHtml(subj.color_tag || '#6d28d9')}"></div>
            <div>
              <div class="flex flex-wrap items-center gap-2">
                <h3 class="text-lg font-bold text-slate-900">${escapeHtml(subj.subject_name)}</h3>
                ${subj.subject_code ? `<span class="badge badge-navy">${escapeHtml(subj.subject_code)}</span>` : ''}
                <span class="badge ${prioBadge}">${escapeHtml(subj.priority)} Priority</span>
                <span class="badge badge-purple">Difficulty ${subj.difficulty_level}/5</span>
              </div>
              <div class="flex flex-wrap items-center gap-2 mt-2">
                ${examsHtml}
              </div>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <button type="button" onclick="openAddTopicModal(${subj.subject_id})" class="btn btn-cyan btn-sm">+ Add Topic</button>
            <button type="button" onclick="openAddExamModal(${subj.subject_id})" class="btn btn-outline btn-sm">+ Exam</button>
            <button type="button" onclick="openEditSubjectModal(${subj.subject_id})" class="btn btn-outline btn-sm">Edit</button>
            <button type="button" onclick="deleteSubject(${subj.subject_id})" class="btn btn-danger-soft btn-sm">Delete</button>
          </div>
        </div>

        <div class="my-4">
          <div class="flex justify-between text-xs font-semibold text-slate-600 mb-1.5">
            <span>Syllabus Progress (${completedCount} of ${topics.length} topics completed)</span>
            <span>${pct}%</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" style="width: ${pct}%"></div>
          </div>
        </div>

        <div class="space-y-2.5">${topicsHtml}</div>
      </div>`;
  }).join('');
}

function setupSubjectHandlers() {
  document.getElementById('subjectSearchInput')?.addEventListener('input', renderSubjects);
  document.getElementById('priorityFilterSelect')?.addEventListener('change', renderSubjects);

  document.getElementById('openAddSubjectBtn')?.addEventListener('click', () => {
    document.getElementById('subjectModalTitle').textContent = 'Add New Subject';
    document.getElementById('subjectForm').reset();
    document.getElementById('subjectIdField').value = '';
    document.getElementById('subjectTargetHoursInput').value = '6';
    openModal('subjectModal');
  });

  document.getElementById('subjectForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('subjectIdField').value;
    const payload = {
      subject_name: document.getElementById('subjectNameInput').value.trim(),
      subject_code: document.getElementById('subjectCodeInput').value.trim(),
      priority: document.getElementById('subjectPriorityInput').value,
      difficulty_level: Number(document.getElementById('subjectDifficultyInput').value),
      target_hours_per_week: Number(document.getElementById('subjectTargetHoursInput').value),
      color_tag: document.getElementById('subjectColorInput').value,
      exam_date: document.getElementById('subjectExamDateInput').value || null,
      exam_title: document.getElementById('subjectExamTitleInput').value.trim() || 'Semester Exam'
    };
    try {
      if (id) {
        await apiFetch(`/api/subjects/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
        showToast('Subject updated!', 'success');
      } else {
        await apiFetch('/api/subjects', { method: 'POST', body: JSON.stringify(payload) });
        showToast('Subject added successfully!', 'success');
      }
      closeModal('subjectModal');
      loadSubjects();
      refreshReminderBadge();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  document.getElementById('topicForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const subjectId = document.getElementById('topicSubjectIdField').value;
    const topicId = document.getElementById('topicIdField').value;
    const payload = {
      chapter_name: document.getElementById('topicChapterInput').value.trim(),
      topic_name: document.getElementById('topicNameInput').value.trim(),
      estimated_hours: Number(document.getElementById('topicHoursInput').value),
      status: document.getElementById('topicStatusInput').value,
      understanding_rating: Number(document.getElementById('topicRatingInput').value)
    };
    try {
      if (topicId) {
        await apiFetch(`/api/topics/${topicId}`, { method: 'PUT', body: JSON.stringify(payload) });
        showToast('Topic updated!', 'success');
      } else {
        await apiFetch(`/api/subjects/${subjectId}/topics`, { method: 'POST', body: JSON.stringify(payload) });
        showToast('Topic added!', 'success');
      }
      closeModal('topicModal');
      loadSubjects();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  document.getElementById('examForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const subjectId = document.getElementById('examSubjectIdField').value;
    const payload = {
      subject_id: Number(subjectId),
      exam_title: document.getElementById('examTitleInput').value.trim(),
      exam_date: document.getElementById('examDateInput').value,
      exam_time: document.getElementById('examTimeInput').value,
      syllabus_notes: document.getElementById('examNotesInput').value.trim()
    };
    try {
      await apiFetch('/api/exams', { method: 'POST', body: JSON.stringify(payload) });
      closeModal('examModal');
      showToast('Exam scheduled & reminder created!', 'success');
      loadSubjects();
      refreshReminderBadge();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

window.openEditSubjectModal = function (subjectId) {
  const s = allSubjects.find(item => item.subject_id === subjectId);
  if (!s) return;
  document.getElementById('subjectModalTitle').textContent = 'Edit Subject';
  document.getElementById('subjectIdField').value = s.subject_id;
  document.getElementById('subjectNameInput').value = s.subject_name;
  document.getElementById('subjectCodeInput').value = s.subject_code || '';
  document.getElementById('subjectPriorityInput').value = s.priority;
  document.getElementById('subjectDifficultyInput').value = s.difficulty_level;
  document.getElementById('subjectTargetHoursInput').value = s.target_hours_per_week;
  document.getElementById('subjectColorInput').value = s.color_tag || '#6d28d9';
  document.getElementById('subjectExamDateInput').value = (s.exams && s.exams[0]) ? s.exams[0].exam_date : '';
  document.getElementById('subjectExamTitleInput').value = (s.exams && s.exams[0]) ? s.exams[0].exam_title : 'Semester Exam';
  openModal('subjectModal');
};

window.deleteSubject = async function (subjectId) {
  if (!confirm('Delete this subject along with its topics, exams, and scheduled sessions?')) return;
  try {
    await apiFetch(`/api/subjects/${subjectId}`, { method: 'DELETE' });
    showToast('Subject deleted.', 'success');
    loadSubjects();
  } catch (err) {
    showToast(err.message, 'error');
  }
};

window.openAddTopicModal = function (subjectId) {
  document.getElementById('topicModalTitle').textContent = 'Add Chapter & Topic';
  document.getElementById('topicForm').reset();
  document.getElementById('topicSubjectIdField').value = subjectId;
  document.getElementById('topicIdField').value = '';
  document.getElementById('topicHoursInput').value = '2';
  document.getElementById('topicRatingInput').value = '3';
  openModal('topicModal');
};

window.openEditTopicModal = function (subjectId, topicId) {
  const s = allSubjects.find(item => item.subject_id === subjectId);
  const t = s && (s.topics || []).find(item => item.topic_id === topicId);
  if (!t) return;
  document.getElementById('topicModalTitle').textContent = 'Edit Topic';
  document.getElementById('topicSubjectIdField').value = subjectId;
  document.getElementById('topicIdField').value = t.topic_id;
  document.getElementById('topicChapterInput').value = t.chapter_name;
  document.getElementById('topicNameInput').value = t.topic_name;
  document.getElementById('topicHoursInput').value = t.estimated_hours;
  document.getElementById('topicStatusInput').value = t.status;
  document.getElementById('topicRatingInput').value = t.understanding_rating;
  openModal('topicModal');
};

window.toggleTopicStatus = async function (topicId, status) {
  try {
    await apiFetch(`/api/topics/${topicId}`, {
      method: 'PUT',
      body: JSON.stringify({ status })
    });
    showToast(`Topic marked as ${status}.`, 'success');
    loadSubjects();
  } catch (err) {
    showToast(err.message, 'error');
  }
};

window.deleteTopic = async function (topicId) {
  if (!confirm('Delete this topic?')) return;
  try {
    await apiFetch(`/api/topics/${topicId}`, { method: 'DELETE' });
    showToast('Topic deleted.', 'success');
    loadSubjects();
  } catch (err) {
    showToast(err.message, 'error');
  }
};

window.openAddExamModal = function (subjectId) {
  document.getElementById('examForm').reset();
  document.getElementById('examSubjectIdField').value = subjectId;
  document.getElementById('examTimeInput').value = '09:00';
  openModal('examModal');
};

window.deleteExam = async function (examId) {
  try {
    await apiFetch(`/api/exams/${examId}`, { method: 'DELETE' });
    showToast('Exam removed.', 'success');
    loadSubjects();
  } catch (err) {
    showToast(err.message, 'error');
  }
};


document.addEventListener('DOMContentLoaded', () => {
  loadAssistantContext();
  setupChatEvents();
});

async function loadAssistantContext() {
  try {
    const [dash, subRes] = await Promise.all([
      apiFetch('/api/dashboard'),
      apiFetch('/api/subjects')
    ]);
    const contextBox = document.getElementById('assistantContextBox');
    contextBox.innerHTML = `
      <div class="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
        <div class="flex justify-between"><span>Subjects:</span><strong>${dash.kpis.total_subjects}</strong></div>
        <div class="flex justify-between"><span>Weak Topics Flagged:</span><strong class="text-rose-600">${dash.kpis.weak_topics_count}</strong></div>
        <div class="flex justify-between"><span>Upcoming Exams:</span><strong class="text-purple-600">${dash.kpis.upcoming_exams_count}</strong></div>
        <div class="flex justify-between"><span>Completion Rate:</span><strong class="text-emerald-600">${dash.kpis.completion_rate}%</strong></div>
      </div>`;

    const topicSelect = document.getElementById('explainTopicSelect');
    const options = [];
    (subRes.subjects || []).forEach(s => {
      (s.topics || []).forEach(t => {
        options.push(`<option value="${escapeHtml(t.topic_name)} (${escapeHtml(s.subject_name)})">${escapeHtml(s.subject_name)}: ${escapeHtml(t.topic_name)}</option>`);
      });
    });
    topicSelect.innerHTML = options.length
      ? options.join('')
      : '<option value="Study Techniques">Active Recall & Spaced Repetition</option>';
  } catch (err) {
    // non-fatal
  }
}

function setupChatEvents() {
  const form = document.getElementById('assistantChatForm');
  const input = document.getElementById('assistantInput');

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const msg = input.value.trim();
    if (!msg) return;
    input.value = '';
    await sendMessageToAI(msg);
  });

  document.querySelectorAll('.quick-prompt-chip').forEach(btn => {
    btn.addEventListener('click', () => sendMessageToAI(btn.dataset.prompt));
  });

  document.getElementById('explainTopicBtn')?.addEventListener('click', () => {
    const topicLabel = document.getElementById('explainTopicSelect').value;
    if (topicLabel) {
      sendMessageToAI(`Explain ${topicLabel} clearly with key concepts, study tips, and a quick practice question.`);
    }
  });

  document.getElementById('clearChatBtn')?.addEventListener('click', () => {
    const box = document.getElementById('chatMessagesContainer');
    box.innerHTML = `
      <div class="flex gap-3 max-w-2xl">
        <div class="w-8 h-8 rounded-lg bg-[#0b1437] text-cyan-300 flex items-center justify-center text-xs font-bold shrink-0">AI</div>
        <div class="chat-bubble-ai p-4 text-sm">Chat cleared. Ask any study question, concept explanation, or timetable request!</div>
      </div>`;
  });
}

async function sendMessageToAI(message) {
  appendBubble(message, 'user');
  const typingId = appendTypingBubble();

  try {
    const data = await apiFetch('/api/assistant/chat', {
      method: 'POST',
      body: JSON.stringify({ message })
    });
    document.getElementById(typingId)?.remove();
    appendBubble(data.reply, 'ai', data.suggestions || []);
  } catch (err) {
    document.getElementById(typingId)?.remove();
    showToast(err.message, 'error');
  }
}

function appendBubble(text, sender, followups = []) {
  const box = document.getElementById('chatMessagesContainer');
  const wrapper = document.createElement('div');
  if (sender === 'user') {
    wrapper.className = 'flex justify-end';
    wrapper.innerHTML = `<div class="chat-bubble-user px-4 py-3 text-sm max-w-xl">${escapeHtml(text)}</div>`;
  } else {
    wrapper.className = 'flex gap-3 max-w-2xl';
    const formatted = formatAiResponse(text);
    const chipsHtml = followups.length
      ? `<div class="flex flex-wrap gap-1.5 mt-3 pt-2 border-t border-slate-100">${followups.map(f =>
          `<button type="button" onclick="window._askChip('${escapeHtml(f).replace(/'/g, "\\'")}')" class="badge badge-purple cursor-pointer hover:opacity-80">${escapeHtml(f)}</button>`
        ).join('')}</div>`
      : '';
    wrapper.innerHTML = `
      <div class="w-8 h-8 rounded-lg bg-[#0b1437] text-cyan-300 flex items-center justify-center text-xs font-bold shrink-0">AI</div>
      <div class="chat-bubble-ai p-4 text-sm leading-relaxed space-y-2">${formatted}${chipsHtml}</div>`;
  }
  box.appendChild(wrapper);
  box.scrollTop = box.scrollHeight;
}

window._askChip = (prompt) => sendMessageToAI(prompt);

function appendTypingBubble() {
  const box = document.getElementById('chatMessagesContainer');
  const id = 'typing_' + Date.now();
  const div = document.createElement('div');
  div.id = id;
  div.className = 'flex gap-3 max-w-md';
  div.innerHTML = `
    <div class="w-8 h-8 rounded-lg bg-[#0b1437] text-cyan-300 flex items-center justify-center text-xs font-bold shrink-0">AI</div>
    <div class="chat-bubble-ai px-4 py-3 text-xs text-slate-400">Thinking and analyzing your study plan...</div>`;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return id;
}

function formatAiResponse(raw) {
  const safe = escapeHtml(raw);
  return safe
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .split('\n')
    .map(line => {
      if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
        return `<li class="ml-4 list-disc">${line.trim().slice(2)}</li>`;
      }
      return line.trim() ? `<p>${line}</p>` : '';
    })
    .join('');
}


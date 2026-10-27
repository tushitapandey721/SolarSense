/* ===== SolarSense Chatbot JS ===== */
'use strict';

const chatMessages  = document.getElementById('chatMessages');
const chatInputArea = document.getElementById('chatInputArea');
const chatForm      = document.getElementById('chatForm');
const chatInput     = document.getElementById('chatInput');
const chatSendBtn   = document.getElementById('chatSendBtn');
const chatLoading   = document.getElementById('chatLoading');
const progressBar   = document.getElementById('chatProgressBar');
const progressText  = document.getElementById('chatProgressText');
const quickReplies  = document.getElementById('quickReplies');
const recPanel      = document.getElementById('recommendationPanel');
const recGrid       = document.getElementById('recGrid');
const sidebarSteps  = document.getElementById('sidebarSteps');
const billAttachBtn = document.getElementById('billAttachBtn');
const billFileInput = document.getElementById('billFileInput');
const billUploadBanner = document.getElementById('billUploadBanner');

// State → quick-reply mapping
const QUICK_REPLIES = {
  ask_ownership: ['Owned', 'Rented'],
  ask_roof_type: ['Flat', 'Sloped', 'Mixed'],
  ask_battery:   ['Yes', 'No'],
};

// State → sidebar step index
const STATE_STEP_MAP = {
  ask_bill:      1,
  ask_name:      2,
  ask_phone:     3,
  ask_city:      4,
  ask_ownership: 5,
  ask_roof_type: 6,
  ask_roof_area: 7,
  ask_battery:   8,
  complete:      8,
};

let currentState = 'greeting';

/* ---- Helpers ---- */

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function setProgress(progress) {
  if (!progress) return;
  progressBar.style.width = `${progress.percent}%`;
  progressText.textContent = `Step ${progress.current} of ${progress.total}`;
  updateSidebarSteps(progress.current);
}

function updateSidebarSteps(currentStep) {
  if (!sidebarSteps) return;
  sidebarSteps.querySelectorAll('.s-step').forEach(el => {
    const step = parseInt(el.dataset.step);
    el.classList.remove('active', 'done');
    if (step < currentStep)  el.classList.add('done');
    if (step === currentStep) el.classList.add('active');
  });
}

function renderQuickReplies(state) {
  if (!quickReplies) return;
  quickReplies.innerHTML = '';
  const replies = QUICK_REPLIES[state];
  if (!replies) return;

  replies.forEach(label => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'qr-btn';
    btn.textContent = label;
    btn.addEventListener('click', () => {
      chatInput.value = label;
      sendMessage(label);
    });
    quickReplies.appendChild(btn);
  });
}

function renderBillAttach(state) {
  if (!billAttachBtn) return;
  billAttachBtn.style.display = state === 'ask_bill' ? '' : 'none';
  if (state !== 'ask_bill' && billUploadBanner) {
    billUploadBanner.style.display = 'none';
    billUploadBanner.innerHTML = '';
  }
}

function appendBotMessage(html, isError = false) {
  // Remove typing indicator if present
  const typing = chatMessages.querySelector('.typing-msg');
  if (typing) typing.remove();

  const wrap = document.createElement('div');
  wrap.className = 'msg msg-bot';
  wrap.innerHTML = `
    <div class="msg-avatar">
      <svg width="16" height="16" viewBox="0 0 32 32" fill="none">
        <circle cx="16" cy="16" r="8" fill="#F59E0B"/>
        <path d="M16 6v4M16 22v4M6 16h4M22 16h4" stroke="#F59E0B" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </div>
    <div class="msg-bubble ${isError ? 'error' : ''}">${html}</div>
  `;
  chatMessages.appendChild(wrap);
  scrollToBottom();
}

function appendUserMessage(text) {
  const wrap = document.createElement('div');
  wrap.className = 'msg msg-user';
  wrap.innerHTML = `<div class="msg-bubble">${escapeHtml(text)}</div>`;
  chatMessages.appendChild(wrap);
  scrollToBottom();
}

function showTypingIndicator() {
  const wrap = document.createElement('div');
  wrap.className = 'msg msg-bot typing-msg';
  wrap.innerHTML = `
    <div class="msg-avatar">
      <svg width="16" height="16" viewBox="0 0 32 32" fill="none">
        <circle cx="16" cy="16" r="8" fill="#F59E0B"/>
      </svg>
    </div>
    <div class="msg-bubble">
      <div class="typing-indicator">
        <span></span><span></span><span></span>
      </div>
    </div>
  `;
  chatMessages.appendChild(wrap);
  scrollToBottom();
  return wrap;
}

function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function setInputDisabled(disabled) {
  chatInput.disabled = disabled;
  chatSendBtn.disabled = disabled;
  if (!disabled) chatInput.focus();
}

/* ---- Recommendation rendering ---- */

function showRecommendation(rec) {
  if (!rec || !recPanel || !recGrid) return;

  chatMessages.style.display     = 'none';
  chatInputArea.style.display    = 'none';
  recPanel.style.display         = 'block';

  const cards = [
    { icon: '⚡', value: `${rec.system_size_kw} kW`, label: 'System Size' },
    { icon: '🔆', value: rec.panels_count, label: 'Solar Panels' },
    { icon: '💰', value: `PKR ${rec.monthly_savings_pkr.toLocaleString()}`, label: 'Monthly Savings', highlight: true },
    { icon: '📅', value: `${rec.payback_years} yrs`, label: 'Payback Period' },
    { icon: '🏭', value: `${rec.annual_generation_kwh.toLocaleString()} kWh`, label: 'Annual Output' },
    { icon: '🌱', value: `${rec.co2_saved_kg_per_year} kg`, label: 'CO₂ Saved/Year' },
  ];

  if (rec.battery_units > 0) {
    cards.push({ icon: '🔋', value: `${rec.battery_units} unit(s)`, label: 'Battery Backup' });
  }

  recGrid.innerHTML = `
    <div class="rec-suitability" style="grid-column: 1/-1;">
      <strong>🌞 ${rec.suitability_label} Suitability — Score: ${rec.suitability_score}/100</strong>
      <p>${rec.suitability_message}</p>
    </div>
    ${cards.map(c => `
      <div class="rec-card">
        <div class="rec-card-icon">${c.icon}</div>
        <div class="rec-card-value ${c.highlight ? 'highlight' : ''}">${c.value}</div>
        <div class="rec-card-label">${c.label}</div>
      </div>
    `).join('')}
    <div class="rec-card" style="grid-column: 1/-1; text-align: left; padding: 16px 18px;">
      <div style="font-size:.85rem;color:#64748B;margin-bottom:6px;">Estimated Total Cost</div>
      <div style="font-size:1.2rem;font-weight:800;">PKR ${rec.total_cost_pkr.toLocaleString()}</div>
    </div>
  `;
}

/* ---- API calls ---- */

async function startAssessment() {
  try {
    const res = await fetch('/api/start-assessment', { method: 'POST' });
    const data = await res.json();

    chatLoading.remove();
    chatInputArea.style.display = '';

    if (data.success && data.response) {
      const r = data.response;
      currentState = r.state || 'greeting';
      appendBotMessage(r.message);
      setProgress(r.progress);
      renderQuickReplies(currentState);
      renderBillAttach(currentState);
    }
  } catch {
    if (chatLoading) chatLoading.innerHTML = '<p style="color:#EF4444">Failed to connect. Please refresh.</p>';
  }
}

async function sendMessage(text) {
  const msg = text || chatInput.value.trim();
  if (!msg) return;

  chatInput.value = '';
  quickReplies.innerHTML = '';
  appendUserMessage(msg);
  setInputDisabled(true);

  const typingEl = showTypingIndicator();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg }),
    });

    const data = await res.json();
    typingEl.remove();

    if (!data.success) {
      appendBotMessage(data.error || 'An error occurred. Please try again.', true);
      setInputDisabled(false);
      return;
    }

    const r = data.response;
    currentState = r.state || currentState;
    appendBotMessage(r.message, r.error);
    setProgress(r.progress);

    if (r.complete && r.recommendation) {
      // Small delay for UX
      setTimeout(() => showRecommendation(r.recommendation), 1200);
    } else {
      renderQuickReplies(currentState);
      renderBillAttach(currentState);
      setInputDisabled(false);
    }
  } catch {
    typingEl.remove();
    appendBotMessage('Connection error. Please check your connection and try again.', true);
    setInputDisabled(false);
  }
}

/* ---- Bill upload ---- */

async function handleBillUpload(file) {
  billUploadBanner.style.display = '';
  billUploadBanner.innerHTML = `
    <div class="bill-banner-row">
      <div class="bill-spinner"></div>
      <span>Reading your bill…</span>
    </div>`;

  const formData = new FormData();
  formData.append('bill', file);

  try {
    const res = await fetch('/api/upload-bill', { method: 'POST', body: formData });
    const data = await res.json();

    if (!data.success) {
      billUploadBanner.innerHTML = `
        <div class="bill-banner-row bill-banner-error">
          <span>⚠️ ${escapeHtml(data.error || 'Could not read this bill.')}</span>
          <button type="button" class="bill-banner-dismiss" id="billBannerDismiss">Dismiss</button>
        </div>`;
      document.getElementById('billBannerDismiss')?.addEventListener('click', () => {
        billUploadBanner.style.display = 'none';
      });
      return;
    }

    const d = data.data;
    const amount = Math.round(d.monthly_bill).toLocaleString();
    const confidenceNote = d.confidence === 'low'
      ? ' (please double check this)'
      : '';

    billUploadBanner.innerHTML = `
      <div class="bill-banner-row">
        <span>📄 Found <strong>PKR ${amount}/month</strong>${confidenceNote}${d.bill_month ? ` for ${escapeHtml(d.bill_month)}` : ''}.</span>
      </div>
      <div class="bill-banner-actions">
        <button type="button" class="bill-banner-btn primary" id="billUseBtn">Use PKR ${amount}</button>
        <button type="button" class="bill-banner-btn" id="billManualBtn">Enter manually</button>
      </div>`;

    document.getElementById('billUseBtn')?.addEventListener('click', () => {
      billUploadBanner.style.display = 'none';
      billUploadBanner.innerHTML = '';
      sendMessage(String(Math.round(d.monthly_bill)));
    });
    document.getElementById('billManualBtn')?.addEventListener('click', () => {
      billUploadBanner.style.display = 'none';
      billUploadBanner.innerHTML = '';
      chatInput.focus();
    });
  } catch {
    billUploadBanner.innerHTML = `
      <div class="bill-banner-row bill-banner-error">
        <span>⚠️ Connection error while reading your bill. Please try again or enter it manually.</span>
      </div>`;
  }
}

/* ---- Event listeners ---- */

if (chatForm) {
  chatForm.addEventListener('submit', e => {
    e.preventDefault();
    sendMessage();
  });
}

if (billAttachBtn && billFileInput) {
  billAttachBtn.addEventListener('click', () => billFileInput.click());
  billFileInput.addEventListener('change', () => {
    const file = billFileInput.files[0];
    billFileInput.value = ''; // allow re-selecting the same file later
    if (file) handleBillUpload(file);
  });
}

/* ---- Initialise ---- */
startAssessment();

/* ═══════════════════════════════════════════════════
   深圳 AI 外贸助手  ·  Frontend Logic
   ═══════════════════════════════════════════════════ */

'use strict';

// ── Utils ──────────────────────────────────────────

function $(id) { return document.getElementById(id); }
const BASE_PATH = window.APP_BASE || '';
function withBasePath(path) {
  if (!path.startsWith('/')) return `${BASE_PATH}/${path}`;
  return `${BASE_PATH}${path}`;
}

function showMsg(el, text, type = 'info') {
  el.textContent = text;
  el.className = `inline-msg ${type}`;
  el.classList.remove('hidden');
}

function hideMsg(el) { el.classList.add('hidden'); }

let toastTimer;
function toast(msg) {
  const t = $('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2600);
}

function setLoading(btn, loading, label = null) {
  if (loading) {
    btn._origHTML = btn.innerHTML;
    btn.innerHTML = `<span class="spinner"></span>${label ? `<span>${label}</span>` : ''}`;
    btn.disabled = true;
  } else {
    if (btn._origHTML) btn.innerHTML = btn._origHTML;
    btn.disabled = false;
  }
}

async function apiPost(url, body, isFormData = false) {
  const opts = { method: 'POST' };
  if (isFormData) {
    opts.body = body;
  } else {
    opts.headers = { 'Content-Type': 'application/json' };
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

async function apiGet(url) {
  const res = await fetch(url);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}


// ── Tab Navigation ─────────────────────────────────

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    $('tab-' + tab).classList.add('active');
    if (tab === 'history') loadHistory();
  });
});


// ── Health Check ───────────────────────────────────

async function checkHealth() {
  const dot  = $('statusDot');
  const text = $('statusText');
  try {
    const data = await apiGet(withBasePath('/api/health'));
    dot.className  = 'status-dot online';
    text.textContent = data.app || '已连接';
  } catch {
    dot.className  = 'status-dot offline';
    text.textContent = '连接失败';
  }
}
checkHealth();


// ── Document Upload ────────────────────────────────

const uploadZone = $('uploadZone');
const fileInput  = $('fileInput');

uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('drag-over'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f) doUpload(f);
});
fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) doUpload(fileInput.files[0]);
});

$('uploadBtn').addEventListener('click', () => fileInput.click());

async function doUpload(file) {
  const btn = $('uploadBtn');
  const msg = $('uploadMsg');
  setLoading(btn, true, '上传中…');
  hideMsg(msg);

  const fd = new FormData();
  fd.append('file', file);
  try {
    const data = await apiPost(withBasePath('/api/docs/upload'), fd, true);
    showMsg(msg, `已上传：${data.file_name}`, 'success');
    toast('文档上传成功');
    await refreshDocList();
  } catch (err) {
    showMsg(msg, `错误：${err.message}`, 'error');
  } finally {
    setLoading(btn, false);
    fileInput.value = '';
  }
}


// ── Seed Demo Docs ─────────────────────────────────

$('seedBtn').addEventListener('click', async () => {
  const btn = $('seedBtn');
  const msg = $('uploadMsg');
  setLoading(btn, true, '加载中…');
  hideMsg(msg);
  try {
    const data = await apiPost(withBasePath('/api/demo/seed'), {});
    if (data.count === 0) {
      showMsg(msg, 'Demo 文档已全部加载，无需重复', 'info');
    } else {
      showMsg(msg, `已加载 ${data.count} 个 Demo 文档：${data.loaded.join('、')}`, 'success');
      toast(`已加载 ${data.count} 个 Demo 文档`);
      await refreshDocList();
    }
  } catch (err) {
    showMsg(msg, `错误：${err.message}`, 'error');
  } finally {
    setLoading(btn, false);
  }
});


// ── Refresh Doc List ───────────────────────────────

async function refreshDocList() {
  try {
    const docs = await apiGet(withBasePath('/api/docs'));
    const list = $('docList');
    if (docs.length === 0) {
      list.innerHTML = '<li class="doc-empty">暂无文档 — 点击上传或加载 Demo</li>';
      return;
    }
    list.innerHTML = docs.map(doc => `
      <li class="doc-item">
        <svg class="doc-icon" width="13" height="13" viewBox="0 0 13 13" fill="none">
          <path d="M2 1h7l2 2v9H2V1z" stroke="currentColor" stroke-width="1.2"/>
          <path d="M8 1v2h2" stroke="currentColor" stroke-width="1.2"/>
        </svg>
        <span class="doc-name">${escHtml(doc.file_name)}</span>
        <span class="doc-type">${escHtml(doc.file_type)}</span>
      </li>`).join('');
  } catch { /* silent */ }
}


// ── Knowledge Base Q&A ─────────────────────────────

async function doAsk(question) {
  if (!question.trim()) return;
  const btn    = $('qaBtn');
  const result = $('qaResult');
  const answer = $('qaAnswer');
  const sources = $('qaSources');

  setLoading(btn, true, '检索中…');
  result.classList.add('hidden');

  try {
    const data = await apiPost(withBasePath('/api/ask'), { question });
    answer.textContent = data.answer || '（无回答）';
    sources.innerHTML = (data.sources || []).map(s =>
      `<span class="qa-source-chip">来源：${escHtml(s.source_label)}</span>`
    ).join('');
    result.classList.remove('hidden');
  } catch (err) {
    answer.textContent = `错误：${err.message}`;
    sources.innerHTML = '';
    result.classList.remove('hidden');
  } finally {
    setLoading(btn, false);
  }
}

$('qaBtn').addEventListener('click', () => doAsk($('qaInput').value));
$('qaInput').addEventListener('keydown', e => { if (e.key === 'Enter') doAsk($('qaInput').value); });

document.querySelectorAll('.chip').forEach(chip => {
  chip.addEventListener('click', () => {
    const q = chip.dataset.q;
    $('qaInput').value = q;
    doAsk(q);
  });
});


// ── Inquiry Submission ─────────────────────────────

$('inqSubmit').addEventListener('click', async () => {
  const body = $('inqBody').value.trim();
  if (!body) { toast('请填写询盘正文'); return; }

  const btn = $('inqSubmit');
  const msg = $('inqMsg');
  setLoading(btn, true, 'AI 分析中…');
  hideMsg(msg);
  $('inqPlaceholder').style.display = 'flex';
  $('inqResult').classList.add('hidden');

  const payload = {
    source_channel: $('inqChannel').value || 'email',
    company:        $('inqCompany').value || null,
    sender_name:    $('inqName').value    || null,
    sender_email:   $('inqEmail').value   || null,
    subject:        $('inqSubject').value || null,
    body,
  };

  try {
    const data = await apiPost(withBasePath('/api/inquiries'), payload);
    renderInquiryResult(data);
    showMsg(msg, '分析完成', 'success');
    setTimeout(() => hideMsg(msg), 2000);
  } catch (err) {
    showMsg(msg, `错误：${err.message}`, 'error');
  } finally {
    setLoading(btn, false);
  }
});


function renderInquiryResult(d) {
  // Grade badge
  const grade = (d.lead_grade || 'C').toUpperCase();
  const badge = $('resBadge');
  badge.textContent = grade;
  badge.className = `grade-badge grade-${grade.toLowerCase()}`;
  $('resScore').textContent = `${d.lead_score ?? 0} 分`;

  // Suggested action
  $('resAction').textContent = d.suggested_action || '—';

  // Specs from analysis_json
  const specsEl = $('resSpecs');
  const section = $('specsSection');
  try {
    const analysis = JSON.parse(d.analysis_json || '{}');
    const specs = analysis.specs || {};
    const entries = Object.entries(specs).filter(([, v]) => v && (typeof v === 'string' ? v.trim() : (Array.isArray(v) ? v.length > 0 : true)));
    if (entries.length > 0) {
      specsEl.innerHTML = entries.map(([k, v]) => {
        const label = {
          model: '型号', quantity: '数量', target_market: '目标市场', certification: '认证要求'
        }[k] || k;
        const value = Array.isArray(v) ? v.join(', ') : v;
        return `<div class="spec-item"><div class="spec-key">${escHtml(label)}</div><div class="spec-val">${escHtml(value)}</div></div>`;
      }).join('');
      section.style.display = 'block';
    } else {
      section.style.display = 'none';
    }
  } catch {
    section.style.display = 'none';
  }

  // Reply
  $('resSubject').textContent = d.reply_subject ? `主题：${d.reply_subject}` : '';
  $('resBody').textContent    = d.reply_body_en || '（无回复草稿）';

  // Raw JSON
  try {
    $('resJson').textContent = JSON.stringify(JSON.parse(d.analysis_json || '{}'), null, 2);
  } catch {
    $('resJson').textContent = d.analysis_json || '';
  }

  // Show result
  $('inqPlaceholder').style.display = 'none';
  $('inqResult').classList.remove('hidden');
}


// ── Copy Reply ─────────────────────────────────────

$('copyReplyBtn').addEventListener('click', async () => {
  const subject = $('resSubject').textContent.replace(/^主题：/, '');
  const body    = $('resBody').textContent;
  const full    = subject ? `Subject: ${subject}\n\n${body}` : body;
  try {
    await navigator.clipboard.writeText(full);
    toast('已复制回复内容');
    const btn = $('copyReplyBtn');
    btn.textContent = '已复制';
    setTimeout(() => { btn.textContent = '复制回复'; }, 2000);
  } catch {
    toast('复制失败，请手动选择文本');
  }
});


// ── History ────────────────────────────────────────

async function loadHistory() {
  const listEl = $('historyList');
  try {
    const items = await apiGet(withBasePath('/api/inquiries'));
    if (items.length === 0) {
      listEl.innerHTML = '<div class="history-empty">暂无询盘记录</div>';
      return;
    }
    listEl.innerHTML = items.map(item => {
      const grade = (item.lead_grade || 'C').toLowerCase();
      const subject = escHtml(item.subject || 'Untitled Inquiry');
      const company = escHtml(item.company || '未知公司');
      const email   = escHtml(item.sender_email || '无邮箱');
      const channel = escHtml(item.source_channel || 'form');
      const action  = item.suggested_action ? `<div class="history-action">${escHtml(item.suggested_action)}</div>` : '';
      return `
        <div class="history-item">
          <div class="grade-badge grade-sm grade-${grade}">${item.lead_grade || 'C'}</div>
          <div class="history-body">
            <div class="history-top">
              <span class="history-title">${subject}</span>
              <span class="history-score">${item.lead_score ?? 0}<small> 分</small></span>
            </div>
            <div class="history-meta">
              <span>${company}</span>
              <span class="dot">·</span>
              <span>${email}</span>
              <span class="dot">·</span>
              <span class="channel-tag">${channel}</span>
            </div>
            ${action}
          </div>
        </div>`;
    }).join('');
  } catch (err) {
    listEl.innerHTML = `<div class="history-empty">加载失败：${escHtml(err.message)}</div>`;
  }
}

$('refreshHistory').addEventListener('click', () => {
  toast('刷新中…');
  loadHistory();
});


// ── Helpers ────────────────────────────────────────

function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

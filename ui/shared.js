// ── State ──────────────────────────────────────────────────────────────────
const BASE = window.location.origin;
const WS_BASE = BASE.replace(/^http/, 'ws');
const MAX_DEBUG = 50;

const channels = {
  whatsapp: { ws: null, retryDelay: 1000, retryTimer: null, lastMsgId: null },
  instagram: { ws: null, retryDelay: 1000, retryTimer: null, lastMsgId: null },
};

// Canais ativos nesta página. index.html usa ambos (default);
// whatsapp.html define window.CHANNELS = ['whatsapp'] antes de carregar shared.js.
const CHANNELS = (window.CHANNELS && window.CHANNELS.length)
  ? window.CHANNELS
  : ['whatsapp', 'instagram'];

// ── Boot ───────────────────────────────────────────────────────────────────
async function boot() {
  const info = await fetch('/info').then(r => r.json()).catch(() => null);
  if (!info) return;

  const base = info.base_url;
  for (const ch of CHANNELS) {
    const pre = ch === 'whatsapp' ? 'wpp' : 'ig';
    setText(`${pre}-callback-url`, info.channels[ch].callback_url);
    setText(`${pre}-verify-url`,   info.channels[ch].webhook_verification_url);
  }

  // load server-side secrets (from /config endpoint)
  const cfg = await fetch('/config').then(r => r.json()).catch(() => null);

  // load persisted info from /info for secrets
  const settingsRes = await fetch('/settings-info').then(r=>r.json()).catch(()=>null);
  if (settingsRes) {
    setText('wpp-verify-token', settingsRes.verify_token);
    setText('wpp-app-secret',   settingsRes.app_secret);
    setText('ig-verify-token',  settingsRes.verify_token);
    setText('ig-app-secret',    settingsRes.app_secret);
  }

  if (cfg) {
    for (const [ch, data] of Object.entries(cfg)) {
      if (!CHANNELS.includes(ch)) continue;
      const pre = ch === 'whatsapp' ? 'wpp' : 'ig';
      if (data.configured) {
        setInput(`${pre}-webhook-url`, data.webhook_url);
        setInput(`${pre}-user-name`,   data.user_name);
        setInput(`${pre}-identifier`,  data.identifier);
        if (ch === 'whatsapp' && data.phone_number_id) {
          setInput('wpp-phone-number-id', data.phone_number_id);
        }
        updateHeader(ch, data.user_name, data.identifier);
        setSendEnabled(ch, true);
      }
    }
  }

  // Pre-fill form fields from localStorage (includes unconfigured channels)
  for (const ch of CHANNELS) _fillFormFromStorage(ch);

  restoreDebugState();
  for (const ch of CHANNELS) connectWS(ch);
}

// ── WebSocket ──────────────────────────────────────────────────────────────
function connectWS(ch) {
  const state = channels[ch];
  if (state.ws) { state.ws.onclose = null; state.ws.close(); }

  setDot(ch, 'reconnecting');
  const ws = new WebSocket(`${WS_BASE}/ws/${ch}`);
  state.ws = ws;

  ws.onopen = () => {
    state.retryDelay = 1000;
    setDot(ch, 'connected');
    // keepalive ping every 25s
    state.pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ping: true}));
    }, 25000);
  };

  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    handleWsMessage(ch, msg);
  };

  ws.onclose = () => {
    clearInterval(state.pingInterval);
    setDot(ch, 'reconnecting');
    state.retryTimer = setTimeout(() => {
      state.retryDelay = Math.min(state.retryDelay * 2, 30000);
      connectWS(ch);
    }, state.retryDelay);
  };

  ws.onerror = () => ws.close();
}

function handleWsMessage(ch, msg) {
  switch (msg.type) {
    case 'sent':
      appendMsg(ch, 'sent', msg.text, msg.ts, msg.msg_type, msg.url, msg.caption, msg.filename);
      hideEmpty(ch);
      break;
    case 'received':
      hideTyping(ch);
      appendMsg(ch, 'recv', msg.text, msg.ts, msg.msg_type, msg.url, msg.caption, msg.filename);
      break;
    case 'typing':
      if (msg.status) showTyping(ch); else hideTyping(ch);
      break;
    case 'status':
      updateReceipt(ch, msg.status);
      break;
    case 'error':
      showError(ch, msg.text);
      break;
    case 'history_cleared':
      clearMessages(ch);
      break;
    case 'debug':
      addDebugEntry(ch, msg.direction, msg.payload, msg.http_status);
      break;
  }
}

// ── Message rendering ──────────────────────────────────────────────────────
let msgSeq = 0;

function appendMsg(ch, dir, text, ts, msgType, url, caption, filename) {
  const container = document.getElementById(ch === 'whatsapp' ? 'wpp-messages' : 'ig-messages');
  const isWpp = ch === 'whatsapp';
  const id = `msg-${++msgSeq}`;

  const row = document.createElement('div');
  row.className = `msg-row ${dir}`;
  row.id = id;

  const bubble = document.createElement('div');
  bubble.className = `bubble ${dir}`;

  if (msgType && msgType !== 'text') {
    bubble.appendChild(_buildMediaContent(msgType, url || text, caption, filename));
  } else {
    const textNode = document.createElement('div');
    textNode.className = 'bubble-text';
    textNode.innerHTML = formatWaText(text);
    bubble.appendChild(textNode);
  }

  const meta = document.createElement('div');
  meta.className = 'bubble-meta';

  const timeSpan = document.createElement('span');
  timeSpan.className = 'bubble-time';
  timeSpan.textContent = ts;
  meta.appendChild(timeSpan);

  if (isWpp && dir === 'sent') {
    const receipt = document.createElement('span');
    receipt.className = 'receipt sent';
    receipt.textContent = '✓';
    receipt.id = `receipt-${id}`;
    meta.appendChild(receipt);
    channels['whatsapp'].lastMsgId = id;
  }

  bubble.appendChild(meta);
  row.appendChild(bubble);
  container.appendChild(row);
  scrollBottom(container);
}

// ── WhatsApp-style audio player helpers ────────────────────────────────────

function _seededRng(seed) {
  let s = (seed ^ 0xDEADBEEF) >>> 0;
  return () => { s = Math.imul(s ^ (s >>> 15), s | 1) ^ Math.imul(s ^ (s >>> 7), s | 61); return ((s ^ (s >>> 14)) >>> 0) / 0xFFFFFFFF; };
}

function _svgPlay()  { return '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>'; }
function _svgPause() { return '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>'; }

function _buildAudioPlayer(url) {
  const N = 35;
  const audio = new Audio(url);
  const wrap  = document.createElement('div');
  wrap.className = 'wa-audio';

  const btn = document.createElement('button');
  btn.className = 'wa-audio-play';
  btn.innerHTML = _svgPlay();
  wrap.appendChild(btn);

  const body = document.createElement('div');
  body.className = 'wa-audio-body';

  const wave = document.createElement('div');
  wave.className = 'wa-audio-wave';
  const rng  = _seededRng(url.split('').reduce((a, c) => (a * 31 + c.charCodeAt(0)) | 0, 0));
  const bars = Array.from({ length: N }, () => {
    const b = document.createElement('div');
    b.className = 'wa-audio-bar';
    b.style.height = `${4 + Math.round(rng() * 14)}px`;
    wave.appendChild(b);
    return b;
  });
  body.appendChild(wave);

  const timeEl = document.createElement('div');
  timeEl.className = 'wa-audio-time';
  timeEl.textContent = '0:00';
  body.appendChild(timeEl);
  wrap.appendChild(body);

  const fmt = s => { const m = Math.floor(s / 60); return `${m}:${String(Math.floor(s % 60)).padStart(2,'0')}`; };

  function syncBars() {
    const pct = audio.duration ? audio.currentTime / audio.duration : 0;
    const on  = Math.floor(pct * N);
    bars.forEach((b, i) => b.classList.toggle('wa-on', i < on));
    timeEl.textContent = fmt(audio.currentTime);
  }

  audio.addEventListener('loadedmetadata', () => { timeEl.textContent = fmt(audio.duration); });
  audio.addEventListener('timeupdate', syncBars);
  audio.addEventListener('ended', () => {
    btn.innerHTML = _svgPlay();
    bars.forEach(b => b.classList.remove('wa-on'));
    timeEl.textContent = fmt(audio.duration || 0);
  });

  btn.addEventListener('click', () => {
    if (audio.paused) { audio.play(); btn.innerHTML = _svgPause(); }
    else              { audio.pause(); btn.innerHTML = _svgPlay(); }
  });

  wave.addEventListener('click', e => {
    if (!audio.duration) return;
    const r = wave.getBoundingClientRect();
    audio.currentTime = ((e.clientX - r.left) / r.width) * audio.duration;
    syncBars();
  });

  return wrap;
}

// ── Media content builder ──────────────────────────────────────────────────

function _buildMediaContent(tipo, url, caption, filename) {
  const wrap = document.createElement('div');
  if (tipo === 'image') {
    const img = document.createElement('img');
    img.src = url; img.className = 'media-img';
    img.onclick = () => window.open(url, '_blank');
    wrap.appendChild(img);
  } else if (tipo === 'audio') {
    wrap.appendChild(_buildAudioPlayer(url));
  } else {
    const doc = document.createElement('div');
    doc.className = 'media-doc';
    doc.innerHTML = `<span class="media-doc-icon">📄</span><span class="media-doc-name">${escHtml(filename || url)}</span>`;
    doc.onclick = () => window.open(url, '_blank');
    doc.style.cursor = 'pointer';
    wrap.appendChild(doc);
  }
  if (caption) {
    const cap = document.createElement('div');
    cap.className = 'media-caption';
    cap.textContent = caption;
    wrap.appendChild(cap);
  }
  return wrap;
}

function updateReceipt(ch, status) {
  if (ch !== 'whatsapp') return;
  const msgId = channels['whatsapp'].lastMsgId;
  if (!msgId) return;
  const receipt = document.getElementById(`receipt-${msgId}`);
  if (!receipt) return;
  if (status === 'delivered') { receipt.textContent = '✓✓'; receipt.className = 'receipt delivered'; }
  if (status === 'read')      { receipt.textContent = '✓✓'; receipt.className = 'receipt read'; }
}

function showTyping(ch) {
  const id = `typing-${ch}`;
  if (document.getElementById(id)) return;
  const container = document.getElementById(ch === 'whatsapp' ? 'wpp-messages' : 'ig-messages');
  const row = document.createElement('div');
  row.className = 'typing-row';
  row.id = id;
  row.innerHTML = `<div class="typing-bubble"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>`;
  container.appendChild(row);
  scrollBottom(container);
}

function hideTyping(ch) {
  const el = document.getElementById(`typing-${ch}`);
  if (el) el.remove();
}

function showError(ch, text) {
  const container = document.getElementById(ch === 'whatsapp' ? 'wpp-messages' : 'ig-messages');
  const row = document.createElement('div');
  row.className = 'msg-row';
  row.style.justifyContent = 'center';
  row.innerHTML = `<div style="background:#2d1b1b;color:#fc8181;font-size:.72rem;border-radius:8px;padding:4px 10px;max-width:90%">⚠ ${escHtml(text)}</div>`;
  container.appendChild(row);
  scrollBottom(container);
}

function clearMessages(ch) {
  const id = ch === 'whatsapp' ? 'wpp-messages' : 'ig-messages';
  const emptyId = ch === 'whatsapp' ? 'wpp-empty' : 'ig-empty';
  const el = document.getElementById(id);
  el.innerHTML = `<div class="debug-empty" id="${emptyId}" ${ch==='instagram'?'style="color:#8e8e8e"':''}>Configure o canal e envie uma mensagem.</div>`;
}

function hideEmpty(ch) {
  const id = ch === 'whatsapp' ? 'wpp-empty' : 'ig-empty';
  const el = document.getElementById(id);
  if (el) el.remove();
}

// ── Sending ────────────────────────────────────────────────────────────────
function sendMsg(ch) {
  const pre = ch === 'whatsapp' ? 'wpp' : 'ig';
  const field = document.getElementById(`${pre}-field`);
  const text = field.value.trim();
  const media = _pendingMedia[ch];

  if (!media && !text) return;

  const state = channels[ch];
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;

  if (media?.uploadUrl) {
    state.ws.send(JSON.stringify({
      media_type: media.mediaType,
      url: media.uploadUrl,
      filename: media.filename,
      mime: media.mime || '',
      caption: text,
    }));
    cancelMedia(ch);
  } else {
    state.ws.send(JSON.stringify({ text }));
    showTyping(ch);
    setTimeout(() => hideTyping(ch), 10000);
  }

  field.value = '';
  field.style.height = 'auto';
  _updateSendMic(pre);
}

function handleKey(e, ch) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMsg(ch); }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 80) + 'px';
}

// ── Config ─────────────────────────────────────────────────────────────────
async function saveConfig(ch) {
  const pre = ch === 'whatsapp' ? 'wpp' : 'ig';
  let valid = true;

  const webhookUrl    = document.getElementById(`${pre}-webhook-url`).value.trim();
  const userName      = document.getElementById(`${pre}-user-name`).value.trim();
  const identifier    = document.getElementById(`${pre}-identifier`).value.trim();
  const phoneNumberId = ch === 'whatsapp'
    ? document.getElementById('wpp-phone-number-id').value.trim()
    : '';

  valid = validateUrl(`${pre}-webhook-url`, webhookUrl) && valid;
  valid = validateRequired(`${pre}-user-name`, userName) && valid;
  valid = validateDigits(`${pre}-identifier`, identifier) && valid;
  if (!valid) return;

  const res = await fetch(`/config/${ch}`, {
    method: 'PATCH',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ webhook_url: webhookUrl, user_name: userName, identifier, phone_number_id: phoneNumberId }),
  }).catch(() => null);

  if (!res || !res.ok) {
    alert('Erro ao salvar configuração'); return;
  }

  // test webhook reachability
  const statusEl = document.getElementById(`${pre}-wh-status`);
  try {
    const ping = await fetch(webhookUrl, { method: 'HEAD', signal: AbortSignal.timeout(3000) });
    statusEl.className = 'webhook-status ok';
  } catch {
    statusEl.className = 'webhook-status err';
  }

  updateHeader(ch, userName, identifier);
  setSendEnabled(ch, true);
  togglePanel(`cfg-${ch}`);

  const saved = JSON.parse(localStorage.getItem('wig-config') || '{}');
  saved[ch] = { webhook_url: webhookUrl, user_name: userName, identifier, phone_number_id: phoneNumberId };
  localStorage.setItem('wig-config', JSON.stringify(saved));
}

async function clearChat(ch) {
  await fetch(`/history/${ch}`, { method: 'DELETE' });
  clearMessages(ch);
}

// ── UI helpers ─────────────────────────────────────────────────────────────
function toggleConfig(ch) { togglePanel(`cfg-${ch}`); }

function togglePanel(id) {
  const body = document.getElementById(`${id}-body`);
  const toggle = document.getElementById(`${id}-toggle`);
  const isOpen = body.classList.contains('open');
  body.classList.toggle('open', !isOpen);
  toggle.classList.toggle('open', !isOpen);
  // persist debug panel state
  if (id.startsWith('dbg-')) {
    const ch = id.replace('dbg-', '');
    const state = JSON.parse(localStorage.getItem('wig-debug-open') || '{}');
    state[ch] = !isOpen;
    localStorage.setItem('wig-debug-open', JSON.stringify(state));
  }
}

function restoreDebugState() {
  const state = JSON.parse(localStorage.getItem('wig-debug-open') || '{}');
  for (const [ch, open] of Object.entries(state)) {
    if (open && CHANNELS.includes(ch)) togglePanel(`dbg-${ch}`);
  }
}

function _fillFormFromStorage(ch) {
  const saved = JSON.parse(localStorage.getItem('wig-config') || '{}');
  const data = saved[ch];
  const pre = ch === 'whatsapp' ? 'wpp' : 'ig';
  const btn = document.getElementById(`${pre}-restore-btn`);
  if (!data || !data.webhook_url) { if (btn) btn.style.display = 'none'; return; }
  setInput(`${pre}-webhook-url`, data.webhook_url || '');
  setInput(`${pre}-user-name`,   data.user_name   || '');
  setInput(`${pre}-identifier`,  data.identifier  || '');
  if (ch === 'whatsapp') setInput('wpp-phone-number-id', data.phone_number_id || '');
  if (btn) btn.style.display = '';
}

function restoreFormFromStorage(ch) {
  _fillFormFromStorage(ch);
  const pre = ch === 'whatsapp' ? 'wpp' : 'ig';
  const body = document.getElementById(`cfg-${ch}-body`);
  if (!body.classList.contains('open')) togglePanel(`cfg-${ch}`);
}

function setDot(ch, status) {
  const id = ch === 'whatsapp' ? 'wpp-dot' : 'ig-dot';
  const el = document.getElementById(id);
  el.className = `conn-dot ${status}`;
}

function updateHeader(ch, name, identifier) {
  const pre = ch === 'whatsapp' ? 'wpp' : 'ig';
  setText(`${pre}-name`, name || ch);
  setText(`${pre}-sub`, identifier || 'online');
  const avatar = document.getElementById(`${pre}-avatar`);
  avatar.textContent = name ? name[0].toUpperCase() : '👤';
}

function setSendEnabled(ch, enabled) {
  const pre = ch === 'whatsapp' ? 'wpp' : 'ig';
  document.getElementById(`${pre}-attach-btn`).disabled = !enabled;
  document.getElementById(`${pre}-mic`).disabled = !enabled;
  // send/mic visibility controlled by onFieldInput
  _updateSendMic(pre, enabled);
}

function _updateSendMic(pre, channelEnabled) {
  const field = document.getElementById(`${pre}-field`);
  const hasPendingMedia = _pendingMedia[pre === 'wpp' ? 'whatsapp' : 'instagram'];
  const hasText = field && field.value.trim().length > 0;
  const showSend = channelEnabled !== false && (hasText || hasPendingMedia);
  document.getElementById(`${pre}-send`).style.display = showSend ? 'flex' : 'none';
  document.getElementById(`${pre}-mic`).style.display  = showSend ? 'none' : 'flex';
  document.getElementById(`${pre}-send`).disabled = !showSend;
}

function onFieldInput(event, ch) {
  autoResize(event.target);
  const pre = ch === 'whatsapp' ? 'wpp' : 'ig';
  _updateSendMic(pre);
}

// ── Attachment / media upload ──────────────────────────────────────────────
// Estado por canal: { mediaType, uploadUrl, filename } ou null
const _pendingMedia = { whatsapp: null, instagram: null };
const _mediaIcons = { image: '🖼', audio: '🎵', video: '🎬', document: '📄' };

function toggleAttachMenu(ch) {
  const pre = ch === 'whatsapp' ? 'wpp' : 'ig';
  document.getElementById(`${pre}-attach-menu`).classList.toggle('open');
}

function pickFile(ch, mediaType) {
  const pre = ch === 'whatsapp' ? 'wpp' : 'ig';
  _pendingMedia[ch] = { mediaType, uploadUrl: null, filename: null };
  const input = document.getElementById(`${pre}-file-input`);
  input.accept = mediaType === 'image'  ? 'image/*'
               : mediaType === 'audio'  ? 'audio/*'
               : '.pdf,.doc,.docx,.xls,.xlsx';
  document.getElementById(`${pre}-attach-menu`).classList.remove('open');
  input.click();
}

async function onFileSelected(event, ch) {
  const file = event.target.files[0];
  if (!file) return;
  event.target.value = '';

  const pre = ch === 'whatsapp' ? 'wpp' : 'ig';
  const mediaType = _pendingMedia[ch]?.mediaType || 'document';

  // sobe o arquivo imediatamente
  const form = new FormData();
  form.append('file', file);
  let uploadRes;
  try {
    const r = await fetch('/media/upload', { method: 'POST', body: form });
    if (!r.ok) throw new Error(`Upload falhou: ${r.status}`);
    uploadRes = await r.json();
  } catch (err) {
    showError(ch, err.message);
    _pendingMedia[ch] = null;
    return;
  }

  _pendingMedia[ch] = { mediaType, uploadUrl: uploadRes.url, filename: uploadRes.filename, mime: uploadRes.type };

  // mostra preview bar
  document.getElementById(`${pre}-preview-icon`).textContent = _mediaIcons[mediaType] || '📄';
  document.getElementById(`${pre}-preview-name`).textContent = uploadRes.filename;
  document.getElementById(`${pre}-preview-bar`).classList.add('visible');

  // foca no textarea para digitar a legenda
  document.getElementById(`${pre}-field`).placeholder =
    mediaType === 'audio' ? 'Mensagem (opcional)' : 'Legenda (opcional)';
  document.getElementById(`${pre}-field`).focus();

  // habilita o botão de envio mesmo sem texto
  document.getElementById(`${pre}-send`).disabled = false;
}

function cancelMedia(ch) {
  const pre = ch === 'whatsapp' ? 'wpp' : 'ig';
  _pendingMedia[ch] = null;
  document.getElementById(`${pre}-preview-bar`).classList.remove('visible');
  document.getElementById(`${pre}-field`).placeholder = ch === 'whatsapp' ? 'Mensagem' : 'Mensagem…';
  _updateSendMic(pre);
}

// ── Audio recording ────────────────────────────────────────────────────────
const _rec = {
  whatsapp: { recorder: null, chunks: [], timerInterval: null, seconds: 0 },
  instagram: { recorder: null, chunks: [], timerInterval: null, seconds: 0 },
};

function _pickMime() {
  const types = ['audio/webm;codecs=opus','audio/webm','audio/ogg;codecs=opus','audio/ogg','audio/mp4'];
  return types.find(t => MediaRecorder.isTypeSupported(t)) || '';
}

function _mimeExt(mime) {
  if (mime.includes('ogg')) return '.ogg';
  if (mime.includes('mp4')) return '.m4a';
  return '.webm';
}

async function toggleRecording(ch) {
  if (_rec[ch].recorder) { stopRecording(ch, false); return; }
  await startRecording(ch);
}

async function startRecording(ch) {
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    showError(ch, 'Permissão de microfone negada');
    return;
  }

  const mime = _pickMime();
  const recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : {});
  _rec[ch].recorder = recorder;
  _rec[ch].chunks = [];
  _rec[ch].seconds = 0;

  recorder.ondataavailable = e => { if (e.data.size) _rec[ch].chunks.push(e.data); };
  // Sem timeslice: ondataavailable dispara UMA vez em stop(), garantindo WebM
  // completo com o EBML header na primeira posição do blob.
  recorder.start();

  const pre = ch === 'whatsapp' ? 'wpp' : 'ig';
  document.getElementById(`${pre}-recording-bar`).classList.add('visible');
  document.getElementById(`${pre}-chat-input-area`)?.classList.add('hidden');
  document.getElementById(`${pre}-mic`).classList.add('recording');
  document.getElementById(`${pre}-attach-btn`).disabled = true;

  _rec[ch].timerInterval = setInterval(() => {
    _rec[ch].seconds++;
    const m = Math.floor(_rec[ch].seconds / 60);
    const s = String(_rec[ch].seconds % 60).padStart(2, '0');
    document.getElementById(`${pre}-rec-timer`).textContent = `${m}:${s}`;
  }, 1000);
}

async function stopRecording(ch, cancel) {
  const state = _rec[ch];
  if (!state.recorder) return;

  clearInterval(state.timerInterval);
  const pre = ch === 'whatsapp' ? 'wpp' : 'ig';
  document.getElementById(`${pre}-recording-bar`).classList.remove('visible');
  document.getElementById(`${pre}-rec-timer`).textContent = '0:00';
  document.getElementById(`${pre}-mic`).classList.remove('recording');
  document.getElementById(`${pre}-attach-btn`).disabled = false;

  const recorder = state.recorder;
  state.recorder = null;

  if (cancel || state.seconds < 1) {
    recorder.stop();
    recorder.stream?.getTracks().forEach(t => t.stop());
    return;
  }

  // Para o recorder ANTES de parar os tracks: se os tracks forem parados
  // primeiro, o Chrome finaliza o WebM sem fechar o Cluster corretamente,
  // resultando em EBML header inválido que o ffmpeg não consegue decodificar.
  await new Promise(resolve => {
    recorder.onstop = resolve;
    recorder.stop();
  });

  recorder.stream?.getTracks().forEach(t => t.stop());

  const mime = recorder.mimeType || 'audio/webm';
  const ext  = _mimeExt(mime);
  const blob = new Blob(state.chunks, { type: mime });
  const file = new File([blob], `audio${ext}`, { type: mime });

  // upload
  const form = new FormData();
  form.append('file', file);
  let uploadRes;
  try {
    const r = await fetch('/media/upload', { method: 'POST', body: form });
    if (!r.ok) throw new Error(`Upload falhou: ${r.status}`);
    uploadRes = await r.json();
  } catch (err) {
    showError(ch, err.message); return;
  }

  const wsState = channels[ch];
  if (!wsState.ws || wsState.ws.readyState !== WebSocket.OPEN) {
    showError(ch, 'WebSocket desconectado'); return;
  }
  wsState.ws.send(JSON.stringify({
    media_type: 'audio',
    url: uploadRes.url,
    filename: uploadRes.filename,
    mime: uploadRes.type || mime,
    caption: '',
  }));
}

function scrollBottom(el) { el.scrollTop = el.scrollHeight; }
function setText(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }
function setInput(id, val) { const el = document.getElementById(id); if (el) el.value = val; }
function escHtml(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

// Renderiza o texto com a marcação do WhatsApp: *negrito*, _itálico_, ~tachado~,
// ```monoespaçado``` e quebras de linha. Escapa o HTML antes de aplicar (anti-XSS):
// nenhum tag vem do texto, só os que adicionamos.
function formatWaText(raw) {
  let s = escHtml(String(raw));
  // monoespaçado em bloco (não recebe formatação aninhada)
  s = s.replace(/```([\s\S]+?)```/g, (_m, p1) => `<code class="wa-mono">${p1}</code>`);
  // negrito *...* — marcadores em borda de palavra
  s = s.replace(/(^|[^\w*])\*([^*\n]+?)\*(?=[^\w*]|$)/g, '$1<strong>$2</strong>');
  // itálico _..._
  s = s.replace(/(^|[^\w_])_([^_\n]+?)_(?=[^\w_]|$)/g, '$1<em>$2</em>');
  // tachado ~...~
  s = s.replace(/(^|[^\w~])~([^~\n]+?)~(?=[^\w~]|$)/g, '$1<del>$2</del>');
  // quebras de linha
  s = s.replace(/\n/g, '<br>');
  return s;
}

// ── Validation ─────────────────────────────────────────────────────────────
function validateUrl(id, val) {
  try { new URL(val); clearErr(id); return true; } catch { showErr(id); return false; }
}
function validateRequired(id, val) {
  if (val) { clearErr(id); return true; } showErr(id); return false;
}
function validateDigits(id, val) {
  if (/^\d+$/.test(val)) { clearErr(id); return true; } showErr(id); return false;
}
function showErr(id) {
  document.getElementById(id).classList.add('error');
  document.getElementById(`${id}-err`).classList.add('show');
}
function clearErr(id) {
  document.getElementById(id).classList.remove('error');
  document.getElementById(`${id}-err`).classList.remove('show');
}

// ── Debug log ──────────────────────────────────────────────────────────────
async function loadDebugFromServer() {
  // debug entries are pushed via WebSocket; this function can be extended
}

function addDebugEntry(ch, direction, payload, httpStatus) {
  const logId = ch === 'whatsapp' ? 'wpp-debug-log' : 'ig-debug-log';
  const emptyId = ch === 'whatsapp' ? 'wpp-debug-empty' : 'ig-debug-empty';
  const log = document.getElementById(logId);

  const empty = document.getElementById(emptyId);
  if (empty) empty.remove();

  // enforce MAX_DEBUG
  while (log.children.length >= MAX_DEBUG) log.lastChild.remove();

  const ts = new Date().toLocaleTimeString('pt-BR', {hour12: false}) + '.' + String(Date.now()%1000).padStart(3,'0');
  const dirLabel = { sent:'→ ENVIADO', recv:'← RECEBIDO', status:'⚡ STATUS', error:'✕ ERRO' }[direction] || direction;

  const entry = document.createElement('div');
  entry.className = `debug-entry ${direction}`;
  entry.innerHTML = `
    <div>
      <span class="debug-dir">${dirLabel}</span>
      <span class="debug-ts">${ts}</span>
      ${httpStatus ? `<span class="debug-http">${httpStatus}</span>` : ''}
    </div>
    <pre class="debug-json">${syntaxHighlight(typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2))}</pre>
    <div class="debug-entry-footer">
      <button class="copy-json-btn" onclick="copyJson(this, ${JSON.stringify(JSON.stringify(payload, null, 2)).replace(/</g,'\\u003c')})">Copiar JSON</button>
    </div>`;

  log.insertBefore(entry, log.firstChild);
}

function clearDebug(ch) {
  const logId = ch === 'whatsapp' ? 'wpp-debug-log' : 'ig-debug-log';
  const emptyId = ch === 'whatsapp' ? 'wpp-debug-empty' : 'ig-debug-empty';
  const log = document.getElementById(logId);
  const color = ch === 'instagram' ? 'style="color:#8e8e8e"' : '';
  log.innerHTML = `<div class="debug-empty" id="${emptyId}" ${color}>Nenhuma entrada ainda.</div>`;
}

function syntaxHighlight(json) {
  return json
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (m) => {
      let cls = 'json-num';
      if (/^"/.test(m)) cls = /:$/.test(m) ? 'json-key' : 'json-str';
      else if (/true|false/.test(m)) cls = 'json-bool';
      else if (/null/.test(m)) cls = 'json-null';
      return `<span class="${cls}">${m}</span>`;
    });
}

async function copyText(id, btn) {
  const text = document.getElementById(id).textContent;
  await navigator.clipboard.writeText(text).catch(() => {});
  btn.textContent = 'Copiado ✓'; btn.classList.add('copied');
  setTimeout(() => { btn.textContent = 'Copiar'; btn.classList.remove('copied'); }, 2000);
}

async function copyJson(btn, text) {
  await navigator.clipboard.writeText(text).catch(() => {});
  btn.textContent = 'Copiado ✓'; btn.classList.add('copied');
  setTimeout(() => { btn.textContent = 'Copiar JSON'; btn.classList.remove('copied'); }, 2000);
}

// ── Start ──────────────────────────────────────────────────────────────────
document.addEventListener('click', (e) => {
  if (!e.target.closest('.attach-wrap')) {
    document.querySelectorAll('.attach-menu').forEach(m => m.classList.remove('open'));
  }
});

boot();

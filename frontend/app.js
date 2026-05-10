/* ═══════════════════════════════════════════════════════════
   Fosk — Frontend SPA
   ═══════════════════════════════════════════════════════════ */

const API = '/api';

// ── State ────────────────────────────────────────────────────────────────────
const state = {
  folders: [],
  currentFolder: null,
  currentTrack: null,
  queue: [],
  queueIndex: -1,
  shuffle: false,
  repeat: false,       // false | 'one' | 'all'
  deviceId: getOrCreateDeviceId(),
  lyrics: null,
  lyricsTimer: null,
  settings: {
    enableBlur: localStorage.getItem('fosk_blur') !== 'false',
    enableCrossfade: localStorage.getItem('fosk_crossfade') === 'true'
  }
};

const audio = document.getElementById('audio-element');

// ── Init ─────────────────────────────────────────────────────────────────────
(async () => {
  await registerDevice();
  await loadFolders();
  renderView('home');
  bindPlayerControls();
  bindProgressBar();
  bindVolumeBar();
  bindSearch();
  bindSidebarNav();
  bindKeyboardShortcuts();
  audio.volume = 0.8;
  updateVolumeUI(0.8);
})();

// ── Device ID ────────────────────────────────────────────────────────────────
function getOrCreateDeviceId() {
  let id = localStorage.getItem('fosk_device_id');
  if (!id) {
    id = 'dev_' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
    localStorage.setItem('fosk_device_id', id);
  }
  return id;
}

async function registerDevice() {
  const name = navigator.userAgent.includes('Mobile') ? 'Mobile' :
    navigator.userAgent.includes('Tablet') ? 'Tablet' : 'Desktop';
  await api('POST', '/device', { id: state.deviceId, name });
}

// ── API helpers ───────────────────────────────────────────────────────────────
async function api(method, path, body = null) {
  const opts = { method, headers: {} };
  if (body) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  try {
    const res = await fetch(API + path, opts);
    if (!res.ok) throw new Error(res.statusText);
    return await res.json();
  } catch (e) {
    console.error('[API]', method, path, e.message);
    return null;
  }
}

// ── Folder loading ────────────────────────────────────────────────────────────
async function loadFolders() {
  const data = await api('GET', '/folders');
  state.folders = data?.folders || [];
  renderSidebarFolders();
}

function renderSidebarFolders() {
  const list = document.getElementById('folder-list');
  list.innerHTML = '';

  // Find roots (folders with no parent)
  const roots = state.folders.filter(f => !f.parent_id);

  // Instead of showing roots, show their children directly
  roots.forEach(root => {
    const children = state.folders.filter(c => c.parent_id == root.id);
    children.forEach(c => list.appendChild(buildFolderNode(c, 0)));
  });

  if (list.innerHTML === '' && roots.length === 0) {
    list.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:8px 18px">Nessuna cartella. Scansiona la tua musica dalla Home.</div>';
  }
}

function buildFolderNode(folder, depth) {
  const children = state.folders.filter(f => f.parent_id == folder.id);  // == handles int/string mismatch
  const hasChildren = children.length > 0;

  const wrap = document.createElement('div');
  wrap.className = 'folder-tree-node';

  const row = document.createElement('div');
  row.className = 'folder-item';
  row.dataset.id = folder.id;
  row.style.paddingLeft = `${18 + depth * 14}px`;

  const arrow = document.createElement('span');
  arrow.className = 'folder-arrow';
  arrow.textContent = hasChildren ? '▶' : '';
  arrow.style.marginRight = '4px';
  arrow.style.fontSize = '9px';
  arrow.style.opacity = '0.6';
  arrow.style.transition = 'transform 0.2s';
  arrow.style.display = 'inline-block';

  const icon = document.createElement('span');
  icon.className = 'folder-icon';
  icon.textContent = '📁';

  const label = document.createElement('span');
  label.textContent = ' ' + folder.name;

  row.appendChild(arrow);
  row.appendChild(icon);
  row.appendChild(label);
  wrap.appendChild(row);

  // Subfolder container (hidden by default)
  const sub = document.createElement('div');
  sub.className = 'folder-children';
  sub.style.display = 'none';
  children.forEach(c => sub.appendChild(buildFolderNode(c, depth + 1)));
  wrap.appendChild(sub);

  // Click: open folder (loads all tracks incl. subfolders)
  row.onclick = (e) => {
    e.stopPropagation();
    // Toggle children
    if (hasChildren) {
      const open = sub.style.display !== 'none';
      sub.style.display = open ? 'none' : 'block';
      arrow.style.transform = open ? '' : 'rotate(90deg)';
    }
    openFolder(folder.id);
  };

  return wrap;
}

async function openFolder(id) {
  // Highlight active folder
  document.querySelectorAll('.folder-item').forEach(el =>
    el.classList.toggle('active', +el.dataset.id === id)
  );
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

  // Use /all to include tracks from all subfolders
  const data = await api('GET', `/folder/${id}/all`);
  if (!data) return;

  state.currentFolder = data.folder;
  state.queue = data.tracks;

  const subCount = data.children?.length || 0;
  document.getElementById('main-title').textContent = data.folder.name;
  document.getElementById('main-subtitle').textContent =
    `${data.tracks.length} brani` + (subCount > 0 ? ` · ${subCount} sottocartelle` : '');

  renderTrackList(data.tracks);
}

// ── Views ─────────────────────────────────────────────────────────────────────
function renderView(name) {
  // Update nav highlight
  document.querySelectorAll('.nav-item[data-view]').forEach(el =>
    el.classList.toggle('active', el.dataset.view === name)
  );

  const content = document.getElementById('content');

  if (name === 'home') {
    document.getElementById('main-title').textContent = 'Home';
    document.getElementById('main-subtitle').textContent = 'La tua musica, ovunque';

    if (state.folders.length === 0) {
      content.innerHTML = `
      <div style="padding:60px; text-align:center">
        <div style="font-size:48px;margin-bottom:20px">🎵</div>
        <h2 style="font-family:Syne,sans-serif;margin-bottom:12px">Benvenuto su Fosk</h2>
        <p style="color:var(--text-muted);margin-bottom:24px">Non hai ancora aggiunto musica alla tua libreria.</p>
        <button class="btn btn-primary" onclick="renderView('settings')">Vai alle Impostazioni</button>
      </div>`;
    } else {
      renderDashboard();
    }
  } else if (name === 'library') {
    document.getElementById('main-title').textContent = 'Libreria';
    document.getElementById('main-subtitle').textContent = `${state.folders.length} cartelle`;
    renderLibraryView();
  } else if (name === 'discover') {
    document.getElementById('main-title').textContent = 'Discover';
    document.getElementById('main-subtitle').textContent = 'Musica dimenticata e gemme nascoste';
    renderDiscoverView();
  } else if (name === 'favorites') {
    document.getElementById('main-title').textContent = 'I tuoi preferiti';
    document.getElementById('main-subtitle').textContent = 'I brani che ami di più';
    renderFavoritesView();
  } else if (name === 'settings') {
    document.getElementById('main-title').textContent = 'Impostazioni';
    document.getElementById('main-subtitle').textContent = 'Gestione libreria e preferenze';
    renderSettingsView();
  }
}

async function renderSettingsView() {
  const content = document.getElementById('content');
  content.innerHTML = '<div style="padding:40px;color:var(--text-muted)">Caricamento impostazioni…</div>';

  const [roots, stats] = await Promise.all([
    api('GET', '/folders').then(d => d?.folders.filter(f => !f.parent_id) || []),
    api('GET', '/stats')
  ]);

  content.innerHTML = `
  <div id="view-settings" style="padding:32px; max-width:900px; display:grid; grid-template-columns: 1fr 1fr; gap:24px">
    
    <div class="settings-col">
      <div class="section-title">Libreria</div>
      
      <!-- Scan Section -->
      <div class="settings-card">
        <h3>Aggiungi Musica</h3>
        <p>Inserisci il percorso di una cartella musicale.</p>
        <div class="scan-form" style="margin-top:12px">
          <input class="scan-input" id="settings-scan-input" placeholder="Es. C:\\Musica" />
          <button class="btn btn-primary" onclick="handleSettingsScan()">Scansiona</button>
        </div>
      </div>

      <!-- Roots Section -->
      <div class="settings-card" style="margin-top:16px">
        <h3>Sorgenti Attuali</h3>
        <div style="margin-top:12px">
          ${roots.length === 0 ? '<div class="text-muted">Nessuna cartella aggiunta.</div>' : roots.map(f => `
            <div style="padding:8px 0; border-bottom:1px solid var(--border); display:flex; justify-content:space-between">
              <span style="font-size:13px">${esc(f.path)}</span>
              <span style="color:var(--text-muted)">📁</span>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- Stats Section -->
      <div class="settings-card" style="margin-top:16px">
        <h3>Statistiche</h3>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:12px">
          <div class="stat-box">
            <div class="stat-val">${stats?.tracks || 0}</div>
            <div class="stat-lbl">Brani</div>
          </div>
          <div class="stat-box">
            <div class="stat-val">${stats?.folders || 0}</div>
            <div class="stat-lbl">Cartelle</div>
          </div>
          <div class="stat-box" style="grid-column: span 2">
            <div class="stat-val">${Math.floor((stats?.duration || 0) / 3600)}h ${Math.floor(((stats?.duration || 0) % 3600) / 60)}m</div>
            <div class="stat-lbl">Tempo di ascolto totale</div>
          </div>
        </div>
      </div>
    </div>

    <div class="settings-col">
      <div class="section-title">Preferenze</div>

      <!-- Appearance Section -->
      <div class="settings-card">
        <h3>Interfaccia</h3>
        <label style="display:flex; justify-content:space-between; align-items:center; margin-top:12px; cursor:pointer">
          <span style="font-size:14px">Sfondo dinamico (Sfocatura)</span>
          <input type="checkbox" ${state.settings.enableBlur ? 'checked' : ''} onchange="toggleSetting('enableBlur', this.checked)">
        </label>
        <label style="display:flex; justify-content:space-between; align-items:center; margin-top:12px; cursor:pointer">
          <span style="font-size:14px">Dissolvenza tra i brani (Crossfade)</span>
          <input type="checkbox" ${state.settings.enableCrossfade ? 'checked' : ''} onchange="toggleSetting('enableCrossfade', this.checked)">
        </label>
        <p style="font-size:11px; color:var(--text-muted); margin-top:8px">Disattiva lo sfondo per migliorare le prestazioni su dispositivi lenti.</p>
      </div>

      <!-- Device Section -->
      <div class="settings-card" style="margin-top:16px">
        <h3>Dispositivo</h3>
        <div style="margin-top:12px">
          <div style="font-size:13px; color:var(--text-secondary)">ID: <code style="background:var(--bg-active); padding:2px 4px; border-radius:4px">${state.deviceId}</code></div>
          <div style="font-size:11px; color:var(--text-muted); margin-top:4px">Registrato come: ${navigator.userAgent.includes('Mobile') ? 'Mobile' : 'Desktop'}</div>
        </div>
      </div>

      <!-- Reset Section -->
      <div class="settings-card" style="margin-top:16px; border-color:rgba(255,68,68,0.3)">
        <h3 style="color:#ff4444">Zona Pericolosa</h3>
        <p style="font-size:12px; margin-top:8px">Svuota la libreria e cancella tutti i dati salvati.</p>
        <button class="btn" style="background:#ff4444; color:white; margin-top:12px; width:100%" onclick="resetLibrary()">Resetta Tutto</button>
      </div>
    </div>

  </div>`;
}

function toggleSetting(key, val) {
  state.settings[key] = val;
  localStorage.setItem('fosk_' + key.replace('enable', '').toLowerCase(), val);
  if (key === 'enableBlur' && !val) {
    document.getElementById('bg-blur').classList.remove('active');
  } else if (key === 'enableBlur' && val && state.currentTrack) {
    updateBackgroundBlur(state.currentTrack.id);
  }
}

async function handleSettingsScan() {
  const input = document.getElementById('settings-scan-input');
  const path = input.value.trim();
  if (!path) return;

  const overlay = document.getElementById('scan-overlay');
  overlay.classList.add('visible');

  const data = await api('POST', '/scan', { path });
  overlay.classList.remove('visible');

  if (data) {
    toast(`✓ Trovati ${data.tracks} brani`);
    input.value = '';
    await loadFolders();
    renderSettingsView();
  } else {
    toast('✗ Errore scansione. Percorso valido?', 'error');
  }
}

async function resetLibrary() {
  if (!confirm("Sei sicuro? Perderai tutti i preferiti e la cronologia di ascolto.")) return;
  await api('POST', '/reset');
  location.reload();
}

async function renderDashboard() {
  const content = document.getElementById('content');
  content.innerHTML = '<div style="padding:40px;color:var(--text-muted)">Caricamento dashboard…</div>';

  const data = await api('GET', `/discover?device_id=${state.deviceId}`);
  if (!data) return;

  const roots = state.folders.filter(f => !f.parent_id);
  const topFolders = state.folders.filter(f => roots.some(r => f.parent_id == r.id));

  content.innerHTML = `
  <div id="view-home" style="padding:24px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
      <div class="section-title" style="margin:0">Dashboard</div>
      <button class="btn btn-secondary" onclick="showScanModal()">+ Aggiungi musica</button>
    </div>

    ${renderDiscoverSection('🔥 Aggiunti di recente', data.recently_added)}
    ${renderDiscoverSection('✨ Gemme nascoste', data.hidden_gems)}
    
    <div class="section-title" style="margin-top:32px">Le tue cartelle</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:20px">
      ${topFolders.map(f => {
        const coverUrl = f.representative_track_id ? `${API}/cover/${f.representative_track_id}` : '';
        return `
        <div class="discover-card" onclick="openFolder(${f.id})">
          <div class="discover-card-cover">
            ${coverUrl ? `<img src="${coverUrl}" loading="lazy" />` : '📁'}
            <div class="card-play-overlay">📂</div>
          </div>
          <div class="discover-card-title" style="font-size:15px">${esc(f.name)}</div>
          <div class="discover-card-artist" style="color:var(--text-secondary)">${esc(f.path.split(/[\\/]/).pop())}</div>
        </div>
      `}).join('')}
    </div>
  </div>`;
}

function showScanModal() {
  const path = prompt("Inserisci il percorso della cartella musicale:");
  if (path) {
    const overlay = document.getElementById('scan-overlay');
    overlay.classList.add('visible');
    api('POST', '/scan', { path }).then(data => {
      overlay.classList.remove('visible');
      if (data) {
        toast(`✓ Scansione completata: ${data.tracks} brani`);
        loadFolders().then(() => renderView('home'));
      }
    });
  }
}

function bindScanForm() {
  document.getElementById('scan-btn')?.addEventListener('click', async () => {
    const path = document.getElementById('scan-path-input').value.trim();
    if (!path) return;
    const overlay = document.getElementById('scan-overlay');
    overlay.classList.add('visible');
    const data = await api('POST', '/scan', { path });
    overlay.classList.remove('visible');
    if (data) {
      toast(`✓ Scansione completata: ${data.tracks} brani in ${data.folders} cartelle`);
      document.getElementById('scan-status').textContent =
        `Trovati ${data.tracks} brani in ${data.folders} cartelle.`;
      await loadFolders();
      renderView('home');
    } else {
      toast('✗ Errore durante la scansione. Controlla il percorso.', 'error');
    }
  });
}

async function renderLibraryView() {
  const content = document.getElementById('content');
  content.innerHTML = '<div style="padding:40px;color:var(--text-muted)">Caricamento brani…</div>';
  
  const data = await api('GET', '/tracks/all');
  if (!data || !data.tracks.length) {
    content.innerHTML = '<div style="padding:32px;color:var(--text-muted);text-align:center">Nessun brano trovato. Vai in Impostazioni e scansiona la tua musica.</div>';
    return;
  }

  content.innerHTML = `
    <div style="padding:24px">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:24px">
        <div class="section-title" style="margin:0">Tutti i brani (${data.tracks.length})</div>
        <button class="btn btn-primary" onclick="shuffleAll()">🔀 Riproduzione casuale</button>
      </div>
      <div id="track-list-container"></div>
    </div>
  `;

  state.queue = data.tracks;
  renderTrackList(data.tracks);
}

function shuffleAll() {
  if (!state.queue.length) return;
  state.shuffle = true;
  updateControlsUI();
  
  // Pick a random track to start
  const idx = Math.floor(Math.random() * state.queue.length);
  playTrackFromQueue(idx);
}

async function renderDiscoverView() {
  const content = document.getElementById('content');
  content.innerHTML = `<div id="view-discover"><div class="section-title">Caricamento…</div></div>`;
  const data = await api('GET', `/discover?device_id=${state.deviceId}`);
  if (!data) { content.innerHTML = '<div style="padding:24px;color:var(--text-muted)">Impossibile caricare i suggerimenti.</div>'; return; }

  content.innerHTML = `<div id="view-discover">
    ${renderDiscoverSection('🕰 Brani dimenticati', data.forgotten)}
    ${renderDiscoverSection('💎 Hidden Gems', data.hidden_gems)}
    ${renderDiscoverSection('🎲 Scoperta casuale', data.random_pick)}
  </div>`;
}

async function renderFavoritesView() {
  const data = await api('GET', '/search?q='); // We'll need a proper favorites endpoint, but let's assume search returns them if we filter
  // Actually let's use search results for now or a new endpoint.
  // For simplicity, let's just fetch everything and filter (not ideal but works for now)
  const tracks = await api('GET', '/search?q=');
  const favs = tracks?.tracks.filter(t => t.is_favorite) || [];
  state.queue = favs;
  renderTrackList(favs);
}

function renderDiscoverSection(title, tracks) {
  if (!tracks?.length) return '';
  return `
  <div class="discovery-section">
    <div class="section-title">${title}</div>
    <div class="discovery-grid">
      ${tracks.map(t => `
        <div class="discover-card" onclick="playDiscoveryTrack(${t.id})">
          <div class="discover-card-cover">
            <img src="${API}/cover/${t.id}" alt="" onerror="this.parentElement.innerHTML='♫'" loading="lazy"/>
            <div class="card-play-overlay">▶</div>
          </div>
          <div class="discover-card-title">${esc(t.title || t.filename)}</div>
          <div class="discover-card-artist">${esc(t.artist || '—')}</div>
        </div>
      `).join('')}
    </div>
  </div>`;
}

// ── Track List ────────────────────────────────────────────────────────────────
async function renderTrackList(tracks) {
  const content = document.getElementById('content');
  if (!tracks.length) {
    content.innerHTML = '<div style="padding:32px;color:var(--text-muted);text-align:center">Nessun brano trovato.</div>';
    return;
  }

  // Header
  content.innerHTML = `
  <div id="view-folder">
    <div class="track-list-header">
      <span>#</span>
      <span></span>
      <span>Titolo</span>
      <span>Album</span>
      <span>Genere</span>
      <span>Durata</span>
      <span></span>
    </div>
    <div id="track-rows-container"></div>
  </div>`;

  const container = document.getElementById('track-rows-container');
  const chunkSize = 50;
  let index = 0;

  // Render in chunks to prevent UI freeze
  function renderChunk() {
    const end = Math.min(index + chunkSize, tracks.length);
    let html = '';
    for (let i = index; i < end; i++) {
      html += trackRowHTML(tracks[i], i);
    }
    container.insertAdjacentHTML('beforeend', html);
    index = end;

    if (index < tracks.length) {
      requestAnimationFrame(renderChunk);
    }
  }

  renderChunk();
}

function trackRowHTML(t, i) {
  const coverUrl = `${API}/cover/${t.id}`;
  const isFav = t.is_favorite ? 'active' : '';

  return `
  <div class="track-row" data-id="${t.id}" data-index="${i}" onclick="playTrackFromQueue(${i})">
    <div class="track-num">
      <span class="track-num-text">${i + 1}</span>
      <span class="play-icon-inline">▶</span>
    </div>
    <div class="track-cover">
      <img src="${coverUrl}" onerror="this.parentElement.innerHTML='♫'" loading="lazy"/>
    </div>
    <div class="track-info">
      <div class="track-title">${esc(t.title || t.filename)}</div>
      <div class="track-artist">${esc(t.artist || '—')}</div>
    </div>
    <div class="track-album">${esc(t.album || '—')}</div>
    <div class="track-genre">${esc(t.genre || '—')}</div>
    <div class="track-duration">${fmtTime(t.duration)}</div>
    <div class="track-actions">
      <button class="btn-like ${isFav}" onclick="event.stopPropagation();toggleLike(${t.id}, this)">♥</button>
      <button class="icon-btn" title="Download" onclick="event.stopPropagation();downloadTrack(${t.id})">↓</button>
    </div>
  </div>`;
}


function selectTrack(index) {
  // Single click just highlights
  document.querySelectorAll('.track-row').forEach((el, i) =>
    el.classList.toggle('playing', i === index)
  );
}

// ── Playback ──────────────────────────────────────────────────────────────────
async function playTrackFromQueue(index) {
  if (!state.queue[index]) return;
  state.queueIndex = index;
  await loadAndPlay(state.queue[index]);
}

async function playDiscoveryTrack(trackId) {
  const data = await api('GET', `/track/${trackId}`);
  if (!data) return;
  state.queue = [data];
  state.queueIndex = 0;
  await loadAndPlay(data);
}

async function loadAndPlay(track) {
  state.currentTrack = track;
  updateNowPlayingUI(track);
  updateBackgroundBlur(track.id);

  const src = `${API}/stream/${track.id}`;
  audio.src = src;
  audio.load();

  if (state.settings.enableCrossfade) {
    fadeIn(audio.volume || 0.8);
  }

  try {
    await audio.play();
    initVisualizer(); // Start visualizer on first play
    document.getElementById('btn-play').textContent = '⏸';
    document.getElementById('fs-btn-play').textContent = '⏸';
  } catch (e) {
    console.warn('Play blocked:', e);
  }

  // Log play
  api('POST', `/play/${track.id}`, { device_id: state.deviceId });

  // Load lyrics
  loadLyrics(track);

  // Highlight row
  document.querySelectorAll('.track-row').forEach((el, i) =>
    el.classList.toggle('playing', i === state.queueIndex)
  );
}

function updateBackgroundBlur(trackId) {
  if (!state.settings.enableBlur) return;
  const bg = document.getElementById('bg-blur');
  bg.style.backgroundImage = `url(${API}/cover/${trackId})`;
  bg.classList.add('active');
}

async function toggleLike(trackId, btnEl) {
  const isFav = !btnEl.classList.contains('active');
  btnEl.classList.toggle('active', isFav);

  // If it's the current track, update player heart too
  if (state.currentTrack && state.currentTrack.id === trackId) {
    state.currentTrack.is_favorite = isFav;
    document.getElementById('player-btn-like').classList.toggle('active', isFav);
  }

  await api('POST', `/track/${trackId}/like`, { is_favorite: isFav });
}

function updateNowPlayingUI(track) {
  const coverUrl = track.cover_url || `${API}/cover/${track.id}`;

  // Right panel
  document.getElementById('np-title').textContent = track.title || track.filename;
  document.getElementById('np-artist').textContent = track.artist || '—';

  const img = document.getElementById('np-cover-img');
  const ph = document.getElementById('np-cover-placeholder');

  img.src = coverUrl;
  img.style.display = 'block';
  ph.style.display = 'none';
  // If image fails to load (no cover), show placeholder
  img.onerror = () => { img.style.display = 'none'; ph.style.display = ''; };

  // Player bar
  document.getElementById('player-title').textContent = track.title || track.filename;
  document.getElementById('player-artist').textContent = track.artist || '—';

  // Fullscreen UI
  document.getElementById('fs-title').textContent = track.title || track.filename;
  document.getElementById('fs-artist').textContent = track.artist || '—';
  document.getElementById('fs-cover').src = coverUrl;
  document.getElementById('fs-bg').style.backgroundImage = `url(${coverUrl})`;

  const tImg = document.getElementById('player-thumb-img');
  const tIcon = document.getElementById('player-thumb-icon');

  tImg.src = coverUrl;
  tImg.style.display = 'block';
  tIcon.style.display = 'none';
  tImg.onerror = () => { tImg.style.display = 'none'; tIcon.style.display = ''; };

  document.getElementById('time-total').textContent = fmtTime(track.duration || 0);
  document.title = `${track.title || track.filename} — Fosk`;

  // Update heart in player
  const heart = document.getElementById('player-btn-like');
  heart.style.display = 'block';
  heart.classList.toggle('active', !!track.is_favorite);
  heart.onclick = () => toggleLike(track.id, heart);
}

// ── Lyrics ────────────────────────────────────────────────────────────────────
async function loadLyrics(track) {
  clearInterval(state.lyricsTimer);
  state.lyrics = null;

  document.getElementById('lyrics-content').innerHTML = '<div class="no-lyrics">Caricamento testi…</div>';

  const data = await api('GET', `/lyrics/${track.id}`);
  if (!data || (!data.synced && !data.plain)) {
    document.getElementById('lyrics-content').innerHTML =
      '<div class="no-lyrics">Testi non disponibili per questo brano.</div>';
    return;
  }

  state.lyrics = data;

  if (data.synced) {
    renderSyncedLyrics(data.synced);
    renderFullscreenLyrics(data.synced);
    startLyricsSync(data.synced);
  } else {
    document.getElementById('lyrics-content').innerHTML =
      `<div style="color:var(--text-secondary);font-size:13px;line-height:1.8;white-space:pre-wrap">${esc(data.plain)}</div>`;
  }
}

function renderSyncedLyrics(lines) {
  const html = lines.map((l, i) =>
    `<div class="lyric-line" data-index="${i}" data-time="${l.time}">${esc(l.text)}</div>`
  ).join('');
  document.getElementById('lyrics-content').innerHTML = html;
}

function renderFullscreenLyrics(lines) {
  const html = lines.map((l, i) =>
    `<div class="fs-lyric-line" data-index="${i}" data-time="${l.time}">${esc(l.text)}</div>`
  ).join('');
  document.getElementById('fs-lyrics-content').innerHTML = html;
}

function startLyricsSync(lines) {
  clearInterval(state.lyricsTimer);
  state.lyricsTimer = setInterval(() => {
    if (!lines.length) return;
    const t = audio.currentTime;

    // Find current line
    let active = 0;
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].time <= t) active = i;
      else break;
    }

    // Update standard lyrics
    const allLines = document.querySelectorAll('.lyric-line');
    allLines.forEach((el, i) => {
      el.classList.toggle('active', i === active);
      el.classList.toggle('near', Math.abs(i - active) === 1);
    });

    const activeEl = document.querySelector('.lyric-line.active');
    if (activeEl) activeEl.scrollIntoView({ behavior: 'smooth', block: 'center' });

    // Update fullscreen lyrics
    const fsLines = document.querySelectorAll('.fs-lyric-line');
    fsLines.forEach((el, i) => el.classList.toggle('active', i === active));
    const fsActive = document.querySelector('.fs-lyric-line.active');
    if (fsActive) fsActive.scrollIntoView({ behavior: 'smooth', block: 'center' });

  }, 200);
}

// ── Player controls ───────────────────────────────────────────────────────────
function bindPlayerControls() {
  document.getElementById('btn-play').onclick = togglePlay;
  document.getElementById('btn-prev').onclick = playPrev;
  document.getElementById('btn-next').onclick = playNext;
  document.getElementById('btn-shuffle').onclick = toggleShuffle;
  document.getElementById('btn-repeat').onclick = toggleRepeat;
  document.getElementById('btn-fs').onclick = toggleFullscreen;
  document.getElementById('btn-pip').onclick = togglePiP;

  audio.addEventListener('timeupdate', onTimeUpdate);
  audio.addEventListener('ended', onEnded);
  audio.addEventListener('play', () => { 
    document.getElementById('btn-play').textContent = '⏸'; 
    document.getElementById('fs-btn-play').textContent = '⏸';
  });
  audio.addEventListener('pause', () => { 
    document.getElementById('btn-play').textContent = '▶'; 
    document.getElementById('fs-btn-play').textContent = '▶';
  });
}

function bindKeyboardShortcuts() {
  window.addEventListener('keydown', e => {
    if (e.code === 'Space') {
      // Don't toggle play if typing in an input
      if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
      
      e.preventDefault(); // Prevent page scroll
      togglePlay();
    }
    // Optional: Left/Right for skipping
    if (e.code === 'ArrowLeft') {
      audio.currentTime = Math.max(0, audio.currentTime - 10);
    }
    if (e.code === 'ArrowRight') {
      audio.currentTime = Math.min(audio.duration, audio.currentTime + 10);
    }
  });
}

function togglePlay() {
  if (!state.currentTrack) return;
  audio.paused ? audio.play() : audio.pause();
}

function playPrev() {
  let idx = state.queueIndex - 1;
  if (idx < 0) idx = state.queue.length - 1;
  if (state.queue[idx]) playTrackFromQueue(idx);
}

let fadingOut = false;
function onTimeUpdate() {
  if (!audio.duration) return;
  const pct = audio.currentTime / audio.duration;
  updateProgressUI(pct);
  document.getElementById('time-current').textContent = fmtTime(audio.currentTime);

  // Crossfade check
  if (state.settings.enableCrossfade && audio.duration - audio.currentTime < 5 && !fadingOut && !audio.paused) {
    const nextIdx = getNextIndex();
    if (nextIdx !== -1) {
      fadingOut = true;
      fadeOutAndNext();
    }
  }
}

function fadeOutAndNext() {
  const startVol = audio.volume;
  const interval = setInterval(() => {
    if (audio.volume > 0.05) {
      audio.volume -= 0.05;
    } else {
      clearInterval(interval);
      audio.volume = 0;
      fadingOut = false;
      playNext();
      // Volume will be faded in by loadAndPlay
    }
  }, 200);
}

function fadeIn(targetVol) {
  audio.volume = 0;
  const interval = setInterval(() => {
    if (audio.volume < targetVol - 0.05) {
      audio.volume += 0.05;
    } else {
      audio.volume = targetVol;
      clearInterval(interval);
    }
  }, 200);
}

function getNextIndex() {
  if (state.shuffle) return Math.floor(Math.random() * state.queue.length);
  const next = state.queueIndex + 1;
  return next < state.queue.length ? next : (state.repeat === 'all' ? 0 : -1);
}

function playNext() {
  const idx = getNextIndex();
  if (idx !== -1 && state.queue[idx]) {
    playTrackFromQueue(idx);
  }
}

function onEnded() {
  if (fadingOut) return; // Already handled by crossfade
  if (state.repeat === 'one') {
    audio.currentTime = 0; audio.play();
  } else {
    playNext();
  }
}

function toggleShuffle() {
  state.shuffle = !state.shuffle;
  document.getElementById('btn-shuffle').classList.toggle('active', state.shuffle);
}

function toggleRepeat() {
  const modes = [false, 'one', 'all'];
  const idx = modes.indexOf(state.repeat);
  state.repeat = modes[(idx + 1) % modes.length];
  const btn = document.getElementById('btn-repeat');
  btn.classList.toggle('active', state.repeat !== false);
  btn.textContent = state.repeat === 'one' ? '↺¹' : '↺';
}

// ── Progress bar ──────────────────────────────────────────────────────────────
function bindProgressBar() {
  const bar = document.getElementById('progress-bar');
  let dragging = false;

  bar.addEventListener('mousedown', e => {
    dragging = true;
    seek(e);
  });
  document.addEventListener('mousemove', e => { if (dragging) seek(e); });
  document.addEventListener('mouseup', () => { dragging = false; });

  bar.addEventListener('touchstart', e => { dragging = true; seek(e.touches[0]); });
  document.addEventListener('touchmove', e => { if (dragging) seek(e.touches[0]); });
  document.addEventListener('touchend', () => { dragging = false; });

  function seek(e) {
    const rect = bar.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    if (audio.duration) {
      audio.currentTime = pct * audio.duration;
    }
    updateProgressUI(pct);
  }
}

function onTimeUpdate() {
  if (!audio.duration) return;
  const pct = audio.currentTime / audio.duration;
  updateProgressUI(pct);
  document.getElementById('time-current').textContent = fmtTime(audio.currentTime);
}

function updateProgressUI(pct) {
  const fill = document.getElementById('progress-fill');
  const handle = document.getElementById('progress-handle');
  fill.style.width = `${pct * 100}%`;
  handle.style.left = `${pct * 100}%`;
}

// ── Volume ────────────────────────────────────────────────────────────────────
function bindVolumeBar() {
  const bar = document.getElementById('volume-bar');

  bar.addEventListener('click', e => {
    const rect = bar.getBoundingClientRect();
    const vol = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    audio.volume = vol;
    updateVolumeUI(vol);
  });

  bar.addEventListener('wheel', e => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.05 : 0.05;
    const newVol = Math.max(0, Math.min(1, audio.volume + delta));
    audio.volume = newVol;
    updateVolumeUI(newVol);
  }, { passive: false });

  document.getElementById('vol-icon').onclick = () => {
    audio.muted = !audio.muted;
    document.getElementById('vol-icon').textContent = audio.muted ? '🔇' : '🔊';
  };
}

function updateVolumeUI(vol) {
  document.getElementById('volume-fill').style.width = `${vol * 100}%`;
}

// ── Search ────────────────────────────────────────────────────────────────────
function bindSearch() {
  let timer;
  document.getElementById('search-input').addEventListener('input', e => {
    clearTimeout(timer);
    const q = e.target.value.trim();
    if (!q) return;
    timer = setTimeout(() => doSearch(q), 400);
  });
}

async function doSearch(q) {
  const data = await api('GET', `/search?q=${encodeURIComponent(q)}`);
  if (!data) return;
  document.getElementById('main-title').textContent = `Risultati per "${q}"`;
  document.getElementById('main-subtitle').textContent = `${data.tracks.length} brani`;
  state.queue = data.tracks;
  renderTrackList(data.tracks);
}

// ── Sidebar nav ───────────────────────────────────────────────────────────────
function bindSidebarNav() {
  document.querySelectorAll('.nav-item[data-view]').forEach(el => {
    el.addEventListener('click', () => {
      document.querySelectorAll('.nav-item[data-view]').forEach(n => n.classList.remove('active'));
      el.classList.add('active');
      renderView(el.dataset.view);
    });
  });
}

// ── Download ──────────────────────────────────────────────────────────────────
function downloadTrack(id) {
  const a = document.createElement('a');
  a.href = `${API}/download/${id}`;
  a.download = '';
  a.click();
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function toast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = 'toast';
  el.style.borderLeft = `3px solid ${type === 'error' ? '#f87171' : 'var(--accent)'}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ── Utilities ─────────────────────────────────────────────────────────────────
function fmtTime(s) {
  if (!s || isNaN(s)) return '0:00';
  const m = Math.floor(s / 60);
  const ss = Math.floor(s % 60).toString().padStart(2, '0');
  return `${m}:${ss}`;
}

function esc(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function toggleFullscreen() {
  const el = document.getElementById('fullscreen-view');
  el.classList.add('visible');
  if (document.documentElement.requestFullscreen) {
    document.documentElement.requestFullscreen();
  }
}

function closeFullscreen() {
  const el = document.getElementById('fullscreen-view');
  el.classList.remove('visible');
  if (document.exitFullscreen) {
    document.exitFullscreen();
  }
}

async function togglePiP() {
  const img = document.getElementById('player-thumb-img');
  if (!img.src) return;

  const canvas = document.createElement('canvas');
  canvas.width = 512; canvas.height = 512;
  const ctx = canvas.getContext('2d');
  
  const tempImg = new Image();
  tempImg.crossOrigin = 'anonymous';
  tempImg.src = img.src;
  tempImg.onload = async () => {
    ctx.drawImage(tempImg, 0, 0, 512, 512);
    const video = document.createElement('video');
    video.muted = true;
    video.srcObject = canvas.captureStream();
    await video.play();
    await video.requestPictureInPicture();
  };
}

let audioCtx, analyser, visualizerInit = false;

function initVisualizer() {
  if (visualizerInit) return;
  const canvas = document.getElementById('visualizer');
  if (!canvas) return;
  visualizerInit = true;

  const ctx = canvas.getContext('2d');
  audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const source = audioCtx.createMediaElementSource(audio);
  analyser = audioCtx.createAnalyser();
  
  source.connect(analyser);
  analyser.connect(audioCtx.destination);
  
  analyser.fftSize = 64;
  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);
  
  const barWidth = (canvas.width / bufferLength) * 2.5;
  let barHeight;
  let x = 0;

  function draw() {
    requestAnimationFrame(draw);
    if (audio.paused) return;

    x = 0;
    analyser.getByteFrequencyData(dataArray);
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (let i = 0; i < bufferLength; i++) {
      barHeight = dataArray[i] / 4;
      ctx.fillStyle = `rgba(147, 51, 234, ${barHeight/40 + 0.3})`;
      ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
      x += barWidth + 2;
    }
  }
  draw();
}

// Make these accessible from inline HTML
window.openFolder = openFolder;
window.playTrackFromQueue = playTrackFromQueue;
window.playDiscoveryTrack = playDiscoveryTrack;
window.downloadTrack = downloadTrack;
window.selectTrack = selectTrack;
window.closeFullscreen = closeFullscreen;
window.toggleFullscreen = toggleFullscreen;
window.togglePiP = togglePiP;

const paths = {
  sprout: '<path d="M12 22V10M12 15C3 15 3 6 3 6c9 0 9 9 9 9Zm0-5C12 2 21 2 21 2c0 8-9 8-9 8Z"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.87M15 3.13a4 4 0 0 1 0 7.75"/><circle cx="9" cy="7" r="4"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Zm0 0v6h6M8 13h8m-8 4h5"/>',
  briefcase: '<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2M3 12a20 20 0 0 0 18 0m-9-1v4"/>',
  chart: '<path d="M3 3v18h18M8 16v-5m5 5V7m5 9v-7"/>',
  arrow: '<path d="M5 12h14m-6-6 6 6-6 6"/>',
  arrowUp: '<path d="m7 17 10-10M7 7h10v10"/>',
  chevron: '<path d="m9 5 7 7-7 7"/>',
  left: '<path d="m15 5-7 7 7 7"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  search: '<circle cx="10.5" cy="10.5" r="7.5"/><path d="m16 16 5 5"/>',
  upload: '<path d="M12 16V3m-5 5 5-5 5 5M3 16v4a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1v-4"/>',
  download: '<path d="M12 3v13m-5-5 5 5 5-5M3 16v4a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1v-4"/>',
  sparkle: '<path d="m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6ZM20 2v4m-2-2h4"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  checkCircle: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  shield: '<path d="M12 3 3 7v5c0 5 9 10 9 10s9-5 9-10V7Z"/><path d="m8 12 3 3 5-6"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4m7 14 5-5-5-5M9 12h12"/>',
  x: '<path d="m6 6 12 12M6 18 18 6"/>',
  eye: '<path d="M2 12S6 5 12 5s10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  layers: '<path d="m12 3 10 6-10 6L2 9Zm-10 12 10 6 10-6M2 15l10 6 10-6M2 12l10 6 10-6"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  edit: '<path d="m16 3 5 5M4 16l-1 5 5-1L21 7a2 2 0 0 0-5-5Z"/>',
  leaf: '<path d="M20 3C8 3 2 8 5 16c8 5 16-1 15-13ZM4 21 16 9"/>',
};
const icon = (name, cls = '') => `<svg class="icon ${cls}" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.file}</svg>`;
const e = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const num = v => Number(v || 0).toLocaleString('en-IN');
const pct = v => v == null ? '—' : `${(v * 100).toFixed(1)}%`;
const list = v => Array.isArray(v) ? v : (!v || ['none', 'n, o, n, e', 'nan'].includes(String(v).toLowerCase()) ? [] : String(v).split(',').map(x => x.trim()).filter(Boolean));
const initials = v => (String(v || 'C').replace(/^CND_/, '').slice(-2)).toUpperCase();
const brand = `<a href="#overview" class="brand" aria-label="Sprout home">${icon('sprout')}<span>sprout<span class="brand-dot">.</span></span></a>`;
const app = document.querySelector('#app');
let current = 'overview', summary, jobs = [], health, filters = {q: '', job_id: '', segment: '', review: '', page: 1}, selectedFile = null;
let viewGeneration = 0, modalGeneration = 0, toastTimer, searchTimer, pollTimer, lastFocus, controller;
const pageNames = {overview: 'Overview', candidates: 'Talent pool', screening: 'Resume studio', jobs: 'Open positions', reports: 'Reports'};

async function api(path, options = {}) {
  const response = await fetch('/api' + path, {...options, headers: {...(options.body instanceof FormData ? {} : {'Content-Type': 'application/json'}), ...options.headers}});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const d = data.detail;
    const message = typeof d === 'string' ? d : d?.fields?.join('\n') || d?.message || (Array.isArray(d) ? d.map(x => x.msg).join('; ') : 'Something went wrong. Please try again.');
    throw new Error(message);
  }
  return data;
}
function toast(message, error = false) {
  const target = document.querySelector('#toast');
  target.textContent = message;
  target.className = 'visible' + (error ? ' error' : '');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => target.className = '', 5000);
}
function badge(text) {
  const cls = {'Potential Match': 'green', 'Dataset Shortlist': 'green', 'Dataset Pool': 'neutral', 'Needs Data Review': 'orange', 'Lower Model Match': 'blue', Active: 'green', Closed: 'neutral', Draft: 'orange', Pending: 'orange', Reviewed: 'blue', Shortlisted: 'green', 'Not progressing': 'neutral', failed: 'red'}[text] || 'neutral';
  return `<span class="badge ${cls}">${e(text)}</span>`;
}
const loading = () => '<div class="loading"><div class="spinner"></div><p class="small muted">Loading your workspace…</p></div>';
const empty = (title, detail = '') => `<div class="empty">${icon('leaf')}<h3>${e(title)}</h3><p>${e(detail)}</p></div>`;
const jobOptions = (selected = '', all = true) => `${all ? '<option value="">All positions</option>' : '<option value="">Choose an active position</option>'}${jobs.filter(j => all || j.status === 'Active').map(j => `<option value="${e(j.id)}" ${selected === j.id ? 'selected' : ''}>${e(j.title)}</option>`).join('')}`;
const notice = (message, type = '') => `<div class="notice ${type}">${icon('info')}<span>${message}</span></div>`;

function login() {
  clearTimeout(pollTimer);
  app.innerHTML = `<main class="login"><section class="login-art">${brand}<div class="login-orbit"></div><div class="login-story"><div class="eyebrow">A LITTLE POTENTIAL. A BIG FUTURE.</div><h1>Great careers<br>start with<br><em>a fresh perspective.</em></h1><p>A thoughtful space to discover early talent. Turn resumes into a clearer picture of who comes next.</p></div><div class="login-note">${icon('sprout')} Built for beginnings. Designed for people.</div></section><section class="login-form-side"><form class="login-form" id="login-form"><div class="eyebrow">YOUR RECRUITMENT WORKSPACE</div><h2>Welcome to Sprout.</h2><p>Your next great hire starts here.</p><label for="email">Work email</label><input class="input" id="email" type="email" autocomplete="username" value="hr@sprout.local" required><label for="password">Password</label><input class="input" id="password" type="password" autocomplete="current-password" value="prototype" required minlength="1"><button class="btn primary" type="submit">Enter demo workspace ${icon('arrow')}</button><div class="demo-note"><strong>V1 prototype · Mocked login</strong><br>Use any email and password. No account is created and no credentials are sent. This local demo has no authentication protection.</div><div class="login-footer">Resume screening, with a human perspective.</div></form></section></main>`;
  document.querySelector('#login-form').onsubmit = event => {
    event.preventDefault();
    sessionStorage.setItem('sprout-demo', 'true');
    start();
  };
}
function shell() {
  app.innerHTML = `<div class="shell"><aside class="sidebar" id="sidebar">${brand}<div class="workspace-label">WORKSPACE</div><nav class="nav" aria-label="Main navigation">${[['overview','grid'],['candidates','users'],['screening','file'],['jobs','briefcase'],['reports','chart']].map(([page, glyph]) => `<a href="#${page}" class="nav-link ${current === page ? 'active' : ''}" data-page="${page}">${icon(glyph)}<span>${pageNames[page]}</span>${page === 'jobs' ? `<span class="nav-count">${jobs.filter(j => j.status === 'Active').length}</span>` : ''}</a>`).join('')}</nav><div class="sidebar-bottom"><div class="prototype-card">${icon('sparkle')}<h4>Potential, made visible.</h4><p>Upload a resume. Review the details. Let the model help you see the fit.</p><div class="eyebrow">FRESHER RECRUITMENT · V1</div></div><div class="sidebar-user"><span class="avatar">HR</span><div><strong>HR workspace</strong><p>Demo administrator</p></div><button id="logout" title="Leave demo workspace" aria-label="Leave demo workspace">${icon('logout')}</button></div></div></aside><div class="main"><header class="topbar"><div class="topbar-left"><button class="icon-btn mobile-menu" id="menu" aria-label="Open navigation">${icon('menu')}</button><div class="breadcrumb"><span>Workspace</span><span>/</span><strong id="breadcrumb">${pageNames[current]}</strong></div></div><div class="topbar-right"><span class="date">${new Intl.DateTimeFormat('en-IN', {day:'numeric', month:'short', year:'numeric', timeZone:'Asia/Kolkata'}).format(new Date())}</span><span class="environment">Prototype workspace</span><span class="topbar-divider"></span><span class="avatar">HR</span></div></header><main class="content" id="content">${loading()}</main></div></div>`;
  document.querySelector('#logout').onclick = () => { sessionStorage.removeItem('sprout-demo'); closeModal(); login(); };
  document.querySelector('#menu').onclick = () => document.querySelector('#sidebar').classList.toggle('open');
  document.querySelector('#sidebar').addEventListener('click', ev => { if (ev.target.closest('a')) document.querySelector('#sidebar').classList.remove('open'); });
}
async function start() {
  current = location.hash.slice(1) in pageNames ? location.hash.slice(1) : 'overview';
  app.innerHTML = loading();
  try {
    [health, summary, jobs] = await Promise.all([api('/health'), api('/summary'), api('/jobs')]);
    shell(); await navigate(current);
  } catch (err) {
    app.innerHTML = `<div class="boot"><span class="boot-mark">s.</span><h2>Let’s reconnect.</h2><p>${e(err.message)}</p><p>Start the local server using start.ps1, then try again.</p><button class="btn primary" id="retry">Try again</button></div>`;
    document.querySelector('#retry').onclick = start;
  }
}
function footer() { return `<footer class="footer"><span>Powered by AI. Guided by people. &nbsp;·&nbsp; Synthetic dataset</span><span>${icon('sprout')} Sprout V1</span></footer>`; }
function intro(title, subtitle, action = '', eyebrow = '') {
  return `<div class="page-intro between"><div>${eyebrow ? `<div class="eyebrow">${eyebrow}</div>` : ''}<h1>${title}</h1><p>${subtitle}</p></div>${action}</div>`;
}
async function navigate(page) {
  current = page;
  clearTimeout(pollTimer);
  const generation = ++viewGeneration;
  document.querySelectorAll('.nav-link').forEach(a => { a.classList.toggle('active', a.dataset.page === page); a.setAttribute('aria-current', a.dataset.page === page ? 'page' : 'false'); });
  document.querySelector('#breadcrumb').textContent = pageNames[page];
  const content = document.querySelector('#content');
  content.innerHTML = loading();
  try {
    [summary, jobs] = await Promise.all([api('/summary'), api('/jobs')]);
    if (generation !== viewGeneration) return;
    if (page === 'overview') await overview(generation);
    if (page === 'candidates') await pool(generation);
    if (page === 'screening') await studio(generation);
    if (page === 'jobs') positions();
    if (page === 'reports') reports();
  } catch (err) {
    if (generation !== viewGeneration) return;
    content.innerHTML = `<div class="error-panel card"><h3>We couldn’t load this view.</h3><p>${e(err.message)}</p><button class="btn primary" id="retry-view">Try again</button></div>`;
    document.querySelector('#retry-view').onclick = () => navigate(page);
  }
}
function goto(page) { if (location.hash === '#' + page) navigate(page); else location.hash = page; }
window.addEventListener('hashchange', () => { if (sessionStorage.getItem('sprout-demo') && document.querySelector('#content')) navigate(location.hash.slice(1) in pageNames ? location.hash.slice(1) : 'overview'); });

function stat(label, value, note, glyph) {
  return `<div class="card stat"><div class="stat-top"><span class="stat-label">${label}</span><span class="stat-icon">${icon(glyph)}</span></div><div class="stat-value">${value}</div><div class="stat-foot">${icon('arrowUp')}${note}</div></div>`;
}
function chart() {
  const maximum = Math.ceil(Math.max(1, ...summary.by_job.map(j => j.total)) / 1000) * 1000;
  const shortName = title => ({'AI/ML Engineer':'AI / ML','Software Engineer':'Software eng.','Data Analyst':'Data analyst','Python Developer':'Python dev.'}[title] || title.slice(0,12));
  return `<div class="chart"><div class="chart-axis">${[maximum, Math.round(maximum * .75), Math.round(maximum * .5), Math.round(maximum * .25), 0].map(n => `<span>${n >= 1000 ? n / 1000 + 'k' : n}</span>`).join('')}</div><div class="chart-plot">${summary.by_job.slice(0,6).map(j => `<div class="bar-group" title="${e(j.title)}: ${num(j.total)} applications"><div class="bar" style="height:${j.total / maximum * 100}%"></div><span class="bar-label">${e(shortName(j.title))}</span></div>`).join('')}</div></div>`;
}
async function overview(generation) {
  const top = await api('/candidates?limit=5&sort=dataset');
  if (generation !== viewGeneration) return;
  document.querySelector('#content').innerHTML = `<div>${intro('A fresh start. A better fit.', 'Here’s a clear view of your fresher recruitment pipeline.', `<button class="btn primary" id="upload-top">${icon('plus')} Screen a resume</button>`, 'YOUR RECRUITMENT, AT A GLANCE')}<section class="hero"><div class="hero-copy"><div class="eyebrow">${icon('sparkle')} DISCOVER WHAT’S NEXT</div><h2>Look beyond the resume.<br><em>Find the potential.</em></h2><p>From resume to reviewed shortlist, give every fresher a thoughtful first look.</p><button class="btn lime" id="hero-upload">Open resume studio ${icon('arrow')}</button></div><div class="hero-art" aria-hidden="true"><div class="orbit"></div><div class="plant-card">${icon('sprout')}</div><span class="floating-tag one">${icon('checkCircle')} Details, decoded</span><span class="floating-tag two">${icon('sparkle')} A clearer first look</span></div></section><section class="stats-grid" aria-label="Recruitment summary">${stat('Total applications', num(summary.applications), `${num(summary.candidates)} unique candidate records`, 'users')}${stat('Open positions', num(summary.active_jobs), `${num(summary.openings)} seats to fill`, 'briefcase')}${stat('Dataset shortlist', num(summary.dataset_shortlisted), 'Existing synthetic shortlist labels', 'checkCircle')}${stat('Resumes uploaded', num(summary.uploads), `${num(summary.reviewed)} HR decisions recorded`, 'file')}</section><div class="dashboard-middle"><section class="card distribution"><div class="section-head"><div><h2>Applications by position</h2><p>Where the next generation is applying</p></div><div class="legend"><span><i class="dot"></i>Applications</span></div></div>${chart()}</section><section class="card review-panel"><div class="section-head"><div><h2>Your resume workspace</h2><p>A little clarity at every step</p></div>${icon('layers')}</div><div class="review-steps">${[['file','Uploaded resumes', 'Ready for extraction and review',summary.uploads],['eye','Needs data review','Confirm details before the model runs', summary.segments.find(x=>x.name==='Needs Data Review').count],['checkCircle','Potential matches','New resumes above the model threshold',summary.segments.find(x=>x.name==='Potential Match').count]].map(([glyph,title,sub,n])=>`<div class="review-step"><span class="step-symbol">${icon(glyph)}</span><div><h4>${title}</h4><p>${sub}</p></div><span class="number">${num(n)}</span></div>`).join('')}</div><p class="mini-note">Model suggestions support your review. You make the decision.</p></section></div><section class="card"><div class="card-head between"><div><h2>Discover your talent pool</h2><p class="small muted" style="margin-top:5px;font-size:10px">Highest dataset scores · across all positions</p></div><button class="text-btn" id="view-pool">View all candidates ${icon('arrow')}</button></div>${candidateTable(top.items, true)}</section>${footer()}</div>`;
  document.querySelector('#upload-top').onclick = document.querySelector('#hero-upload').onclick = () => goto('screening');
  document.querySelector('#view-pool').onclick = () => goto('candidates');
  bindCandidateButtons();
}
function candidateTable(rows, compact = false) {
  if (!rows.length) return empty('No candidates here yet.', 'Try a different filter, or upload a resume to begin.');
  return `<div class="table-wrapper"><table><thead><tr><th>Candidate</th><th>Position</th>${!compact ? '<th>Skills</th>' : ''}<th>Score <span title="Dataset score is a synthetic weighted score. Model score appears only after prediction.">ⓘ</span></th><th>Segment</th>${!compact ? '<th>HR review</th>' : ''}<th><span class="sr-only">View candidate</span></th></tr></thead><tbody>${rows.map((r,i) => `<tr><td><div class="candidate-cell"><span class="avatar ${['','peach','blue','lilac'][i%4]}">${e(initials(r.name))}</span><div><strong>${e(r.name)}</strong><span class="sub">${e(r.degree || 'Degree pending')} · ${e(r.specialization || 'Details pending')}</span></div></div></td><td><strong>${e(r.job)}</strong><span class="sub">${e(r.source)}</span></td>${!compact ? `<td><div class="skills-cell">${r.skills.slice(0,2).map(s => `<span class="pill">${e(s)}</span>`).join('')}${r.skills.length > 2 ? `<span class="pill more">+${r.skills.length-2}</span>` : ''}</div></td>` : ''}<td><div class="score"><span>${r.probability != null ? pct(r.probability) : r.score != null ? Number(r.score).toFixed(1) : '—'}</span><span class="score-track"><i style="width:${Math.max(0, Math.min(100, r.probability != null ? r.probability * 100 : r.score || 0))}%"></i></span></div><span class="sub">${r.probability != null ? 'Model score' : r.score != null ? 'Dataset score' : 'Awaiting confirmation'}</span></td><td>${badge(r.segment)}</td>${!compact ? `<td>${badge(r.review)}</td>` : ''}<td><button class="icon-btn view-candidate" data-id="${e(r.id)}" aria-label="View ${e(r.name)}">${icon('arrowUp')}</button></td></tr>`).join('')}</tbody></table></div>`;
}
function bindCandidateButtons() {
  document.querySelectorAll('.view-candidate').forEach(button => button.onclick = () => openCandidate(button.dataset.id));
}
function queryParams() { return new URLSearchParams(Object.entries(filters).filter(([k,v]) => v !== '' && k !== 'page')).toString(); }
async function pool(generation) {
  document.querySelector('#content').innerHTML = `<div>${intro('Make room for potential.', 'Explore applications, review the evidence, and build your shortlist.', `<button class="btn primary" id="pool-upload">${icon('plus')} Screen a resume</button>`)}<div class="toolbar"><div class="search">${icon('search')}<input aria-label="Search candidates" id="candidate-search" placeholder="Search candidate ID, skills, or position…" value="${e(filters.q)}"></div><select class="filter" id="job-filter" aria-label="Filter by position">${jobOptions(filters.job_id)}</select><select class="filter" id="segment-filter" aria-label="Filter by segment"><option value="">All segments</option>${['Potential Match','Lower Model Match','Needs Data Review','Dataset Shortlist','Dataset Pool'].map(s => `<option ${filters.segment === s ? 'selected' : ''}>${s}</option>`).join('')}</select><button class="btn" id="export">${icon('download')} Export</button></div><div class="tabs" role="group" aria-label="Filter by HR review">${[['','All applications'],['Pending','To review'],['Shortlisted','HR shortlist'],['Reviewed','Reviewed']].map(([value,label]) => `<button class="tab ${filters.review === value ? 'active' : ''}" data-review="${value}">${label}</button>`).join('')}</div><section class="card"><div class="card-head between"><div class="pool-top"><h2>Candidate directory</h2><span class="count-label" id="candidate-count">…</span></div><span class="small muted" style="font-size:10px">Job-specific suggestions · human decisions</span></div><div id="candidate-results">${loading()}</div></section><div style="margin-top:17px">${notice('Dataset segments are existing synthetic labels. Open an application and select <strong>Run model</strong> to get a fresh prediction. Model scores are not hiring probabilities.')}</div>${footer()}</div>`;
  document.querySelector('#pool-upload').onclick = () => goto('screening');
  document.querySelector('#export').insertAdjacentHTML('beforebegin', `<button class="btn primary" id="segment-run" ${!health.model_ready ? 'disabled' : ''}>${icon('sparkle')} Run segmentation</button>`);
  document.querySelector('#segment-run').onclick = async () => {
    const button = document.querySelector('#segment-run');
    button.disabled = true;
    button.textContent = 'Running model…';
    try {
      const result = await api('/segments/run?job_id=' + encodeURIComponent(filters.job_id), {method:'POST'});
      toast(result.processed ? `${num(result.processed)} applications scored · ${num(result.potential_matches)} potential matches.` : result.message);
      if(generation === viewGeneration) await loadPool(generation);
    } catch(err) { toast(err.message, true); }
    finally { if(button.isConnected) {button.disabled = false; button.innerHTML = icon('sparkle') + ' Run segmentation';} }
  };
  document.querySelector('#candidate-search').oninput = ev => { filters.q = ev.target.value; filters.page = 1; clearTimeout(searchTimer); searchTimer = setTimeout(() => loadPool(generation), 220); };
  document.querySelector('#job-filter').onchange = ev => { filters.job_id = ev.target.value; filters.page = 1; loadPool(generation); };
  document.querySelector('#segment-filter').onchange = ev => { filters.segment = ev.target.value; filters.page = 1; loadPool(generation); };
  document.querySelectorAll('[data-review]').forEach(b => b.onclick = () => { filters.review = b.dataset.review; filters.page = 1; document.querySelectorAll('[data-review]').forEach(a => a.classList.toggle('active', a === b)); loadPool(generation); });
  document.querySelector('#export').onclick = () => window.location.assign('/api/export?' + queryParams());
  await loadPool(generation);
}
let poolRequest = 0;
async function loadPool(generation = viewGeneration) {
  const request = ++poolRequest;
  try {
    const data = await api(`/candidates?${queryParams()}&page=${filters.page}&limit=12`);
    if (generation !== viewGeneration || request !== poolRequest) return;
    document.querySelector('#candidate-count').textContent = num(data.total);
    const start = (data.page - 1)*12 + 1;
    document.querySelector('#candidate-results').innerHTML = `${candidateTable(data.items)}<div class="table-footer"><span>${data.total ? `${num(start)}–${num(Math.min(start + 11, data.total))} of ${num(data.total)} applications` : '0 applications'}</span><div class="pagination"><button class="icon-btn" id="prev" aria-label="Previous page" ${data.page === 1 ? 'disabled' : ''}>${icon('left')}</button><span>${data.page} / ${num(data.pages)}</span><button class="icon-btn" id="next" aria-label="Next page" ${data.page >= data.pages ? 'disabled' : ''}>${icon('chevron')}</button></div></div>`;
    document.querySelector('#prev').onclick = () => { filters.page--; loadPool(generation); };
    document.querySelector('#next').onclick = () => { filters.page++; loadPool(generation); };
    bindCandidateButtons();
  } catch (err) { toast(err.message, true); }
}

async function studio(generation) {
  const data = await api('/candidates?limit=100&segment=' + encodeURIComponent('Needs Data Review'));
  const recent = data.items.filter(r => r.source === 'Resume upload');
  if (generation !== viewGeneration) return;
  document.querySelector('#content').innerHTML = `<div>${intro('Every resume has a story.', 'Upload it. Uncover the details. Find the fit.', '', 'RESUME STUDIO')}<div class="upload-layout"><section class="card upload-box"><div class="section-head"><div><h2>Start with a resume</h2><p>A clearer first look, in just a few steps.</p></div><span class="badge green">OCR enabled</span></div><label class="form-label" for="upload-job">Screen for a position</label><select class="input" id="upload-job">${jobOptions(filters.job_id, false)}</select><label class="dropzone" id="dropzone"><input id="resume-file" type="file" accept="application/pdf,.pdf" aria-label="Choose a PDF resume"><span class="upload-symbol">${icon('upload')}</span><h3>Drop a resume here</h3><p>or <span class="browse">browse your files</span> to get started</p><span class="file-limit">PDF ONLY &nbsp; · &nbsp; UP TO 10 MB &nbsp; · &nbsp; 15 PAGES MAX</span></label><div id="selected-file"></div><div class="upload-action"><p>Scanned PDF? We’ll use OCR to read the text for you.</p><button class="btn primary" id="screen-button">Extract resume ${icon('arrow')}</button></div><div id="upload-progress"></div></section><aside class="card how-card"><div class="eyebrow muted" style="font-size:9px;margin-bottom:10px">FROM RESUME TO CLARITY</div><h2>A simple, thoughtful flow.</h2>${[['1','Extract the details','Text extraction and OCR turn your PDF into an editable candidate profile.'],['2','Give it a human check','Review the original, correct the fields, and confirm what’s accurate.'],['3','Discover the fit','The saved model compares the confirmed profile with your selected opening.']].map(([n,title,sub]) => `<div class="how-step"><span class="step-num">${n}</span><div><h4>${title}</h4><p>${sub}</p></div></div>`).join('')}<div style="margin-top:27px">${notice('Missing details stay unknown. We never assume a grade or a backlog count.')}</div></aside></div><section class="card" style="margin-top:24px"><div class="card-head between"><div><h2>Ready for a closer look</h2><p class="small muted" style="font-size:10px;margin-top:5px">Uploaded resumes waiting for data review</p></div><button class="text-btn" id="upload-history">View history ${icon('arrow')}</button></div>${candidateTable(recent.slice(0,6), true)}</section>${footer()}</div>`;
  selectedFile = null;
  const input = document.querySelector('#resume-file');
  input.onchange = () => selectFile(input.files[0]);
  const drop = document.querySelector('#dropzone');
  ['dragenter','dragover'].forEach(type => drop.addEventListener(type, ev => {ev.preventDefault(); drop.classList.add('dragover');}));
  ['dragleave','drop'].forEach(type => drop.addEventListener(type, ev => {ev.preventDefault(); drop.classList.remove('dragover');}));
  drop.addEventListener('drop', ev => { if(ev.dataTransfer.files.length) selectFile(ev.dataTransfer.files[0]); });
  document.querySelector('#screen-button').onclick = beginUpload;
  document.querySelector('#upload-history').onclick = () => { filters.segment = ''; filters.q = 'RES_'; filters.page = 1; goto('candidates'); };
  bindCandidateButtons();
}
function selectFile(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith('.pdf')) return toast('Please choose a PDF resume.', true);
  if (file.size > 10*1024*1024) return toast('Please choose a file smaller than 10 MB.', true);
  selectedFile = file;
  document.querySelector('#selected-file').innerHTML = `<div class="upload-filename">${icon('file')}<div><strong>${e(file.name)}</strong><small>${(file.size/1024).toFixed(0)} KB · Ready to extract</small></div><button class="icon-btn" id="remove-file" aria-label="Remove selected file">${icon('x')}</button></div>`;
  document.querySelector('#remove-file').onclick = () => { selectedFile = null; document.querySelector('#resume-file').value = ''; document.querySelector('#selected-file').innerHTML = ''; };
}
async function beginUpload() {
  const job = document.querySelector('#upload-job').value;
  if (!job) return toast('Choose a position first.', true);
  if (!selectedFile) return toast('Choose a PDF resume to get started.', true);
  const button = document.querySelector('#screen-button');
  button.disabled = true;
  const data = new FormData(); data.append('file', selectedFile);
  const generation = viewGeneration;
  try {
    document.querySelector('#upload-progress').innerHTML = `<div class="progress-card"><div class="spinner"></div><h3>Uploading your resume…</h3><p>We’ll show the extracted details for your review.</p></div>`;
    const result = await api('/screenings?job_id=' + encodeURIComponent(job), {method:'POST',body:data});
    if (generation === viewGeneration) pollScreening(result.id, generation);
    else toast('Resume uploaded. Find it in the talent pool when ready.');
  } catch (err) {
    if (generation === viewGeneration) { document.querySelector('#upload-progress').innerHTML = notice(e(err.message), 'error'); button.disabled = false; }
    toast(err.message, true);
  }
}
async function pollScreening(id, generation) {
  if (generation !== viewGeneration) return;
  try {
    const s = await api('/screenings/' + id);
    if (generation !== viewGeneration) return;
    if (s.status === 'ready' || s.status === 'completed') {
      document.querySelector('#screen-button').disabled = false;
      document.querySelector('#upload-progress').innerHTML = `<div style="margin-top:20px">${notice('Extraction is complete. Review the candidate details before running the model.')}</div>`;
      toast('Resume extracted. Let’s review the details.');
      openReview(s);
      return;
    }
    if (s.status === 'failed') {
      document.querySelector('#screen-button').disabled = false;
      document.querySelector('#upload-progress').innerHTML = `<div style="margin-top:20px">${notice(e(s.error), 'error')}</div>`;
      return;
    }
    const messages = {queued:'Getting your resume ready…',extracting_text:'Reading the PDF text…',ocr:`Reading scanned page ${s.page || 1} with OCR…`,parsing:'Organizing candidate details…'};
    document.querySelector('#upload-progress').innerHTML = `<div class="progress-card"><div class="spinner"></div><h3>${messages[s.status] || 'Processing…'}</h3><p>Your resume is being processed locally. Scanned pages may take a little longer.</p><div class="progress-stages"><span class="active">01 Upload</span><span class="${['extracting_text','ocr','parsing'].includes(s.status) ? 'active' : ''}">02 Extract / OCR</span><span class="${s.status === 'parsing' ? 'active' : ''}">03 Structure</span></div></div>`;
    pollTimer = setTimeout(() => pollScreening(id, generation), 1500);
  } catch (err) { toast(err.message, true); if(generation === viewGeneration) document.querySelector('#screen-button').disabled = false; }
}

function positions() {
  document.querySelector('#content').innerHTML = `<div>${intro('The right opportunity matters.', 'Create openings that give fresh talent somewhere to grow.', `<button class="btn primary" id="new-position">${icon('plus')} Create position</button>`)}<section class="job-grid">${jobs.map((j,i) => `<article class="card job-card"><div class="between"><span class="job-icon">${icon(['sparkle','chart','briefcase','file'][i%4])}</span>${badge(j.status)}</div><div><h3>${e(j.title)}</h3><span class="job-id">${e(j.id)} &nbsp;·&nbsp; Fresher opportunity</span></div><div class="job-meta"><span>${icon('users')}${j.openings} openings</span><span>${icon('target')}Min. CGPA ${j.minimum_cgpa}</span></div><div class="pills">${j.required_skills.map(s => `<span class="pill">${e(s)}</span>`).join('')}</div><div class="job-bottom"><p><strong>${num(j.applications)}</strong> applications</p><div class="row"><button class="btn tiny edit-job" data-id="${e(j.id)}">${icon('edit')} Edit</button><button class="text-btn job-candidates" data-id="${e(j.id)}">View pool ${icon('arrow')}</button></div></div></article>`).join('')}</section><div style="margin-top:22px">${notice('Changes to positions are saved locally. Editing job requirements resets predictions for uploaded resumes so they can be confirmed against the new requirements.')}</div>${footer()}</div>`;
  document.querySelector('#new-position').onclick = () => jobModal();
  document.querySelectorAll('.edit-job').forEach(b => b.onclick = () => jobModal(jobs.find(j => j.id === b.dataset.id)));
  document.querySelectorAll('.job-candidates').forEach(b => b.onclick = () => { filters = {q:'', job_id:b.dataset.id, segment:'',review:'',page:1}; goto('candidates'); });
}
function reports() {
  document.querySelector('#content').innerHTML = `<div>${intro('See the bigger picture.', 'A grounded view of your dataset and recruitment workspace.', `<a class="btn" href="/api/export">${icon('download')} Export all applications</a>`)}<section class="stats-grid">${stat('Dataset average score',summary.average_score.toFixed(1), 'Synthetic weighted score · out of 100', 'chart')}${stat('Unique candidates',num(summary.candidates),'Candidate records, not application count','users')}${stat('HR decisions',num(summary.reviewed),'Reviewed or given a decision','checkCircle')}${stat('Model runs this session',num(summary.model_predictions),'Dataset predictions · cleared on restart','sparkle')}</section><div class="report-grid"><section class="card card-body"><div class="section-head"><div><h2>Applications across positions</h2><p>Dataset records + uploaded resumes</p></div></div>${summary.by_job.map(j => `<div class="report-bar-row"><div class="between"><span>${e(j.title)}</span><strong>${num(j.total)}</strong></div><div class="report-bar"><i style="width:${j.total / Math.max(1,summary.applications)*100}%"></i></div></div>`).join('')}<p class="report-note">${num(summary.applications)} applications across ${jobs.length} positions. Multiple applications can belong to the same candidate.</p></section><section class="card card-body"><h2>Dataset shortlist rate</h2><p class="small muted" style="font-size:11px;margin-top:6px">Existing synthetic labels, not new model predictions</p><div class="donut" style="--angle:${summary.dataset_shortlisted / Math.max(1, summary.applications-summary.uploads)*360}deg"><div class="donut-hole"><strong>${(summary.dataset_shortlisted / Math.max(1,summary.applications-summary.uploads)*100).toFixed(2)}%</strong><small>DATASET SHORTLIST</small></div></div><div class="between small"><span class="muted">Shortlisted labels</span><strong>${num(summary.dataset_shortlisted)}</strong></div></section></div><section class="card card-body" style="margin-top:22px"><div class="section-head"><div><h2>Model & data notes</h2><p>Know what is behind each suggestion.</p></div>${badge(health.model_ready ? 'Active' : 'Model unavailable')}</div><div class="detail-grid"><div class="detail-item"><small>Saved model</small><strong>${e(health.model_name || 'Unavailable')}</strong></div><div class="detail-item"><small>Decision threshold</small><strong>${pct(health.threshold)}</strong></div><div class="detail-item"><small>Engineered input contract</small><strong>34 features</strong></div></div>${notice('This model learned synthetic shortlist labels. Its score is not a hiring-success probability. Review the evidence, missing information, and job fit before making a decision.')}<p class="report-note">Source: <strong>AI_Fresher_Recruitment_ML_Dataset.csv</strong>. CSV files stay unchanged. Uploaded files, edits, and HR decisions are stored in the ignored local <code>.runtime</code> folder. Login is mocked; use this V1 on your local machine only.</p></section>${footer()}</div>`;
}

function openModal(title, subtitle, body, footerHTML = '', size = '') {
  closeModal(false);
  lastFocus = document.activeElement;
  const root = document.querySelector('#modal-root');
  root.innerHTML = `<div class="modal-backdrop"><section class="modal ${size}" role="dialog" aria-modal="true" aria-labelledby="modal-title" tabindex="-1"><header class="modal-head"><div><h2 id="modal-title">${title}</h2><p>${subtitle}</p></div><button class="icon-btn" id="close-modal" aria-label="Close dialog">${icon('x')}</button></header><div class="modal-body">${body}</div>${footerHTML ? `<footer class="modal-footer">${footerHTML}</footer>` : ''}</section></div>`;
  document.body.style.overflow = 'hidden';
  document.querySelector('#close-modal').onclick = () => closeModal();
  root.querySelector('.modal-backdrop').onclick = ev => { if(ev.target === ev.currentTarget) closeModal(); };
  root.querySelector('.modal').focus();
  return ++modalGeneration;
}
function closeModal(restore = true) {
  modalGeneration++;
  document.querySelector('#modal-root').innerHTML = '';
  document.body.style.overflow = '';
  if (restore && lastFocus?.isConnected) lastFocus.focus();
}
document.addEventListener('keydown', ev => {
  const modal = document.querySelector('.modal');
  if (!modal) return;
  if (ev.key === 'Escape') closeModal();
  if (ev.key === 'Tab') {
    const nodes = [...modal.querySelectorAll('button:not(:disabled),a[href],input,select,textarea,[tabindex="0"]')].filter(n => n.offsetParent !== null);
    const first = nodes[0], last = nodes.at(-1);
    if(ev.shiftKey && (document.activeElement === first || document.activeElement === modal)) { ev.preventDefault(); last?.focus(); }
    else if(!ev.shiftKey && document.activeElement === last) { ev.preventDefault(); first?.focus(); }
  }
});
function jobModal(job = null) {
  const body = `<form id="job-form"><div class="form-errors" id="job-errors" role="alert"></div><div class="field-grid"><div class="field full"><label for="job-title">Position title</label><input id="job-title" class="input" required minlength="2" maxlength="100" value="${e(job?.title)}" placeholder="e.g. Junior Python Developer"></div><div class="field"><label for="job-openings">Number of openings</label><input id="job-openings" class="input" type="number" min="1" max="10000" required value="${job?.openings || 5}"></div><div class="field"><label for="job-cgpa">Minimum CGPA · 10-point scale</label><input id="job-cgpa" class="input" type="number" min="0" max="10" step=".01" required value="${job?.minimum_cgpa ?? 6.5}"></div><div class="field full"><label for="job-skills">Required skills · comma-separated</label><textarea class="input" id="job-skills" required placeholder="Python, SQL, Git">${e(job?.required_skills.join(', ') || '')}</textarea></div><div class="field full"><label for="job-degrees">Preferred degrees · comma-separated</label><input class="input" id="job-degrees" required value="${e(job?.preferred_degree.join(', ') || 'B.Tech, B.E, B.Sc, BCA')}"></div><div class="field"><label for="job-status">Status</label><select class="input" id="job-status">${['Active','Draft','Closed'].map(s => `<option ${job?.status === s ? 'selected' : ''}>${s}</option>`).join('')}</select></div></div></form>`;
  openModal(job ? 'Refine the opportunity.' : 'Create a fresh opportunity.', 'Define a clear starting point for the right talent.', body, '<button class="btn" id="cancel-job">Cancel</button><button class="btn primary" type="submit" form="job-form" id="save-job">Save position</button>');
  document.querySelector('#cancel-job').onclick = () => closeModal();
  document.querySelector('#job-form').onsubmit = async ev => {
    ev.preventDefault();
    const button = document.querySelector('#save-job'); button.disabled = true;
    const value = id => document.querySelector(id).value;
    try {
      await api(job ? '/jobs/'+job.id : '/jobs', {method:job ? 'PUT' : 'POST', body:JSON.stringify({title:value('#job-title'),openings:Number(value('#job-openings')),minimum_cgpa:Number(value('#job-cgpa')),required_skills:list(value('#job-skills')),preferred_degree:list(value('#job-degrees')),status:value('#job-status')})});
      closeModal(); toast('Position saved. A new beginning awaits.'); await navigate('jobs');
    } catch (err) { if(document.querySelector('#job-errors')) document.querySelector('#job-errors').textContent = err.message; button.disabled = false; }
  };
}

async function openCandidate(id) {
  const token = openModal('A closer look.', 'Loading application details…', loading(), '', 'medium');
  try {
    const s = await api('/candidates/' + id);
    if (token !== modalGeneration) return;
    if (s.source === 'Resume upload' && !s.confirmed && s.status === 'ready') return openReview(s);
    candidateModal(s);
  } catch (err) { toast(err.message, true); closeModal(); }
}
function candidateModal(s) {
  const d = s.data, name = d['Full Name'] || d['Candidate ID'] || s.candidate_id;
  const job = jobs.find(j => j.id === s.job_id);
  const upload = s.source === 'Resume upload';
  const result = s.probability != null ? `<div class="model-result"><div>${badge(s.segment)}<p>Threshold ${pct(health.threshold)} · ${e(health.model_name)}</p></div><span class="model-score">${(s.probability * 100).toFixed(1)}<small>%</small></span></div>` : '';
  const listBlock = (title, values) => `<div class="detail-list"><h4>${title}</h4><div class="pills">${list(values).length ? list(values).map(v => `<span class="pill">${e(v)}</span>`).join('') : '<span class="small muted">No confirmed entries</span>'}</div></div>`;
  const body = `<div class="detail-hero"><span class="avatar">${e(initials(name))}</span><div><h3>${e(name)}</h3><p>${e(job?.title || d['Job Role'])} &nbsp;·&nbsp; ${e(s.id)}</p></div></div>${!s.confirmed && upload ? notice(s.status === 'failed' ? e(s.error) : 'Extraction is still processing. Close this view and reopen it shortly.', s.status === 'failed' ? 'error' : '') : ''}<div class="between"><span class="small muted">${e(s.source)}</span>${badge(s.segment)}</div>${result}<div class="detail-grid"><div class="detail-item"><small>Degree</small><strong>${e(d.Degree || 'Unknown')}</strong></div><div class="detail-item"><small>CGPA</small><strong>${e(d.CGPA ?? 'Unknown')}<span class="small muted"> / 10</span></strong></div><div class="detail-item"><small>${upload ? 'Data confirmation' : 'Dataset score'}</small><strong>${upload ? (s.confirmed ? 'Confirmed' : 'Pending') : Number(d.Recruitment_Score).toFixed(1)}</strong></div></div>${listBlock('Skills', d.Skills)}${listBlock('Projects',d.Projects)}${listBlock('Internships',d.Internships)}${listBlock('Certifications',d.Certifications)}${listBlock('Achievements',d.Achievements)}<div style="margin-top:22px">${notice('Model results are suggestions. Review the original evidence and job requirements before recording your decision.')}</div><div class="review-decision"><label for="hr-review">HR decision</label><select class="input" id="hr-review">${['Pending','Reviewed','Shortlisted','Not progressing'].map(v => `<option ${v === s.review ? 'selected' : ''}>${v}</option>`).join('')}</select><button class="btn" id="save-review">Save decision</button></div>${upload ? `<details class="source-details"><summary>Extraction notes</summary><p style="margin-top:10px">${s.extraction_methods?.map(e).join(' · ') || ''}</p><p>${s.warnings?.map(e).join(' ') || ''}</p></details>` : ''}`;
  openModal('Potential, in perspective.', 'Review the evidence. Keep the decision human.', body, `${upload ? `<button class="btn" id="edit-data" ${!['ready','completed'].includes(s.status) ? 'disabled' : ''}>${icon('edit')} Review data</button>` : ''}<button class="btn primary" id="run-model" ${!s.confirmed || !health.model_ready ? 'disabled' : ''}>${icon('sparkle')} ${s.probability != null ? 'Run model again' : 'Run model'}</button>`, 'medium');
  document.querySelector('#save-review').onclick = async () => {
    const b = document.querySelector('#save-review'); b.disabled = true;
    try { await api('/candidates/'+s.id+'/review', {method:'PATCH',body:JSON.stringify({status:document.querySelector('#hr-review').value})}); toast('HR decision saved.'); if(current === 'candidates') loadPool(); }
    catch (err) {toast(err.message,true);} finally {b.disabled=false;}
  };
  if(upload) document.querySelector('#edit-data').onclick = () => openReview(s);
  document.querySelector('#run-model').onclick = async () => {
    const b = document.querySelector('#run-model'); b.disabled = true; b.textContent = 'Running the model…';
    try { await api('/candidates/'+s.id+'/predict', {method:'POST'}); const fresh = await api('/candidates/'+s.id); candidateModal(fresh); toast('Model prediction is ready.'); if(current === 'candidates') loadPool(); }
    catch(err) {toast(err.message,true); b.disabled=false; b.innerHTML=icon('sparkle')+' Try prediction again';}
  };
}

function openReview(s) {
  const d = s.data || {};
  const field = (key, label, type = 'text', attrs = '') => `<div class="field"><label for="field-${e(key.replaceAll(' ','-'))}">${label}</label><input class="input review-field" id="field-${e(key.replaceAll(' ','-'))}" data-key="${e(key)}" type="${type}" value="${e(d[key])}" ${attrs} placeholder="${type === 'number' ? 'Unknown — confirm value' : 'Review and enter'}"></div>`;
  const listField = (key, title) => `<div class="field full"><label for="list-${key}">${title} · one confirmed entry per line</label><textarea class="input review-list" id="list-${key}" data-key="${key}" placeholder="${key === 'Skills' ? 'Python\nSQL\nGit' : 'Review extracted entries, or confirm none'}">${e(list(d[key]).join('\n'))}</textarea>${key !== 'Skills' ? `<button type="button" class="confirm-none" data-none="${key}">Confirm no ${key.toLowerCase()}</button><span class="hint" id="none-${key}">${d[key] != null && !list(d[key]).length ? 'Confirmed: no entries.' : 'Blank stays unknown until you confirm no entries.'}</span>` : ''}</div>`;
  const body = `<div class="review-layout"><div><div class="pdf-preview"><iframe src="/api/screenings/${encodeURIComponent(s.id)}/resume#toolbar=0" title="Original uploaded resume"></iframe></div><div class="small muted" style="margin-top:10px;font-size:10px">${e(s.filename)} · <a target="_blank" rel="noopener" href="/api/screenings/${encodeURIComponent(s.id)}/resume">Open original PDF</a></div><details class="source-details"><summary>View extracted text & OCR notes</summary><p style="margin-top:10px;font-size:10px">${s.extraction_methods?.map(e).join(' · ') || ''}</p><pre>${e(s.text || '')}</pre></details></div><form class="review-form" id="review-form"><h3>${e(jobs.find(j=>j.id===s.job_id)?.title || 'Selected position')}</h3>${notice('Confirm all model inputs. Grades must use the indicated scales. Blank values remain unknown, and unknown data blocks prediction.','warning')}<div class="form-errors" id="review-errors" role="alert"></div><div class="field-grid">${field('Full Name','Full name · optional')}${field('Email','Email · optional','email')}${field('Degree','Degree · e.g. B.Tech','text','required')}${field('Specialization','Specialization','text','required')}${field('CGPA','CGPA · confirmed 10-point scale','number','min="0" max="10" step=".01" required')}${field('Backlogs','Backlogs · confirmed count','number','min="0" max="1000" step="1" required')}${field('Class 10 Percentage','Class 10 percentage','number','min="0" max="100" step=".01" required')}${field('Class 12 Percentage','Class 12 percentage','number','min="0" max="100" step=".01" required')}${listField('Skills','Skills')}${listField('Projects','Projects')}${listField('Internships','Internships')}${listField('Certifications','Certifications')}${listField('Achievements','Achievements')}</div><div class="notice" style="margin-top:20px"><span>Counts are calculated from confirmed entries. Treat each project, internship, certificate, or achievement as one entry; remove description lines incorrectly grouped by extraction.</span></div></form></div>`;
  openModal('A human check makes the difference.', 'Review extracted information against the original PDF.', body, `<button class="btn" id="save-confirm">${icon('check')} Confirm data</button><button class="btn primary" type="submit" form="review-form" id="confirm-predict">${icon('sparkle')} Confirm & run model</button>`, 'wide');
  const confirmedNone = new Set(['Projects','Internships','Certifications','Achievements'].filter(key => d[key] != null && !list(d[key]).length));
  document.querySelectorAll('[data-none]').forEach(b => b.onclick = () => {
    const key = b.dataset.none;
    confirmedNone.add(key); document.querySelector('#list-'+key).value = '';
    document.querySelector('#none-'+key).textContent = 'Confirmed: no entries.';
  });
  document.querySelectorAll('.review-list').forEach(t => t.oninput = () => { if(t.value.trim()) confirmedNone.delete(t.dataset.key); });
  const confirm = async predict => {
    const form = document.querySelector('#review-form');
    if(!form.reportValidity()) return;
    const data = {};
    document.querySelectorAll('.review-field').forEach(i => {data[i.dataset.key] = i.type === 'number' ? (i.value === '' ? null : Number(i.value)) : i.value.trim() || null;});
    document.querySelectorAll('.review-list').forEach(i => {
      const entries = [...new Set(i.value.split('\n').map(v=>v.trim()).filter(Boolean))];
      data[i.dataset.key] = entries.length ? entries : confirmedNone.has(i.dataset.key) ? [] : null;
    });
    document.querySelector('#confirm-predict').disabled = document.querySelector('#save-confirm').disabled = true;
    try {
      await api('/screenings/'+s.id+'/data', {method:'PUT',body:JSON.stringify({data})});
      if(predict) await api('/candidates/'+s.id+'/predict', {method:'POST'});
      const fresh = await api('/screenings/'+s.id);
      candidateModal(fresh);
      toast(predict ? 'Your model segment is ready.' : 'Candidate data confirmed.');
      if(current === 'candidates') loadPool();
    } catch(err) {
      const target = document.querySelector('#review-errors');
      if(target) {target.textContent = err.message; target.scrollIntoView({block:'center',behavior:'smooth'});}
      document.querySelector('#confirm-predict')?.removeAttribute('disabled'); document.querySelector('#save-confirm')?.removeAttribute('disabled');
    }
  };
  document.querySelector('#review-form').onsubmit = ev => {ev.preventDefault(); confirm(true);};
  document.querySelector('#save-confirm').onclick = () => confirm(false);
}

if(sessionStorage.getItem('sprout-demo')) start(); else login();

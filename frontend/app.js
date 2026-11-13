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
const pct = v => {
  if(v == null || !Number.isFinite(Number(v))) return '—';
  const percent=Number(v)*100;
  if(percent===0) return '0%';
  if(percent>0 && percent<.001) return `${percent.toExponential(2)}%`;
  if(percent<.1) return `${percent.toFixed(3)}%`;
  if(percent>99.9 && percent<100) return '>99.9%';
  return `${percent.toFixed(1)}%`;
};
const list = v => Array.isArray(v) ? v : (!v || ['none', 'n, o, n, e', 'nan'].includes(String(v).toLowerCase()) ? [] : String(v).split(',').map(x => x.trim()).filter(Boolean));
const initials = v => (String(v || 'C').replace(/^CND_/, '').slice(-2)).toUpperCase();
const brand = `<a href="#overview" class="brand" aria-label="Incepta home">${icon('sprout')}<span>incepta<span class="brand-dot">.</span></span></a>`;
const app = document.querySelector('#app');
let current = 'overview', summary, jobs = [], health, filters = {q: '', job_id: '', segment: '', review: '', route: '', sort: '', page: 1};
let viewGeneration = 0, modalGeneration = 0, toastTimer, searchTimer, pollTimer, lastFocus, controller;
let selectedFiles = [], uploadSending = false, selectedBatch = null, batchLimits, pendingUpload;
const pageNames = {overview: 'Overview', candidates: 'Talent pool', screening: 'Resume studio', jobs: 'Open positions', reports: 'Reports', shortlist: 'HR Shortlist', 'general-pool': 'General Candidate Pool', 'data-review': 'Need Data Review'};
const candidateRoutes = {candidates: '', shortlist: 'shortlist', 'general-pool': 'pool', 'data-review': 'review'};

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
const loading = () => '<div class="loading" role="status"><div class="spinner"></div><p class="small muted">Loading your workspace…</p></div>';
const empty = (title, detail = '') => `<div class="empty">${icon('leaf')}<h3>${e(title)}</h3><p>${e(detail)}</p></div>`;
const jobOptions = (selected = '', all = true) => `${all ? '<option value="">All positions</option>' : '<option value="">Choose an active position</option>'}${jobs.filter(j => all || j.status === 'Active').map(j => `<option value="${e(j.id)}" ${selected === j.id ? 'selected' : ''}>${e(j.title)}</option>`).join('')}`;
const notice = (message, type = '') => `<div class="notice ${type}">${icon('info')}<span>${message}</span></div>`;

function login() {
  clearTimeout(pollTimer);
  app.innerHTML = `<main class="login"><section class="login-art">${brand}<div class="login-orbit"></div><div class="login-story"><div class="eyebrow">Fresher recruitment</div><h1>Great careers start with <em>a fresh perspective.</em></h1><p>A thoughtful space to discover early talent. Turn resumes into a clearer picture of who comes next.</p></div><div class="login-note">${icon('sprout')} Built for beginnings. Designed for people.</div></section><section class="login-form-side"><form class="login-form" id="login-form"><div class="eyebrow">YOUR RECRUITMENT WORKSPACE</div><h2>Welcome to Incepta.</h2><p>Enter the local demo to explore your recruitment workspace.</p><label for="email">Work email</label><input class="input" id="email" type="email" autocomplete="username" value="hr@incepta.local" required><label for="password">Password</label><div class="password-field"><input class="input" id="password" type="password" autocomplete="current-password" value="prototype" required minlength="1"><button class="text-btn" id="password-toggle" type="button" aria-controls="password" aria-label="Show password">Show</button></div><button class="btn primary" type="submit">Enter demo workspace ${icon('arrow')}</button><div class="demo-note"><strong>V1 prototype · Mocked login</strong><br>Use any email and password. No account is created and no credentials are sent. This local demo has no authentication protection.</div><div class="login-footer">Resume screening, with a human perspective.</div></form></section></main>`;
  document.querySelector('#password-toggle').onclick = event => {
    const button = event.currentTarget;
    const password = document.querySelector('#password');
    const shown = password.type === 'password';
    password.type = shown ? 'text' : 'password';
    button.textContent = shown ? 'Hide' : 'Show';
    button.setAttribute('aria-label', shown ? 'Hide password' : 'Show password');
  };
  document.querySelector('#login-form').onsubmit = event => {
    event.preventDefault();
    sessionStorage.setItem('sprout-demo', 'true');
    start();
  };
}
function shell() {
  const groups = [
    ['Workspace', [['overview', 'grid']]],
    ['Recruitment', [['screening', 'file'], ['candidates', 'users'], ['shortlist', 'checkCircle'], ['data-review', 'eye'], ['jobs', 'briefcase']]],
    ['Insights', [['reports', 'chart']]]
  ];
  app.innerHTML = `<div class="shell">
    <a class="skip-link" href="#content">Skip to main content</a>
    <aside class="sidebar" id="sidebar" aria-label="Workspace navigation">
      <div class="between">${brand}<button class="icon-btn drawer-close" aria-label="Close navigation">${icon('x')}</button></div>
      <nav class="nav" aria-label="Main navigation">${groups.map(([label, links]) => `<div class="workspace-label">${label}</div>
        ${links.map(([page, glyph]) => `<a href="#${page}" class="nav-link" data-page="${page}">${icon(glyph)}<span>${pageNames[page]}</span></a>`).join('')}`).join('')}</nav>
      <div class="sidebar-bottom"><div class="sidebar-user"><span class="avatar" aria-hidden="true">HR</span><div><strong>HR workspace</strong><p>Local demo</p></div></div></div>
    </aside>
    <button class="drawer-scrim" tabindex="-1" aria-label="Dismiss navigation" hidden></button>
    <div class="main">
      <header class="topbar"><div class="topbar-inner">
        <div class="topbar-left"><button class="icon-btn mobile-menu" id="menu" aria-label="Open navigation" aria-controls="sidebar" aria-expanded="false">${icon('menu')}</button>
          <div class="breadcrumb"><span>Workspace</span><span aria-hidden="true">/</span><strong id="breadcrumb">${pageNames[current]}</strong></div></div>
        <div class="topbar-right"><span class="environment">Demo workspace</span>
          <details class="workspace-menu"><summary class="avatar" aria-label="HR workspace menu">HR</summary>
            <div class="workspace-popover"><strong>HR workspace</strong><p class="small">Local demo with mock login</p>
              <button class="btn" id="logout" type="button">${icon('logout')} Leave demo workspace</button></div>
          </details></div>
      </div></header>
      <main class="content" id="content" tabindex="-1">${loading()}</main>
    </div></div>`;
  const sidebar = document.querySelector('#sidebar');
  const scrim = document.querySelector('.drawer-scrim');
  const menu = document.querySelector('#menu');
  const main = document.querySelector('.main');
  const workspace = document.querySelector('.workspace-menu');
  const close = sidebar.querySelector('.drawer-close');
  const compact = matchMedia('(max-width: 880px)');
  function drawer(open) {
    open = open && compact.matches;
    const wasOpen = sidebar.classList.contains('open');
    sidebar.classList.toggle('open', open);
    sidebar.inert = compact.matches && !open;
    main.inert = open;
    scrim.hidden = !open;
    menu.setAttribute('aria-expanded', String(open));
    document.body.classList.toggle('drawer-open', open);
    if (open) close.focus();
    else if (wasOpen && compact.matches) menu.focus();
  }
  drawer(false);
  controller?.abort();
  controller = new AbortController();
  const {signal} = controller;
  compact.addEventListener('change', () => drawer(false), {signal});
  menu.onclick = () => drawer(true);
  close.onclick = scrim.onclick = () => drawer(false);
  sidebar.onclick = event => { if (event.target.closest('a')) drawer(false); };
  document.querySelector('.skip-link').onclick = event => {
    event.preventDefault();
    document.querySelector('#content').focus();
  };
  document.addEventListener('click', event => {
    if (workspace.open && !workspace.contains(event.target)) workspace.open = false;
  }, {signal});
  document.addEventListener('keydown', event => {
    if (document.querySelector('.modal')) return;
    if (event.key === 'Escape' && sidebar.classList.contains('open')) drawer(false);
    else if (event.key === 'Escape' && workspace.open) {
      workspace.open = false;
      workspace.querySelector('summary').focus();
    }
    if (event.key === 'Tab' && sidebar.classList.contains('open')) {
      const links = [...sidebar.querySelectorAll('a[href], button')];
      const destination = event.shiftKey && document.activeElement === links[0] ? links.at(-1) :
        !event.shiftKey && document.activeElement === links.at(-1) ? links[0] : null;
      if (destination) {
        event.preventDefault();
        destination.focus();
      }
    }
  }, {signal});
  document.querySelector('#logout').onclick = () => {
    controller.abort();
    sessionStorage.removeItem('sprout-demo');
    closeModal();
    login();
  };
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
function footer() { return `<footer class="footer"><span>Incepta · Local recruitment workspace</span><span>${icon('sprout')} Demo</span></footer>`; }
function intro(title, subtitle, action = '', eyebrow = '') {
  return `<div class="page-intro between"><div>${eyebrow ? `<div class="eyebrow">${eyebrow}</div>` : ''}<h1>${title}</h1><p>${subtitle}</p></div>${action}</div>`;
}
async function navigate(page) {
  current = page;
  clearTimeout(pollTimer);
  const generation = ++viewGeneration;
  document.querySelectorAll('.nav-link').forEach(link => {
    const active = link.dataset.page === page || (page === 'general-pool' && link.dataset.page === 'candidates');
    link.classList.toggle('active', active);
    if (active) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
  document.querySelector('#breadcrumb').textContent = pageNames[page];
  const content = document.querySelector('#content');
  content.innerHTML = loading();
  try {
    [summary, jobs] = await Promise.all([api('/summary'), api('/jobs')]);
    if (generation !== viewGeneration) return;
    if (page === 'overview') await overview(generation);
    if (page in candidateRoutes) {
      const route = candidateRoutes[page];
      if (route !== filters.route && !(page === 'candidates' && filters.route === 'not_assessed')) filters = {...filters, route, segment: '', sort: route === 'shortlist' ? 'rank' : '', page: 1};
      await pool(generation);
    }
    if (page === 'screening') await studio(generation);
    if (page === 'jobs') positions();
    if (page === 'reports') reports();
  } catch (err) {
    if (generation !== viewGeneration) return;
    content.innerHTML = `<div class="error-panel card"><h2>We couldn’t load this view.</h2><p role="alert">${e(err.message)}</p><button class="btn primary" id="retry-view">Try again</button></div>`;
    document.querySelector('#retry-view').onclick = () => navigate(page);
  }
}
function goto(page) { if (location.hash === '#' + page) navigate(page); else location.hash = page; }
window.addEventListener('hashchange', () => { if (sessionStorage.getItem('sprout-demo') && document.querySelector('#content')) navigate(location.hash.slice(1) in pageNames ? location.hash.slice(1) : 'overview'); });

function stat(label, value, note, glyph, href = '') {
  const element = href ? 'a' : 'div';
  return `<${element} class="card stat"${href ? ` href="${e(href)}"` : ''}>
    <div class="stat-top"><span class="stat-label">${label}</span><span class="stat-icon">${icon(glyph)}</span></div>
    <div class="stat-value">${value}</div><p class="stat-foot">${note}</p></${element}>`;
}

async function overview(generation) {
  const [top, history, shortlist, review] = await Promise.all([
    api('/candidates?limit=5&sort=dataset'), api('/batches'),
    api('/candidates?route=shortlist&limit=1'), api('/candidates?route=review&limit=1')
  ]);
  if (generation !== viewGeneration) return;
  const recent = history.items.slice(0, 4);
  document.querySelector('#content').innerHTML = `<div>
    ${intro('A fresh start. A better fit.', 'Track applications, shortlist activity, and profiles that need your attention.', `<a class="btn primary" href="#screening">${icon('plus')} Screen a resume</a>`, 'Recruitment overview')}
    <section class="hero"><div class="hero-copy">
      <h2>Look beyond the resume.<br><em>Find the potential.</em></h2>
      <p>Screen a batch for an open position, then review the evidence behind each recommendation.</p>
      <a class="btn lime" href="#screening">Open resume studio ${icon('arrow')}</a>
    </div><div class="hero-art" aria-hidden="true"><div class="hero-orbit"></div><div class="plant-card">${icon('sprout')}</div></div></section>
    <section class="stats-grid" aria-label="Recruitment summary">
      ${stat('Total applications', num(summary.applications), 'Dataset records and uploaded resumes', 'users', '#candidates')}
      ${stat('Open positions', num(summary.active_jobs), `${num(summary.openings)} active openings`, 'briefcase', '#jobs')}
      ${stat('HR Shortlist', num(shortlist.total), 'Shortlisted resume uploads', 'checkCircle', '#shortlist')}
      ${stat('Resumes uploaded', num(summary.uploads), 'Across all positions', 'file', '#screening')}
    </section>
    <div class="dashboard-middle">
      <section class="card card-body"><div class="section-head"><div><h2>Recent resume batches</h2><p>Open a batch to see its assessment results.</p></div></div>
        ${recent.length ? `<ul class="activity-list">${recent.map(batch => `<li><button class="activity-link recent-batch" data-id="${e(batch.id)}">
          <span class="step-symbol">${icon('file')}</span><span><strong>${e(jobs.find(job => job.id === batch.job_id)?.title || 'Position unavailable')}</strong>
          <time class="sub">${e(formatDate(batch.created_at))}</time></span>${icon('arrow')}</button></li>`).join('')}</ul>` :
          empty('No resume batches yet.', 'Upload resumes in Resume Studio to get started.')}
      </section>
      <section class="card card-body"><div class="section-head"><h2>Review queue</h2></div>
        <ul class="activity-list">
          <li><a class="activity-link" href="#data-review"><span class="step-symbol">${icon('eye')}</span><strong>Need Data Review</strong><span class="number">${num(review.total)}</span></a></li>
          <li><a class="activity-link" href="#shortlist"><span class="step-symbol">${icon('checkCircle')}</span><strong>HR Shortlist</strong><span class="number">${num(shortlist.total)}</span></a></li>
        </ul><p class="report-note">${num(summary.reviewed)} HR decisions recorded across the workspace.</p>
      </section>
    </div>
    <section class="card"><div class="card-head between"><div><h2>Dataset applications</h2><p class="small">Highest synthetic recruitment scores across positions</p></div>
      <a class="text-btn" href="#candidates">View candidate directory ${icon('arrow')}</a></div>${candidateTable(top.items, true)}</section>
    ${footer()}</div>`;
  document.querySelectorAll('.recent-batch').forEach(button => button.onclick = () => {
    sessionStorage.setItem('incepta-batch', button.dataset.id);
    goto('screening');
  });
  bindCandidateButtons();
}

function candidateScoreCell(r) {
  const weighted=r.recruitment_score ?? r.score;
  return `<div class="score"><span>${weighted!=null?Number(weighted).toFixed(2):'—'}</span>${weighted!=null?`<span class="score-track"><i style="width:${Math.max(0,Math.min(100,weighted))}%"></i></span>`:''}</div><span class="sub">${r.recruitment_score!=null?'Recruitment score / 100':r.score!=null?'Dataset score / 100':'Not assessed'}</span>${r.probability!=null?`<span class="sub classifier-table-score">ML shortlist score: ${pct(r.probability)}</span>`:''}`;
}
function candidateTable(rows, compact = false) {
  if (!rows.length) return empty('No candidates here yet.', 'Try a different filter, or upload a resume to begin.');
  return `<div class="table-wrapper" role="region" aria-label="Candidate applications" tabindex="0"><table><thead><tr><th>Candidate</th><th>Position</th>${!compact ? '<th>Skills</th>' : ''}<th>Score <span title="Dataset score is a synthetic weighted score. Model score appears only after prediction.">ⓘ</span></th><th>Segment</th>${!compact ? '<th>HR review</th>' : ''}<th><span class="sr-only">View candidate</span></th></tr></thead><tbody>${rows.map((r,i) => `<tr><td><div class="candidate-cell"><span class="avatar ${['','peach','blue','lilac'][i%4]}">${e(initials(r.name))}</span><div><strong>${e(r.name)}</strong>${r.run_id ? `<span class="sub">${e(formatDate(r.assessed_at))}</span>` : ''}<span class="sub">${e(r.degree || 'Degree pending')} · ${e(r.specialization || 'Details pending')}</span></div></div></td><td><strong>${e(r.job)}</strong><span class="sub">${e(r.source)}${r.rank ? ' · Job rank ' + r.rank : ''}</span></td>${!compact ? `<td><div class="skills-cell">${r.skills.slice(0,2).map(s => `<span class="pill">${e(s)}</span>`).join('')}${r.skills.length > 2 ? `<span class="pill more">+${r.skills.length-2}</span>` : ''}</div></td>` : ''}<td>${candidateScoreCell(r)}</td><td>${badge(r.segment)}</td>${!compact ? `<td>${badge(r.review)}</td>` : ''}<td><button class="icon-btn view-candidate" data-id="${e(r.id)}" aria-label="View ${e(r.name)}">${icon('arrowUp')}</button></td></tr>`).join('')}</tbody></table></div>`;
}
function bindCandidateButtons() {
  document.querySelectorAll('.view-candidate').forEach(button => button.onclick = () => openCandidate(button.dataset.id));
}
function queryParams() { return new URLSearchParams(Object.entries(filters).filter(([k,v]) => v !== '' && k !== 'page')).toString(); }
function resultsView(route, job = '') {
  filters = {route, job_id: job, q: '', segment: '', review: '', sort: route === 'shortlist' ? 'rank' : '', page: 1};
  goto(Object.keys(candidateRoutes).find(page => candidateRoutes[page] === route) || 'candidates');
}

async function pool(generation) {
  const [title, subtitle] = {
    shortlist: ['HR Shortlist', 'Review ranked candidates selected within each position’s shortlist capacity.'],
    pool: ['General Candidate Pool', 'Browse assessed candidates outside the shortlist and switch to unassessed applications.'],
    review: ['Need Data Review', 'Open an application to inspect flagged fields, check evidence, and submit corrections.']
  }[filters.route] || ['Talent Pool', 'Search applications, compare scores, and manage HR decisions.'];
  document.querySelector('#content').innerHTML = `<div>${intro(title, subtitle, `<button class="btn primary" id="pool-upload">${icon('plus')} Screen a resume</button>`)}<section class="card directory-tools" aria-label="Candidate filters"><div class="toolbar"><div class="search">${icon('search')}<input aria-label="Search candidates" id="candidate-search" placeholder="Name, application ID, skills, or position…" value="${e(filters.q)}"></div><select class="filter" id="job-filter" aria-label="Filter by position">${jobOptions(filters.job_id)}</select><select class="filter" id="segment-filter" aria-label="Filter by segment"><option value="">All segments</option>${['Potential Match','Lower Model Match','Needs Data Review','Dataset Shortlist','Dataset Pool'].map(s => `<option ${filters.segment === s ? 'selected' : ''}>${s}</option>`).join('')}</select><button class="btn" id="export">${icon('download')} Export</button></div><div class="tabs" role="group" aria-label="Candidate section">${[['','All applications'],['shortlist','HR Shortlist'],['pool','Non-shortlisted'],['review','Need Data Review'],['not_assessed','Not assessed']].map(([value,label]) => `<button class="tab ${filters.route === value ? 'active' : ''}" data-route="${value}" aria-pressed="${filters.route === value}">${label}</button>`).join('')}</div><div class="toolbar candidate-options"><label>Sort by <select class="input" id="candidate-sort">${[['','ML score'],['rank','Job rank'],['weighted','Recruitment score'],['dataset','Dataset score']].map(([value,label]) => `<option value="${value}" ${filters.sort === value ? 'selected' : ''}>${label}</option>`).join('')}</select></label><label>HR decision <select class="input" id="decision-filter"><option value="">All decisions</option>${['Pending','Pending HR Review','Under Review','Selected','Rejected','On Hold','Reviewed','Shortlisted','Not progressing'].map(v=>`<option ${v === filters.review ? 'selected' : ''}>${v}</option>`).join('')}</select></label></div></section><section class="card"><div class="card-head between"><div class="pool-top"><h2>Candidate directory</h2><span class="count-label" id="candidate-count" role="status">…</span></div><span class="small muted" style="font-size:10px">Job-specific scores and HR decisions</span></div><div id="candidate-results">${loading()}</div></section><div style="margin-top:17px">${notice('Dataset segments are existing synthetic labels. Open an application and select <strong>Run model</strong> to get a fresh prediction. Model scores are not hiring probabilities.')}</div>${footer()}</div>`;
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
  document.querySelectorAll('[data-route]').forEach(button => button.onclick = () => {
    filters.route = button.dataset.route;
    filters.segment = '';
    filters.sort = filters.route === 'shortlist' ? 'rank' : '';
    filters.page = 1;
    const page = Object.keys(candidateRoutes).find(key => candidateRoutes[key] === filters.route) || 'candidates';
    if (page === current) pool(generation).then(() => document.querySelector('.tab.active')?.focus());
    else goto(page);
  });
  document.querySelector('#candidate-sort').onchange = event => { filters.sort = event.target.value; filters.page = 1; loadPool(generation); };
  document.querySelector('#decision-filter').onchange = event => { filters.review = event.target.value; filters.page = 1; loadPool(generation); };
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
  } catch (err) {
    if (generation !== viewGeneration || request !== poolRequest) return;
    document.querySelector('#candidate-results').innerHTML = `<div class="error-panel">
      <h3>Candidate results are unavailable.</h3><p role="alert">${e(err.message)}</p><button class="btn" id="retry-candidates">Try again</button></div>`;
    document.querySelector('#retry-candidates').onclick = () => loadPool(generation);
  }
}

const formatDate = value => value ? new Date(value).toLocaleString('en-IN') : '';
const fileStatus = {
  queued: 'Queued', extracting_text: 'Reading PDF', ocr: 'Running OCR', parsing: 'Parsing resume',
  structuring: 'Gemini parsing', checking_fields: 'Validating fields', ready: 'Extracted',
  completed: 'Assessed', failed: 'Extraction failed', duplicate: 'Exact duplicate'
};

async function studio(generation) {
  const history = await api('/batches');
  if (generation !== viewGeneration) return;
  batchLimits = history;
  document.querySelector('#content').innerHTML = `<div>
    ${intro('Every resume has a story.', 'Upload resumes for one position, then assess the eligible profiles together.', '', 'RESUME STUDIO')}
    <div class="studio-grid"><section class="card upload-box batch-upload">
      <div class="section-head"><h2>Upload resumes</h2></div>
      <label class="form-label" for="upload-job">Screen for a position</label>
      <select class="input" id="upload-job">${jobOptions(filters.job_id, false)}</select>
      <label class="dropzone" id="dropzone"><input id="resume-file" type="file" accept="application/pdf,.pdf" multiple aria-label="Choose PDF resumes">
        <span class="upload-symbol">${icon('upload')}</span><strong>Drop resumes here or browse files</strong>
        <span class="file-limit">${history.max_files} PDFs per batch · ${history.max_mb} MB and ${history.max_pages} pages per PDF</span>
      </label>
      <div id="selected-file"></div>
      <div class="upload-action"><p>Scanned pages are read with OCR.${health.gemini_configured ? ' Gemini is enabled and receives extracted resume text for parsing.' : ''}</p>
        <button class="btn primary" id="screen-button">Extract resume ${icon('arrow')}</button></div>
    </section>
    <section class="card upload-box batch-results">
      <div class="section-head"><h2>Resume batches</h2></div>
      <label class="form-label" for="batch-history">Batch history</label><select class="input" id="batch-history"></select>
      <div id="batch-announcement" class="sr-only" role="status"></div>
      <div id="upload-progress"></div>
    </section></div>${footer()}</div>`;
  const input = document.querySelector('#resume-file');
  input.onchange = () => { selectFiles(input.files); input.value = ''; };
  const drop = document.querySelector('#dropzone');
  ['dragenter', 'dragover'].forEach(type => drop.addEventListener(type, event => {
    event.preventDefault(); drop.classList.add('dragover');
  }));
  ['dragleave', 'drop'].forEach(type => drop.addEventListener(type, event => {
    event.preventDefault(); drop.classList.remove('dragover');
  }));
  drop.addEventListener('drop', event => selectFiles(event.dataTransfer.files));
  document.querySelector('#screen-button').onclick = beginUpload;
  document.querySelector('#batch-history').onchange = event => chooseBatch(event.target.value, generation);
  const previous = sessionStorage.getItem('incepta-batch');
  const id = history.items.find(batch => batch.id === previous)?.id || history.items[0]?.id || '';
  renderBatchHistory(id);
  renderSelectedFiles();
  await chooseBatch(id, generation);
}

function renderBatchHistory(id) {
  document.querySelector('#batch-history').innerHTML = '<option value="">Choose a batch</option>' +
    batchLimits.items.map(batch => `<option value="${e(batch.id)}" ${id === batch.id ? 'selected' : ''}>
      ${e(jobs.find(job => job.id === batch.job_id)?.title || 'Position unavailable')} · ${e(formatDate(batch.created_at))}
    </option>`).join('');
}

function selectFiles(files) {
  if (uploadSending) return;
  for (const file of files) {
    if (!file.name.toLowerCase().endsWith('.pdf')) { toast(`${file.name}: choose a PDF.`, true); continue; }
    if (selectedFiles.length >= batchLimits.max_files) { toast(`Choose up to ${batchLimits.max_files} PDFs per batch.`, true); break; }
    selectedFiles.push(file);
  }
  pendingUpload = null;
  renderSelectedFiles();
}

function renderSelectedFiles() {
  const target = document.querySelector('#selected-file');
  if (!target) return;
  target.innerHTML = selectedFiles.map((file, index) => `<div class="upload-filename">${icon('file')}<div>
    <strong>${e(file.name)}</strong><small>${(file.size / 1024).toFixed(0)} KB</small></div>
    <button class="icon-btn remove-file" data-index="${index}" aria-label="Remove ${e(file.name)}" ${uploadSending ? 'disabled' : ''}>${icon('x')}</button></div>`).join('');
  target.querySelectorAll('.remove-file').forEach(button => button.onclick = () => {
    selectedFiles.splice(Number(button.dataset.index), 1); pendingUpload = null; renderSelectedFiles();
  });
  const button = document.querySelector('#screen-button');
  button.disabled = uploadSending;
  button.innerHTML = (uploadSending ? 'Uploading…' : selectedFiles.length > 1 ? `Extract ${selectedFiles.length} resumes` : 'Extract resume') + icon('arrow');
  document.querySelector('#upload-job').disabled = uploadSending;
  document.querySelector('#resume-file').disabled = uploadSending;
}

async function beginUpload() {
  const job = document.querySelector('#upload-job').value;
  if (!job) return toast('Choose a position first.', true);
  if (!selectedFiles.length) return toast('Choose at least one PDF resume.', true);
  if (uploadSending) return;
  const generation = viewGeneration;
  const form = new FormData();
  selectedFiles.forEach(file => form.append('files', file));
  if (pendingUpload?.job !== job) pendingUpload = {job, key: crypto.randomUUID()};
  uploadSending = true;
  renderSelectedFiles();
  try {
    const params = new URLSearchParams({job_id: job, upload_key: pendingUpload.key});
    const batch = await api('/batches?' + params, {method: 'POST', body: form});
    pendingUpload = null;
    selectedFiles = [];
    sessionStorage.setItem('incepta-batch', batch.id);
    if (current !== 'screening') return;
    batchLimits.items = [batch, ...batchLimits.items.filter(item => item.id !== batch.id)];
    renderBatchHistory(batch.id);
    await chooseBatch(batch.id, viewGeneration);
  } catch (error) {
    if (generation === viewGeneration) toast(error.message, true);
  } finally {
    uploadSending = false;
    if (current === 'screening') renderSelectedFiles();
  }
}

async function chooseBatch(id, generation) {
  clearTimeout(pollTimer);
  selectedBatch = null;
  if (!id) {
    sessionStorage.removeItem('incepta-batch');
    document.querySelector('#upload-progress').innerHTML = '<p class="muted">Choose a batch to view its progress.</p>';
    return;
  }
  sessionStorage.setItem('incepta-batch', id);
  document.querySelector('#upload-progress').innerHTML = loading();
  await refreshBatch(id, generation);
}

async function refreshBatch(id, generation = viewGeneration) {
  const active = () => generation === viewGeneration && document.querySelector('#batch-history')?.value === id;
  if (!active()) return;
  clearTimeout(pollTimer);
  try {
    const batch = await api('/batches/' + id);
    if (!active()) return;
    if (JSON.stringify(batch) !== JSON.stringify(selectedBatch)) {
      selectedBatch = batch;
      renderBatch(batch);
    }
    if (batch.extracting || batch.job_running) pollTimer = setTimeout(() => refreshBatch(id, generation), 750);
  } catch (error) {
    if (!active()) return;
    document.querySelector('#batch-announcement').textContent = error.message + ' Reconnecting.';
    selectedBatch = null;
    pollTimer = setTimeout(() => refreshBatch(id, generation), 2000);
  }
}

function metrics(items, extra = '') {
  return `<dl class="ats-metrics ${extra}">${items.map(([label, value, tone]) =>
    `<div class="${tone || ''}"><dt>${e(label)}</dt><dd>${e(value ?? '—')}</dd></div>`).join('')}</dl>`;
}

function allocationPanel(job, allocation) {
  const active = allocation.active;
  const config = active?.enforced ? active.job : job;
  const capacity = config.shortlist_capacity;
  const used = allocation.shortlisted;
  const eligible = allocation.qualified;
  const percentage = capacity > 0 ? Math.round(100 * used / capacity) : 0;
  const facts = [['Openings', config.openings], ['Shortlisting ratio', config.shortlisting_ratio],
    ['Shortlist capacity', capacity], ['Candidates assessed', allocation.assessed],
    ['Met model threshold', eligible], ['Shortlisted', used], ['Not shortlisted', allocation.non_shortlisted],
    ['Needs Data Review', allocation.review]];
  return `<div class="ats-allocation">
    <dl class="allocation-facts">${facts.map(([label, value]) => `<div><dt>${label}</dt><dd>${num(value)}</dd></div>`).join('')}</dl>
    ${active && !active.enforced ? '<p class="ats-note">This shortlist was assessed before capacity limits. Run an assessment to apply the configured capacity.</p>' : `
      <div class="capacity-usage">
        <label class="capacity-label"><span>Shortlist capacity used <strong>${num(used)} / ${num(capacity)}</strong></span>
          <meter min="0" max="${capacity}" value="${used}">${percentage}%</meter>
        </label>
        <span class="capacity-percent" aria-hidden="true">${percentage}%</span>
      </div>
      <p class="ats-note">${num(used)} ${used === 1 ? 'candidate was' : 'candidates were'} shortlisted from
        ${num(eligible)} eligible ${eligible === 1 ? 'candidate' : 'candidates'}. The configured shortlist capacity is ${num(capacity)}.</p>`}
    ${allocation.configuration_pending ? `<p class="allocation-pending">Saved configuration: ${num(job.openings)} ${job.openings === 1 ? 'opening' : 'openings'} ×
      ${num(job.shortlisting_ratio)}, capacity ${num(job.shortlist_capacity)}. Run an assessment to apply it.</p>` : ''}
    ${active?.enforced && allocation.capacity_excluded ? `<p class="ats-note">${allocation.capacity_excluded} threshold-qualified
      ${allocation.capacity_excluded === 1 ? 'candidate remains' : 'candidates remain'} in the general pool because the shortlist reached capacity.</p>` : ''}
  </div>`;
}

function assessmentDashboard(batch) {
  const {run, job, allocation, counts} = batch;
  const summary = run.summary;
  const status = {running:'Processing', completed:'Completed', partial:'Completed with errors', failed:'Failed', superseded:'Reassessment required'}[run.status] || 'Awaiting assessment';
  const timestamp = run.finished_at || run.started_at;
  const threshold = run.threshold ?? health.threshold;
  return `<section class="ats-dashboard" aria-labelledby="assessment-heading">
    <div class="ats-heading"><div><h3 id="assessment-heading">Assessment Results</h3>
      <p class="assessment-context"><span>${e(run.job?.title || job.title)}</span>
        ${timestamp ? `<time datetime="${e(timestamp)}">${e(formatDate(timestamp))}</time>` : ''}</p></div>
      <span class="ats-status ${run.status === 'completed' ? 'success' : run.status === 'failed' ? 'error' : 'warning'}">${status}</span>
    </div>
    ${metrics([['Total Assessed', summary?.assessed], ['Shortlisted', summary?.shortlisted, 'success'],
      ['Not Shortlisted', summary?.non_shortlisted]], 'assessment-metrics')}
    <dl class="assessment-secondary">
      <div><dt>Failed assessments</dt><dd>${e(summary?.failed ?? '—')}</dd></div>
      <div><dt>Needs Data Review</dt><dd>${num(counts.review)}</dd></div>
      <div><dt>ML threshold</dt><dd>${pct(threshold)}</dd></div>
    </dl>
    ${run.status === 'running' ? `<label class="ats-progress">Assessment progress · ${run.processed} of ${run.total} processed
      <progress ${run.total > 0 ? `value="${run.processed}" max="${run.total}"` : ''}></progress></label>` : ''}
    ${run.error ? notice(e(run.error), 'error') : ''}
    ${!run.status ? `<p class="ats-note">${batch.extracting ? 'Results will be available after extraction and assessment.' :
      counts.eligible ? 'Run the assessment to see results.' : 'No candidates are ready for assessment in this batch.'}</p>` : ''}
    ${summary?.assessed === 0 ? '<p class="ats-note">No candidates were assessed in this batch.</p>' : ''}
    <details class="ats-disclosure assessment-allocation"><summary>Job shortlist allocation</summary>${allocationPanel(job, allocation)}</details>
    <nav class="batch-actions ats-results" aria-label="Assessment results">
      <button class="btn primary" data-result="shortlist">HR Shortlist</button><button class="btn" data-result="pool">General Candidate Pool</button>
      <button class="btn" data-result="review">Need Data Review</button>
    </nav></section>`;
}

function renderBatch(batch) {
  const target = document.querySelector('#upload-progress');
  const counts = batch.counts;
  const pending = batch.extracting || batch.job_running;
  const status = batch.extracting ? 'Extracting resumes' : 'Extraction complete';
  const run = batch.run;
  const announcement = run.status === 'running' ? `Processing assessment. ${run.processed} of ${run.total} processed.` :
    run.summary ? `Assessment results. ${run.summary.assessed} assessed. ${run.summary.shortlisted} shortlisted. ${counts.review} need data review.` :
    `${run.status === 'failed' ? 'Assessment failed.' : status + '.'} ${counts.eligible} eligible. ${counts.review} need data review.`;
  const allocationOpen = target.querySelector('.assessment-allocation')?.open;
  const live = document.querySelector('#batch-announcement');
  if (live.textContent !== announcement) live.textContent = announcement;
  target.innerHTML = `<div class="batch-summary"><h3>${status}</h3>
    <dl class="batch-counts">${[['extracted','Successfully extracted'],['partial','Partially extracted'],['failed','Failed extraction'],
      ['eligible','Ready for assessment'],['review','Need Data Review'],['duplicates','Duplicate or possible duplicate']].map(([key,label]) =>
      `<div><dt>${label}</dt><dd>${counts[key]}</dd></div>`).join('')}</dl></div>
    <div class="processing-files">${batch.files.map(file => `<div class="queue-item processing-file">
      <div class="queue-file"><span class="step-symbol" aria-hidden="true">${icon('file')}</span><div><strong>${e(file.filename)}</strong><small>${e(fileStatus[file.status] || file.status)}
        ${file.page && batch.extracting ? ` · page ${file.page} of ${file.total_pages}` : ''}
        ${file.possible_duplicate && !file.duplicate ? ' · Possible same candidate' : ''}
        ${file.route === 'review' && file.status !== 'failed' ? ' · Need Data Review' : ''}</small>
        ${file.error || file.assessment_error ? `<p class="queue-error">${e(file.error || file.assessment_error)}</p>` : ''}</div></div>
      <div class="batch-actions">${file.application_id && ['ready','completed','failed','duplicate'].includes(file.status) ?
        `<button class="btn tiny queue-review" data-id="${e(file.application_id)}">${file.duplicate ? 'View original application' : 'View profile'}</button>` : ''}
      ${file.retryable ? `<button class="btn tiny queue-retry" data-id="${e(file.application_id)}" ${batch.run.status === 'running' ? 'disabled' : ''}>Retry extraction</button>` : ''}</div>
    </div>`).join('')}</div>
    <div class="batch-actions batch-run">
      <button class="btn primary" id="run-batch" ${pending || !batch.can_run || !health.model_ready ? 'disabled' : ''}>${icon('sparkle')} Run Model on All Resumes</button>
      <span>${counts.eligible} eligible · ${counts.review} pending review${counts.failed > counts.review ? ' · Failed uploads excluded' : ''}</span>
    </div>
    ${assessmentDashboard(batch)}
    <div class="batch-actions">
      <button class="btn" id="download-model-csv" ${counts.eligible ? '' : 'disabled'}>Download ML input CSV</button>
      <button class="btn" id="download-draft-csv" ${counts.extracted || counts.partial ? '' : 'disabled'}>Download extracted draft</button>
    </div>`;
  const extracted = batch.files.filter(file => !file.duplicate && ['ready', 'completed'].includes(file.status));
  target.querySelector('.assessment-allocation').open = Boolean(allocationOpen);
  target.querySelectorAll('[data-result]').forEach(button => button.onclick = () => resultsView(button.dataset.result, batch.job_id));
  target.querySelectorAll('.queue-review').forEach(button => button.onclick = () => openCandidate(button.dataset.id));
  target.querySelectorAll('.queue-retry').forEach(button => button.onclick = () =>
    batchAction(batch.id, '/files/' + button.dataset.id + '/retry', button));
  target.querySelector('#run-batch').onclick = event => batchAction(batch.id, '/run', event.currentTarget);
  target.querySelector('#download-model-csv').onclick = event =>
    downloadApplicationCSV(extracted.filter(file => file.route !== 'review').map(file => file.application_id), 'model', event.currentTarget);
  target.querySelector('#download-draft-csv').onclick = event =>
    downloadApplicationCSV(extracted.map(file => file.application_id), 'draft', event.currentTarget);
}

async function batchAction(id, path, button) {
  const generation = viewGeneration;
  button.disabled = true;
  try {
    await api('/batches/' + id + path, {method: 'POST'});
    await refreshBatch(id, generation);
  } catch (error) {
    toast(error.message, true);
    if (button.isConnected) button.disabled = false;
  }
}
async function downloadApplicationCSV(ids,mode,trigger=null) {
  const button=trigger || document.querySelector(mode==='model'?'#download-model-csv':'#download-draft-csv');
  if(button)button.disabled=true;
  try{
    const response=await fetch('/api/screenings/export-csv',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({screening_ids:ids,mode})});
    if(!response.ok){const error=await response.json();throw new Error(typeof error.detail==='string'?error.detail:error.detail?.fields?.join('; ')||'CSV export failed.');}
    const url=URL.createObjectURL(await response.blob());
    const link=document.createElement('a');link.href=url;link.download=mode==='model'?'Incepta_Applications.csv':'Incepta_Extraction_Draft.csv';document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
    toast(mode==='model'?'Model-ready application CSV downloaded.':'Draft downloaded. Review missing fields before using the ML pipeline.');
  }catch(err){toast(err.message,true);}finally{if(button?.isConnected)button.disabled=false;}
}
function configurationHistory(job) {
  if (!job.configuration_history.length) return '';
  const label = config => `${config.openings} openings × ${config.shortlisting_ratio} · capacity ${config.shortlist_capacity}`;
  return `<details class="ats-disclosure"><summary>Configuration history</summary><ul class="ats-history">
    ${job.configuration_history.slice().reverse().map(change => `<li>${e(label(change.previous))} → ${e(label(change.current))}
      <small>${e(formatDate(change.timestamp))}</small></li>`).join('')}
  </ul></details>`;
}

function positions() {
  document.querySelector('#content').innerHTML = `<div>${intro('The right opportunity matters.', 'Create openings that give fresh talent somewhere to grow.', `<button class="btn primary" id="new-position">${icon('plus')} Create position</button>`)}<section class="job-grid">${jobs.map((j,i) => `<article class="card job-card"><div class="between"><span class="job-icon">${icon(['sparkle','chart','briefcase','file'][i%4])}</span>${badge(j.status)}</div><div><h3>${e(j.title)}</h3></div><div class="job-meta"><span>${icon('users')}${j.openings} openings</span><span>${icon('target')}Min. CGPA ${j.minimum_cgpa}</span></div><div><p class="small">Preferred degrees · ${e(j.preferred_degree.join(', '))}</p></div><div class="pills">${j.required_skills.map(s => `<span class="pill">${e(s)}</span>`).join('')}</div><details class="ats-disclosure"><summary>Shortlist capacity · ${num(j.shortlist_capacity)}</summary>${allocationPanel(j, j.allocation)}${configurationHistory(j)}</details><div class="job-bottom"><p><strong>${num(j.applications)}</strong> applications</p><div class="row"><button class="btn tiny edit-job" data-id="${e(j.id)}">${icon('edit')} Edit</button><button class="text-btn job-candidates" data-id="${e(j.id)}">View pool ${icon('arrow')}</button></div></div></article>`).join('')}</section><div style="margin-top:22px">${notice('Changes to openings or the shortlisting ratio apply to the active shortlist after an assessment is run.')}</div>${footer()}</div>`;
  document.querySelector('#new-position').onclick = () => jobModal();
  document.querySelectorAll('.edit-job').forEach(b => b.onclick = () => jobModal(jobs.find(j => j.id === b.dataset.id)));
  document.querySelectorAll('.job-candidates').forEach(b => b.onclick = () => { filters = {q:'', job_id:b.dataset.id, segment:'',review:'',page:1}; goto('candidates'); });
}
function reports() {
  const datasetTotal = summary.applications - summary.uploads;
  const rate = datasetTotal ? (summary.dataset_shortlisted / datasetTotal * 100).toFixed(2) + '%' : '—';
  const maximum = Math.max(1, ...summary.by_job.map(job => job.total));
  document.querySelector('#content').innerHTML = `<div>
    ${intro('See the bigger picture.', 'Review application volume, HR decisions, and model context.', `<a class="btn primary" href="/api/export">${icon('download')} Export all applications</a>`, 'Reports')}
    <section class="stats-grid" aria-label="Report totals">
      ${stat('Dataset average score', summary.average_score.toFixed(1), 'Synthetic weighted score out of 100', 'chart')}
      ${stat('Candidate records', num(summary.candidates), 'Dataset and uploaded candidate records', 'users')}
      ${stat('HR decisions', num(summary.reviewed), 'Across all positions', 'checkCircle')}
      ${stat('Dataset predictions', num(summary.model_predictions), 'This server session', 'sparkle')}
    </section>
    <div class="report-grid">
      <section class="card card-body">
        <div class="section-head"><div><h2>Applications by position</h2><p>Dataset records and uploaded resumes</p></div></div>
        ${summary.by_job.length ? summary.by_job.map(job => `<div class="report-bar-row">
          <div class="between"><span>${e(job.title)}</span><strong>${num(job.total)}</strong></div>
          <div class="report-bar" aria-hidden="true"><i style="width:${job.total / maximum * 100}%"></i></div></div>`).join('') :
          empty('No position data yet.', 'Application totals appear here when data is available.')}
      </section>
      <section class="card card-body">
        <div class="section-head"><div><h2>Dataset shortlist rate</h2><p>Synthetic dataset labels</p></div></div>
        <p class="report-feature">${rate}</p><p>${num(summary.dataset_shortlisted)} shortlisted labels across ${num(datasetTotal)} dataset applications.</p>
      </section>
    </div>
    <section class="card card-body"><div class="section-head"><h2>Model and data</h2>${badge(health.model_ready ? 'Active' : 'Model unavailable')}</div>
      <div class="detail-grid"><div class="detail-item"><small>Saved model</small><strong>${e(health.model_name || 'Unavailable')}</strong></div>
        <div class="detail-item"><small>Decision threshold</small><strong>${pct(health.threshold)}</strong></div></div>
      ${notice('The classifier learned synthetic shortlist labels. Review the evidence and job requirements before recording an HR decision.')}
    </section>${footer()}</div>`;
}

function openModal(title, subtitle, body, footerHTML = '', size = '') {
  if (!document.querySelector('.modal')) lastFocus = document.activeElement;
  closeModal(false);
  const root = document.querySelector('#modal-root');
  root.innerHTML = `<div class="modal-backdrop"><section class="modal ${size}" role="dialog" aria-modal="true" aria-labelledby="modal-title" tabindex="-1"><header class="modal-head"><div><h2 id="modal-title">${title}</h2><p>${subtitle}</p></div><button class="icon-btn" id="close-modal" aria-label="Close dialog">${icon('x')}</button></header><div class="modal-body">${body}</div>${footerHTML ? `<footer class="modal-footer">${footerHTML}</footer>` : ''}</section></div>`;
  document.body.style.overflow = 'hidden';
  app.inert = true;
  document.querySelector('#close-modal').onclick = () => closeModal();
  root.querySelector('.modal-backdrop').onclick = ev => { if(ev.target === ev.currentTarget) closeModal(); };
  root.querySelector('.modal').focus();
  return ++modalGeneration;
}
function closeModal(restore = true) {
  modalGeneration++;
  document.querySelector('#modal-root').innerHTML = '';
  document.body.style.overflow = '';
  app.inert = false;
  if (restore && lastFocus?.isConnected) lastFocus.focus();
}
document.addEventListener('keydown', ev => {
  const modal = document.querySelector('.modal');
  if (!modal) return;
  if (ev.key === 'Escape') closeModal();
  if (ev.key === 'Tab') {
    const nodes = [...modal.querySelectorAll('button:not(:disabled),a[href],input:not(:disabled),select,textarea,summary,iframe,[tabindex="0"]')].filter(n => n.getClientRects().length && !n.disabled);
    const first = nodes[0], last = nodes.at(-1);
    if(ev.shiftKey && (document.activeElement === first || document.activeElement === modal)) { ev.preventDefault(); last?.focus(); }
    else if(!ev.shiftKey && document.activeElement === last) { ev.preventDefault(); first?.focus(); }
  }
});
function jobModal(job = null) {
  const body = `<form id="job-form"><div class="form-errors" id="job-errors" role="alert"></div><div class="field-grid"><div class="field full"><label for="job-title">Position title</label><input id="job-title" class="input" required minlength="2" maxlength="100" value="${e(job?.title)}" placeholder="e.g. Junior Python Developer"></div><div class="field"><label for="job-openings">Number of openings</label><input id="job-openings" class="input" type="number" min="1" max="10000" required value="${job?.openings || 5}"></div><div class="field"><label for="job-ratio">Shortlisting Ratio (candidates per opening)</label><input id="job-ratio" class="input" type="number" min="0.001" max="999999.999" step="0.001" required value="${job?.shortlisting_ratio ?? 3.5}"></div><div class="field full"><output id="job-capacity" for="job-openings job-ratio" aria-live="polite"></output></div><div class="field"><label for="job-cgpa">Minimum CGPA · 10-point scale</label><input id="job-cgpa" class="input" type="number" min="0" max="10" step=".01" required value="${job?.minimum_cgpa ?? 6.5}"></div><div class="field full"><label for="job-skills">Required skills · comma-separated</label><textarea class="input" id="job-skills" required placeholder="Python, SQL, Git">${e(job?.required_skills.join(', ') || '')}</textarea></div><div class="field full"><label for="job-degrees">Preferred degrees · comma-separated</label><input class="input" id="job-degrees" required value="${e(job?.preferred_degree.join(', ') || 'B.Tech, B.E, B.Sc, BCA')}"></div><div class="field"><label for="job-status">Status</label><select class="input" id="job-status">${['Active','Draft','Closed'].map(s => `<option ${job?.status === s ? 'selected' : ''}>${s}</option>`).join('')}</select></div></div></form>`;
  openModal(job ? 'Edit position' : 'Create position', 'Set the requirements and shortlist capacity for this position.', body, '<button class="btn" id="cancel-job">Cancel</button><button class="btn primary" type="submit" form="job-form" id="save-job">Save position</button>');
  document.querySelector('#cancel-job').onclick = () => closeModal();
  const openings = document.querySelector('#job-openings');
  const ratio = document.querySelector('#job-ratio');
  const preview = () => {
    const valid = openings.validity.valid && ratio.validity.valid;
    const slots = Math.ceil(Number(openings.value) * Math.round(Number(ratio.value) * 1000) / 1000);
    document.querySelector('#job-capacity').textContent = valid ?
      `Shortlist capacity: ${num(slots)}. With ${openings.value} ${openings.value === '1' ? 'opening' : 'openings'} and a ratio of ${ratio.value}, up to ${num(slots)} candidates can be shortlisted.` :
      'Enter positive openings and a positive ratio with up to three decimal places.';
  };
  openings.addEventListener('input', preview);
  ratio.addEventListener('input', preview);
  preview();
  document.querySelector('#job-form').onsubmit = async ev => {
    ev.preventDefault();
    const button = document.querySelector('#save-job'); button.disabled = true;
    const value = id => document.querySelector(id).value;
    try {
      await api(job ? '/jobs/'+job.id : '/jobs', {method:job ? 'PUT' : 'POST', body:JSON.stringify({title:value('#job-title'),openings:Number(value('#job-openings')),shortlisting_ratio:value('#job-ratio'),minimum_cgpa:Number(value('#job-cgpa')),required_skills:list(value('#job-skills')),preferred_degree:list(value('#job-degrees')),status:value('#job-status')})});
      closeModal(); toast('Position saved.'); await navigate('jobs');
    } catch (err) { if(document.querySelector('#job-errors')) document.querySelector('#job-errors').textContent = err.message; button.disabled = false; }
  };
}

async function openCandidate(id) {
  const token = openModal('A closer look.', 'Loading application details…', loading(), '', 'medium');
  try {
    const s = await api('/candidates/' + id);
    if (token !== modalGeneration) return;
    if (s.batch_id) return batchCandidateModal(s);
    if (s.source === 'Resume upload' && !s.confirmed && s.status === 'ready') return openReview(s);
    candidateModal(s);
  } catch (err) { toast(err.message, true); closeModal(); }
}
function candidateModal(s) {
  const d = s.data, name = d['Full Name'] || d['Candidate ID'] || s.candidate_id;
  const job = jobs.find(j => j.id === s.job_id);
  const upload = s.source === 'Resume upload';
  const weighted=s.recruitment_score ?? s.pipeline_result?.Recruitment_Score;
  const result = s.probability != null ? `<div class="screening-scores">${weighted!=null?`<div class="model-result recruitment-result"><div><strong>Recruitment score</strong><p>Weighted skills, education, projects & experience</p></div><span class="model-score">${Number(weighted).toFixed(2)}<small> / 100</small></span></div>`:''}<div class="classifier-result"><div><strong>ML shortlist signal</strong><p>${e(health.model_name)} · Threshold ${pct(health.threshold)}</p>${badge(s.segment)}</div><div class="classifier-value" title="Raw model output: ${e(s.probability)}">${pct(s.probability)}</div></div><p class="score-explanation">The recruitment score and classifier signal are different measurements. A low shortlist signal does not mean a zero recruitment score.</p></div>` : '';
  const listBlock = (title, values) => `<div class="detail-list"><h4>${title}</h4><div class="pills">${list(values).length ? list(values).map(v => `<span class="pill">${e(v)}</span>`).join('') : '<span class="small muted">Not provided / no listed entries</span>'}</div></div>`;
  const body = `<div class="detail-hero"><span class="avatar">${e(initials(name))}</span><div><h3>${e(name)}</h3><p>${e(job?.title || d['Job Role'])} &nbsp;·&nbsp; ${e(s.id)}</p></div></div>${!['ready','completed'].includes(s.status) && upload ? notice(s.status === 'failed' ? e(s.error) : 'Extraction is still processing. Close this view and reopen it shortly.', s.status === 'failed' ? 'error' : '') : ''}<div class="between"><span class="small muted">${e(s.source)}</span>${badge(s.segment)}</div>${result}<div class="detail-grid"><div class="detail-item"><small>Degree</small><strong>${e(d.Degree || 'Not provided')}</strong></div><div class="detail-item"><small>CGPA</small><strong>${e(d.CGPA ?? 'Not provided')}<span class="small muted"> / 10</span></strong></div><div class="detail-item"><small>${upload ? 'Data confirmation' : 'Dataset score'}</small><strong>${upload ? (s.confirmed ? (s.model_ready===false?'Saved · needs validation':'Validated') : 'Pending') : Number(d.Recruitment_Score).toFixed(1)}</strong></div></div>${listBlock('Skills', d.Skills)}${listBlock('Projects',d.Projects)}${listBlock('Internships',d.Internships)}${listBlock('Certifications',d.Certifications)}${listBlock('Achievements',d.Achievements)}<div style="margin-top:22px">${notice('Model results are suggestions. Review the original evidence and job requirements before recording your decision.')}</div><div class="review-decision"><label for="hr-review">HR decision</label><select class="input" id="hr-review">${['Pending','Reviewed','Shortlisted','Not progressing'].map(v => `<option ${v === s.review ? 'selected' : ''}>${v}</option>`).join('')}</select><button class="btn" id="save-review">Save decision</button></div>${upload ? `<details class="source-details"><summary>Extraction notes</summary><p style="margin-top:10px">${s.extraction_methods?.map(e).join(' · ') || ''}</p><p>${s.warnings?.map(e).join(' ') || ''}</p></details>` : ''}`;
  openModal('Potential, in perspective.', 'Review the evidence. Keep the decision human.', body, `${upload ? `<button class="btn" id="edit-data" ${!['ready','completed'].includes(s.status) ? 'disabled' : ''}>${icon('edit')} Review data</button>` : ''}<button class="btn primary" id="run-model" ${s.model_ready===false || !health.model_ready ? 'disabled' : ''}>${icon('sparkle')} ${s.probability != null ? 'Run model again' : 'Run model'}</button>`, 'medium');
  if(upload&&s.model_ready===true){
    document.querySelector('.modal-footer').insertAdjacentHTML('afterbegin',`<button class="btn" id="download-profile-csv">${icon('download')} Download input CSV</button>`);
    document.querySelector('#download-profile-csv').onclick=event=>downloadApplicationCSV([s.id],'model',event.currentTarget);
  }
  if(upload&&s.confirmed&&s.model_ready===false)document.querySelector('.modal-body').insertAdjacentHTML('afterbegin',notice('Review saved. Validation must pass before the CSV enters the model pipeline: '+e((s.validation_issues||[]).join(' ')),'warning'));
  document.querySelector('#save-review').onclick = async () => {
    const b = document.querySelector('#save-review'); b.disabled = true;
    try { await api('/candidates/'+s.id+'/review', {method:'PATCH',body:JSON.stringify({status:document.querySelector('#hr-review').value})}); toast('HR decision saved.'); if(current in candidateRoutes) loadPool(); }
    catch (err) {toast(err.message,true);} finally {b.disabled=false;}
  };
  if(upload) document.querySelector('#edit-data').onclick = () => openReview(s);
  document.querySelector('#run-model').onclick = async () => {
    const b = document.querySelector('#run-model'); b.disabled = true; b.textContent = 'Running the model…';
    try { await api('/candidates/'+s.id+'/predict', {method:'POST'}); const fresh = await api('/candidates/'+s.id); candidateModal(fresh); toast('Model prediction is ready.'); if(current in candidateRoutes) loadPool(); }
    catch(err) {toast(err.message,true); b.disabled=false; b.innerHTML=icon('sparkle')+' Try prediction again';}
  };
}

const resumeFields = ['Full Name', 'Email', 'Degree', 'Specialization', 'CGPA', 'Class 10 Percentage',
  'Class 12 Percentage', 'Backlogs', 'Skills', 'Projects', 'Internships', 'Certifications', 'Achievements'];
const resumeLists = new Set(['Skills', 'Projects', 'Internships', 'Certifications', 'Achievements', 'Work Experience']);
const decisions = ['Pending HR Review', 'Under Review', 'Selected', 'Rejected', 'On Hold'];

function displayValue(value) {
  if (value == null || value === '') return 'Not Provided';
  if (Array.isArray(value)) return value.length ? value.join(', ') : 'Explicitly empty';
  return typeof value === 'object' ? JSON.stringify(value) : String(value);
}

function batchCandidateModal(s) {
  const name = s.data['Full Name'] || s.filename;
  const original = '/api/screenings/' + encodeURIComponent(s.id) + '/resume';
  const result = s.pipeline_result;
  const currentDecision = s.review === 'Pending' ? decisions[0] : s.review;
  const reviewNotes = (s.field_issues || []).map(item => `<li><strong>${e(item.field)}</strong>
    <p>${e(item.reason)} · Extracted value ${e(displayValue(item.value))}</p>
    ${sourceQuotes(item.evidence, original)}</li>`).join('');
  const editable = ['ready', 'completed'].includes(s.status);
  const field = key => `<div><dt>${e(key)}</dt><dd>${e(displayValue(s.data[key]))}</dd>
    ${s.provenance?.[key]?.origin === 'hr_correction' ? `<dd class="muted">Original value ${e(displayValue(s.raw_extracted[key]))}</dd>` : ''}
    ${sourceQuotes(s.field_evidence?.[key], original)}</div>`;
  const section = (title, content, open = false) =>
    `<details class="ats-disclosure profile-section" ${open ? 'open' : ''}><summary>${title}</summary><div class="profile-section-body">${content}</div></details>`;
  const groups = ['Skills', 'Projects', 'Internships', 'Work Experience', 'Certifications', 'Achievements'];
  const groupedSection = key => {
    const entries = s.evidence?.[key] || [];
    return section(key === 'Achievements' ? 'Achievements and Publications' : key,
      `<dl class="ats-profile-fields">${field(key)}</dl>${entries.length ? `<ul class="ats-entries">${entries.map(entry =>
        `<li><strong>${e(entry.title)}</strong><p>${[entry.organization, entry.date_text].filter(Boolean).map(e).join(' · ')}</p>
          ${entry.description ? `<p>${e(entry.description)}</p>` : ''}
          ${sourceQuotes((entry.page_numbers || []).map(page => ({page, text: entry.source_text})), original)}</li>`).join('')}</ul>` : ''}`);
  };
  const job = s.assessment_job || s.job;
  const allocation = s.shortlist_allocation;
  const displayInputs = record => record && Object.fromEntries(Object.entries(record)
    .filter(([key]) => !['Application ID', 'Candidate ID', 'Job ID'].includes(key)));
  const details = [
    ['Input validation', s.model_ready ? 'Passed' : s.route === 'review' ? 'Needs Data Review' : 'Pending'],
    ['Job', job.title], ['Openings used', job.openings], ['Minimum CGPA', job.minimum_cgpa],
    ['Required skills', job.required_skills?.join(', ')], ['Preferred degrees', job.preferred_degree?.join(', ')],
    ['Assessed at', formatDate(s.assessed_at)],
    ['Active shortlist capacity', allocation?.enforced ? allocation.job.shortlist_capacity : null],
    ['Model', result?.Model_Name],
    ['Model segment', result?.Model_Segment], ['Model threshold', result ? pct(result.Model_Threshold) : null],
    ['ML shortlist score', result ? pct(result.Model_Score) : null], ['Weighted recruitment score', result?.Recruitment_Score],
    ['Job rank', result?.Model_Rank], ['Recruitment rank', result?.Recruitment_Rank],
  ].filter(([, value]) => value != null && value !== '');
  const body = `<div class="batch-profile ats-profile">
    <div class="ats-heading candidate-heading"><span class="avatar" aria-hidden="true">${e(name.trim().split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase())}</span>
      <div><h3>${e(name)}</h3><p>${e(s.job.title)} · <span class="application-reference">Application ${e(s.id.slice(-8))}</span></p></div>${badge(s.segment)}</div>
    ${result ? metrics([['Weighted recruitment score', Number(s.recruitment_score).toFixed(2) + ' / 100', 'model-result'],
      ['ML shortlist score', pct(s.probability)], ['Model threshold', pct(result.Model_Threshold)],
      ['Job rank', result.Model_Rank], ['Recruitment rank', result.Recruitment_Rank]]) : ''}
    ${result ? `<p class="ats-note">${s.route === 'shortlist' ? 'On HR Shortlist.' :
      result.Model_Prediction ? 'Met the model threshold. Ranked outside the available shortlist slots.' : 'Below the model shortlist threshold.'}</p>` : ''}
    ${reviewNotes ? `<section class="review-findings"><h4>Field findings</h4><ul>${reviewNotes}</ul></section>` : ''}
    ${s.error || s.assessment_error ? notice(e(s.error || s.assessment_error), 'error') : ''}
    ${s.warnings?.length ? `<details class="ats-disclosure"><summary>Extraction warnings (${s.warnings.length})</summary><ul>${s.warnings.map(warning => `<li>${e(warning)}</li>`).join('')}</ul></details>` : ''}
    ${section('Overview', `<dl class="ats-profile-fields">${field('Full Name')}${field('Email')}</dl>
      ${s.extracted_at ? `<p class="ats-note">Extracted ${e(formatDate(s.extracted_at))}</p>` : ''}
      ${s.possible_duplicates?.length ? `<p>Possible same-candidate applications</p><ul>
        ${s.possible_duplicates.map(match => `<li>${e(jobs.find(job => job.id === match.job_id)?.title || 'Position unavailable')} · ${e(match.reason)}</li>`).join('')}</ul>` : ''}`, true)}
    ${section('Education', `<dl class="ats-profile-fields">${['Degree','Specialization','CGPA','Class 10 Percentage','Class 12 Percentage','Backlogs'].map(field).join('')}</dl>`)}
    ${groups.map(groupedSection).join('')}
    ${section('Original Resume', `<a href="${original}" target="_blank" rel="noopener">Open original PDF</a>
      <div class="pdf-preview"><iframe src="${original}#toolbar=0" title="Original uploaded resume" loading="lazy"></iframe></div>
      <details class="ats-disclosure source-details"><summary>Extracted text and processing notes</summary>
        <p>${(s.extraction_methods || []).map(e).join(' · ')}</p><pre>${e(s.text)}</pre></details>`)}
    ${section('Assessment Details', `<dl class="ats-profile-fields">${details.map(([label,value]) => `<div><dt>${e(label)}</dt><dd>${e(value)}</dd></div>`).join('')}</dl>
      ${s.evidence ? `<details class="ats-disclosure source-details"><summary>Grouped entries and source evidence</summary><pre>${e(JSON.stringify(s.evidence, null, 2))}</pre></details>` : ''}
      ${s.model_ready_record ? `<details class="ats-disclosure source-details"><summary>Model-ready defaults and classifier inputs</summary>
        <pre>${e(JSON.stringify({model_ready: displayInputs(s.model_ready_record), provenance: s.provenance, classifier_input: displayInputs(s.classifier_record),
          compatibility_fallbacks: s.imputed_fields, job_checks: s.job_checks}, null, 2))}</pre></details>` : ''}
      ${s.correction_history?.length ? `<details class="ats-disclosure source-details"><summary>Correction history</summary><pre>${e(JSON.stringify(s.correction_history, null, 2))}</pre></details>` : ''}`)}
    <section class="batch-decision"><h4>HR decision</h4>
      <div class="batch-actions"><div class="batch-decision-field"><label for="batch-decision">Decision</label><select class="input" id="batch-decision">
        ${[...new Set([...decisions, currentDecision])].map(value => `<option ${value === currentDecision ? 'selected' : ''}>${e(value)}</option>`).join('')}</select></div>
        <label>Reason (optional) <input class="input" id="decision-reason" maxlength="1000"></label><button class="btn" id="save-batch-decision">Save decision</button></div>
      ${s.decision_history?.length ? `<details class="source-details"><summary>Decision history</summary><ul>
        ${s.decision_history.map(item => `<li>${e(item.status)} · ${e(formatDate(item.timestamp))}${item.reason ? ' · ' + e(item.reason) : ''}</li>`).join('')}</ul></details>` : ''}
    </section></div>`;
  openModal('Resume application', 'Review the profile and original evidence.', body,
    `${editable ? '<button class="btn primary" id="correct-resume">Correct and revalidate</button>' : ''}
      ${s.model_ready ? '<button class="btn" id="download-profile-csv">Download input CSV</button>' : ''}`, 'wide');
  const correct = document.querySelector('#correct-resume');
  if (correct) correct.onclick = () => correctionModal(s, original);
  const download = document.querySelector('#download-profile-csv');
  if (download) download.onclick = () => downloadApplicationCSV([s.id], 'model', download);
  document.querySelector('#save-batch-decision').onclick = async event => {
    const button = event.currentTarget;
    const status = document.querySelector('#batch-decision').value;
    if (status !== currentDecision && ['Selected', 'Rejected'].includes(status) &&
        !window.confirm(`Record “${status}” as the HR decision for ${name}?`)) return;
    button.disabled = true;
    const token = modalGeneration;
    try {
      await api('/candidates/' + s.id + '/review', {method: 'PATCH', body: JSON.stringify({
        status, reason: document.querySelector('#decision-reason').value
      })});
      const fresh = await api('/candidates/' + s.id);
      if (token === modalGeneration) batchCandidateModal(fresh);
      if (current in candidateRoutes) loadPool();
      toast('HR decision saved.');
    } catch (error) { toast(error.message, true); button.disabled = false; }
  };
}

function sourceQuotes(sources = [], original) {
  return sources.length ? `<ul class="field-evidence">${sources.map(source =>
    `<li><a href="${original}#page=${source.page}" target="_blank" rel="noopener">Page ${source.page}</a> ${e(source.text)}</li>`).join('')}</ul>` : '';
}

function correctionModal(s, original) {
  const findings = new Set((s.field_issues || []).map(item => item.field));
  const fields = resumeFields;
  const fieldInput = field => {
    const value = s.data[field];
    const attrs = `class="input correction-input" id="correction-${fields.indexOf(field)}" data-field="${e(field)}"`;
    if (resumeLists.has(field)) return `<textarea ${attrs} rows="2">${e(Array.isArray(value) ? value.join('\n') : value ?? '')}</textarea>
      <label><input type="checkbox" data-empty="${e(field)}" ${Array.isArray(value) && !value.length ? 'checked' : ''}> Resume explicitly states none</label>`;
    return `<input ${attrs} value="${e(value ?? '')}">`;
  };
  const body = `<form id="correction-form"><p>Use the <a href="${original}" target="_blank" rel="noopener">original PDF</a> to verify changes.
    Leave absent values blank. Put list entries on separate lines.</p>
    ${findings.has('Resume') ? '<label><input type="checkbox" id="verify-source"> I checked the unreadable pages in the original PDF</label>' : ''}
    <div class="field-grid">
    ${fields.map(field => `<div class="field"><label for="correction-${fields.indexOf(field)}">${field}</label>
      ${fieldInput(field)}${findings.has(field) ? `<p class="queue-error">${e(s.field_issues.filter(item => item.field === field).map(item => item.reason).join(' '))}</p>` : ''}
      ${findings.has(field) ? `<label><input type="checkbox" data-verified="${e(field)}"> I checked this value against the source</label>` : ''}
      ${findings.has(field) ? sourceQuotes(s.field_evidence?.[field], original) : ''}</div>`).join('')}
    </div></form>`;
  openModal('Correct extracted fields', 'Saving revalidates the profile for the next batch run.', body,
    '<button class="btn" id="cancel-correction">Back to profile</button><button class="btn primary" type="submit" form="correction-form">Save and revalidate</button>', 'wide');
  document.querySelector('#cancel-correction').onclick = () => batchCandidateModal(s);
  const form = document.querySelector('#correction-form');
  form.onsubmit = async event => {
    event.preventDefault();
    const data = {};
    form.querySelectorAll('.correction-input').forEach(input => {
      const field = input.dataset.field;
      const value = input.value.trim();
      const verified = form.querySelector(`[data-verified="${field}"]`)?.checked;
      const parsed = resumeLists.has(field) ? (value ? value.split('\n').map(line => line.trim()).filter(Boolean) :
        form.querySelector(`[data-empty="${field}"]`).checked ? [] : null) : value || null;
      const originalValue = s.data[field] ?? null;
      const before = Array.isArray(originalValue) ? JSON.stringify(originalValue) : String(originalValue ?? '');
      const after = Array.isArray(parsed) ? JSON.stringify(parsed) : String(parsed ?? '');
      if (verified || before !== after) data[field] = parsed;
    });
    const sourceVerified = form.querySelector('#verify-source')?.checked || false;
    if (!Object.keys(data).length && !sourceVerified) return toast('Change or verify at least one field.', true);
    const token = modalGeneration;
    const button = document.querySelector('[form="correction-form"]');
    button.disabled = true;
    try {
      const fresh = await api('/screenings/' + s.id + '/data', {method: 'PUT', body: JSON.stringify({data, source_verified: sourceVerified})});
      if (token === modalGeneration) batchCandidateModal(fresh);
      if (current in candidateRoutes) loadPool();
      if (current === 'screening') refreshBatch(s.batch_id);
      toast(fresh.model_ready ? 'Profile revalidated and ready for the next batch run.' : 'Correction saved. Review the remaining field findings.');
    } catch (error) { toast(error.message, true); button.disabled = false; }
  };
}

function openReview(s) {
  const d = s.data || {};
  const field = (key, label) => `<div class="field"><label>${label}</label><input class="input review-field" data-key="${e(key)}" type="text" value="${e(d[key] ?? '')}" readonly aria-label="${e(label)}"></div>`;
  const listField = (key, title) => `<div class="field full"><label>${title}</label><textarea class="input review-list" data-key="${e(key)}" readonly aria-label="${e(title)}">${e(list(d[key]).join('\n'))}</textarea></div>`;
  const body = `<div class="review-layout"><div><div class="pdf-preview"><iframe src="/api/screenings/${encodeURIComponent(s.id)}/resume#toolbar=0" title="Original uploaded resume"></iframe></div><div class="small muted" style="margin-top:10px;font-size:10px">${e(s.filename)} · <a target="_blank" rel="noopener" href="/api/screenings/${encodeURIComponent(s.id)}/resume">Open original PDF</a></div><details class="source-details"><summary>View extracted text & OCR notes</summary><p>${s.extraction_methods?.map(e).join(' · ') || ''}</p><pre>${e(s.text || '')}</pre></details></div><section class="review-form" aria-label="Extracted resume preview"><h3>${e(jobs.find(j=>j.id===s.job_id)?.title || 'Selected position')}</h3><p class="small muted" style="margin:12px 0 20px">Extracted information from the resume. Missing details are left empty.</p><div class="field-grid">${field('Full Name','Full name')}${field('Email','Email')}${field('Degree','Degree')}${field('Specialization','Specialization')}${field('CGPA','CGPA · 10-point scale')}${field('Backlogs','Backlogs')}${field('Class 10 Percentage','Class 10 percentage')}${field('Class 12 Percentage','Class 12 percentage')}${listField('Skills','Skills')}${listField('Projects','Projects')}${listField('Internships','Internships')}${listField('Certifications','Certifications')}${listField('Achievements','Achievements')}</div><div class="model-counts" style="margin-top:20px">${['Projects','Internships','Certifications','Achievements'].map(key=>`<div><small>Number of ${key}</small><strong>${d[key] == null ? '' : list(d[key]).length}</strong></div>`).join('')}</div></section></div>`;
  openModal('Resume preview', 'View extracted information alongside the original PDF.', body, `<button class="btn primary" id="preview-run-model" ${!health.model_ready ? 'disabled' : ''}>${icon('sparkle')} Run model</button>`, 'wide');
  document.querySelector('.review-form').insertAdjacentHTML('beforeend', '<div id="preview-model-status" role="status" aria-live="polite"></div>');
  if (Object.keys(s.imputed_fields || {}).length) document.querySelector('#preview-model-status').innerHTML = notice('Before CSV export or prediction, missing inputs are handled using notebook 03 rules. Automatically filled: '+Object.entries(s.imputed_fields).map(([key, info])=>e(key)+': '+e(info.value)+' ('+e(info.method)+')').join('; '));
  document.querySelector('#preview-run-model').onclick = async () => {
    const button = document.querySelector('#preview-run-model'), token = modalGeneration;
    button.disabled = true;
    button.textContent = 'Validating model inputs…';
    try {
      const validated = await api('/screenings/'+s.id);
      if (token !== modalGeneration) return;
      if (!validated.model_ready) {
        document.querySelector('#preview-model-status').innerHTML = notice('The pipeline cannot run with these missing or invalid inputs: '+e((validated.validation_issues || []).join(' ')), 'warning');
        return;
      }
      button.textContent = 'Running the model…';
      await api('/candidates/'+s.id+'/predict', {method:'POST'});
      const fresh = await api('/screenings/'+s.id);
      if (token !== modalGeneration) return;
      candidateModal(fresh);
      toast('Model prediction is ready.');
      if (current in candidateRoutes) loadPool();
    } catch (err) {
      if (token === modalGeneration) document.querySelector('#preview-model-status').innerHTML = notice(e(err.message), 'error');
    } finally {
      if (button.isConnected) {button.disabled=false; button.innerHTML=icon('sparkle')+' Run model';}
    }
  };
  if(s.evidence && Object.keys(s.evidence).length) document.querySelector('.review-layout>div').insertAdjacentHTML('beforeend', `<details class="source-details"><summary>Structured source evidence</summary><pre>${e(JSON.stringify(s.evidence, null, 2))}</pre></details>`);
  if(s.evidence?.['Work Experience']?.length) document.querySelector('.review-layout>div').insertAdjacentHTML('beforeend', `<details class="source-details" open><summary>Work experience</summary>${s.evidence['Work Experience'].map(entry=>`<div class="detail-list"><h4>${e(entry.title)}</h4><p>${e(entry.description || '')}</p></div>`).join('')}</details>`);
}

if(sessionStorage.getItem('sprout-demo')) start(); else login();

'use strict';
const LS = 'fanta-asta-v1', LSD = LS + '-data', LSR = LS + '-rose';
const ROLES = ['POR', 'DIF', 'CEN', 'ATT'];
const BUILTIN = { partecipanti: 10, crediti: 1000, slot: { POR: 3, DIF: 8, CEN: 8, ATT: 6 } };
const NUMRE = /^(Pres|Gol|xG|Assist|xA|Fantamedia|Indice|Titolarit|Continuit|MV|Prezzo_|Punteggio|Età|Forma)/;

let DATA = [], HEADERS = [], PRICE = '', TEAMCOL = '', GOLP = '', XGP = '', ASSP = '', XAP = '', PRESP = '';
let GOLC = '', XGC = '', ASSC = '', XAC = '', PRESC = '', FMP = '', FML = '', TIT = '';
let ROSE = [];
let state = null, sort = { col: 'Punteggio Asta (/100)', dir: -1 }, filt = { q: '', role: 'ALL', free: true, gem: false, star: false, shop: false };
let expanded = null;

const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const num = v => { const n = parseFloat(String(v).replace(',', '.')); return isNaN(n) ? null : n; };

function roleOf(v) {
  v = String(v || '').toUpperCase();
  if (v.startsWith('POR')) return 'POR';
  if (v.startsWith('DIF')) return 'DIF';
  if (v.startsWith('CEN') || v.startsWith('TRE') || v === 'C' || v === 'T') return 'CEN';
  if (v.startsWith('ATT') || v === 'A') return 'ATT';
  return v;
}

function blankSetup(cfg) {
  const n = cfg.partecipanti || 10;
  return { credits: cfg.crediti || 1000, slots: Object.assign({}, BUILTIN.slot, cfg.slot), teams: Array.from({ length: n }, (_, i) => 'Squadra ' + (i + 1)), mine: 0 };
}
function blankState(cfg) { return { setup: blankSetup(cfg), assigned: {}, stars: [], shop: {}, hist: [], cols: null }; }

function save() { try { localStorage.setItem(LS, JSON.stringify(state)); } catch (e) {} }
function load() { try { const s = JSON.parse(localStorage.getItem(LS)); if (s && s.setup) return s; } catch (e) {} return null; }

function setData(rows) {
  DATA = rows;
  HEADERS = Object.keys(rows[0] || {});
  PRICE = HEADERS.find(h => /^Prezzo_/.test(h)) || '';
  TEAMCOL = HEADERS.find(h => /^Squadra Attuale/.test(h)) || 'Squadra';
  GOLP = HEADERS.find(h => /^Gol /.test(h)) || '';
  XGP = HEADERS.find(h => /^xG /.test(h)) || '';
  ASSP = HEADERS.find(h => /^Assist /.test(h)) || '';
  XAP = HEADERS.find(h => /^xA /.test(h)) || '';
  PRESP = HEADERS.find(h => /^Pres /.test(h)) || '';
  const gol = HEADERS.filter(h => /^Gol /.test(h)), xg = HEADERS.filter(h => /^xG /.test(h));
  const ass = HEADERS.filter(h => /^Assist /.test(h)), xa = HEADERS.filter(h => /^xA /.test(h));
  const pres = HEADERS.filter(h => /^Pres /.test(h));
  GOLC = gol[1] || ''; XGC = xg[1] || ''; ASSC = ass[1] || ''; XAC = xa[1] || ''; PRESC = pres[1] || '';
  FMP = HEADERS.includes('Fantamedia Prev') ? 'Fantamedia Prev' : '';
  FML = HEADERS.includes('Fantamedia Live') ? 'Fantamedia Live' : '';
  TIT = HEADERS.includes('Titolarità') ? 'Titolarità' : '';
  if (!HEADERS.includes(sort.col)) sort = { col: 'Punteggio Asta (/100)', dir: -1 };
  try { localStorage.setItem(LSD, JSON.stringify(rows)); } catch (e) {}
  $('filestatus').textContent = rows.length + ' giocatori caricati';
  renderAll();
}

function teamStats() {
  const s = state.setup;
  return s.teams.map((name, i) => {
    const ros = Object.entries(state.assigned).filter(([, a]) => a.t === i)
      .map(([n, a]) => ({ n, p: a.p, r: roleOf(byName(n)?.['Ruolo']) }));
    const spent = ros.reduce((t, x) => t + (+x.p || 0), 0);
    const per = {}; ROLES.forEach(r => per[r] = ros.filter(x => x.r === r));
    const filled = ros.length, total = ROLES.reduce((t, r) => t + (+s.slots[r] || 0), 0);
    const left = s.credits - spent, open = total - filled;
    return { i, name, ros, spent, left, per, open, maxBid: left - open };
  });
}
const byName = n => DATA.find(r => r['Calciatore'] === n);

// ---------- listone ----------
const DEFAULT_COLS = () => ['Calciatore', 'Ruolo', TEAMCOL, 'Punteggio Asta (/100)', PRICE, FMP, GOLP, XGP].filter(c => c && HEADERS.includes(c));
const visibleCols = () => {
  const v = (state.cols || []).filter(c => HEADERS.includes(c));
  return v.length ? v : DEFAULT_COLS();
};
const SHORT = { 'Calciatore': 'Giocatore', 'Ruolo': 'R', 'Punteggio Asta (/100)': 'Punt.', 'Fantamedia Prev': 'FM', 'Fantamedia Live': 'FML', 'Hidden Gem?': 'Gem', 'Infortunato': 'Inf', 'Alternative Affini': 'Altern.', 'Dettaglio infortunio': 'Dettaglio inf.', 'Consiglio rif.': 'Rif.', 'Nazionalità': 'Naz.', 'Forma media': 'Forma', 'Forma serie': 'Serie' };
const shortLbl = c => SHORT[c] || (c === TEAMCOL ? 'Squadra' : (/^Prezzo_/.test(c) ? 'Prz' : c));

function filtered() {
  const q = filt.q.trim().toLowerCase();
  let rows = DATA.filter(r => {
    if (filt.free && state.assigned[r['Calciatore']]) return false;
    if (filt.role !== 'ALL' && roleOf(r['Ruolo']) !== filt.role) return false;
    if (filt.gem && r['Hidden Gem?'] !== 'SÌ') return false;
    if (filt.star && !state.stars.includes(r['Calciatore'])) return false;
    if (filt.shop && !state.shop[r['Calciatore']]) return false;
    if (q && !(String(r['Calciatore']).toLowerCase().includes(q) || String(r[TEAMCOL]).toLowerCase().includes(q))) return false;
    return true;
  });
  const { col, dir } = sort;
  rows = rows.slice().sort((a, b) => {
    if (col === 'Calciatore') return dir * String(a[col]).localeCompare(String(b[col]));
    const x = num(a[col]), y = num(b[col]);
    if (x === null && y === null) return 0;
    if (x === null) return 1; if (y === null) return -1;
    return dir * (x - y);
  });
  return rows;
}

function renderList() {
  const cols = visibleCols();
  $('thead').innerHTML = '<th></th>' + cols.map(c => {
    const arrow = sort.col === c ? (sort.dir === 1 ? ' ▲' : ' ▼') : '';
    const cls = NUMRE.test(c) && c !== 'Calciatore' ? ' class="num"' : '';
    return `<th${cls} data-c="${esc(c)}">${esc(shortLbl(c))}${arrow}</th>`;
  }).join('') + '<th>Stato</th>';
  $('thead').querySelectorAll('th[data-c]').forEach(th => th.onclick = () => {
    const c = th.dataset.c;
    sort = sort.col === c ? { col: c, dir: -sort.dir } : { col: c, dir: c === 'Calciatore' ? 1 : -1 };
    renderList();
  });
  const rows = filtered();
  $('count').textContent = rows.length + ' / ' + DATA.length + ' giocatori';
  const tb = $('tbody');
  tb.innerHTML = '';
  const frag = document.createDocumentFragment();
  rows.slice(0, 500).forEach(r => {
    const n = r['Calciatore'], a = state.assigned[n], star = state.stars.includes(n), shop = state.shop[n];
    const tr = document.createElement('tr');
    if (a) tr.className = 'taken'; if (star) tr.className += ' star'; if (shop) tr.className += ' shop';
    let tds = `<td><button class="starbtn${star ? ' on' : ''}" data-star="${esc(n)}">★</button></td>`;
    cols.forEach(c => {
      let v = r[c];
      if (c === PRICE || c === 'Punteggio Asta (/100)') { const x = num(v); v = x === null ? '—' : (c === PRICE ? Math.round(x) : x); }
      const cls = NUMRE.test(c) && c !== 'Calciatore' ? ' class="num"' : '';
      tds += `<td${cls}>${esc(v)}</td>`;
    });
    let st;
    if (a) {
      const diff = PRICE ? num(r[PRICE]) - a.p : null;
      const b = diff === null ? '' : diff >= 0 ? ` <span class="badge hit">colpo +${Math.round(diff)}</span>` : ` <span class="badge miss">pacco ${Math.round(diff)}</span>`;
      st = `${esc(state.setup.teams[a.t])} ${a.p}${b}`;
    } else st = `<button data-assign="${esc(n)}">Assegna</button>`;
    tds += `<td>${st}</td>`;
    tr.innerHTML = tds;
    tr.ondblclick = () => { expanded = expanded === n ? null : n; renderList(); };
    if (expanded === n) {
      const d = document.createElement('tr');
      d.className = 'detail';
      d.innerHTML = `<td colspan="${cols.length + 2}">${detailHtml(r)}</td>`;
      frag.appendChild(tr); frag.appendChild(d);
    } else frag.appendChild(tr);
  });
  tb.appendChild(frag);
  if (rows.length > 500) $('count').textContent += ' (primi 500 — restringi la ricerca)';
  tb.querySelectorAll('[data-star]').forEach(b => b.onclick = e => { e.stopPropagation(); toggleStar(b.dataset.star); });
  tb.querySelectorAll('[data-assign]').forEach(b => b.onclick = () => { expanded = b.dataset.assign; renderList(); setTimeout(() => $('as-team')?.focus(), 0); });
  bindDetail(tb);
}

function parseSkills(s) {
  if (!s) return [];
  const t = String(s).trim();
  if (!t || t === '[]') return [];
  try { const j = JSON.parse(t.replace(/'/g, '"')); return Array.isArray(j) ? j : [t]; }
  catch (e) { return t.replace(/[\[\]]/g, '').split(',').map(x => x.trim()).filter(Boolean); }
}
const isTrue = v => v === true || v === 1 || String(v).toLowerCase() === 'true';
const fmt = (v, d = 0) => { const n = num(v); return n === null ? '—' : (d ? n.toFixed(d) : Math.round(n)); };

function seasonLine(pref, g, x, a, xa, pr) {
  const gv = num(g), xv = num(x);
  let delta = '';
  if (gv !== null && xv !== null && xv - gv >= 2) delta = ` <span class="good">(${(xv - gv >= 0 ? '+' : '') + (xv - gv).toFixed(1)} xG)</span>`;
  return `Pres <b>${fmt(pr)}</b> · Gol <b>${fmt(g)}</b> · xG <b>${fmt(x, 1)}</b>${delta} · Ass <b>${fmt(a)}</b> · xA <b>${fmt(xa, 1)}</b>`;
}

function detailHtml(r) {
  const n = r['Calciatore'], a = state.assigned[n], shop = state.shop[n];
  const inj = isTrue(r['Infortunato']);
  const trend = String(r['Trend'] || '');
  const tcls = trend === 'UP' ? 'up' : trend === 'DOWN' ? 'down' : '';
  const gem = r['Hidden Gem?'] === 'SÌ';
  const tit = num(TIT ? r[TIT] : null);
  const skills = parseSkills(r['Skills']).map(s => `<span class="chip">${esc(s)}</span>`).join('') || '—';
  const cons = isTrue(r['Consigliato']) ? ' <b class="up">✓ consigliato</b>' : '';
  const eta = r['Età'] ? ` · ${esc(r['Età'])} anni` : '';
  const naz = r['Nazionalità'] ? ` · ${esc(r['Nazionalità'])}` : '';
  // forma ultime gare
  let formaHtml = '';
  const serie = String(r['Forma serie'] || '').split('|').map(num).filter(v => v !== null);
  if (serie.length) {
    const d = serie[serie.length - 1] - serie[0];
    const dc = d > 0 ? 'up' : d < 0 ? 'down' : '';
    formaHtml = `<div class="dsec">Forma ultime gare</div>
      <div class="drow"><span>${serie.join(' · ')}</span><span>media <b>${esc(r['Forma media'])}</b></span>
      ${serie.length > 1 ? `<span class="${dc}"><b>${d > 0 ? '+' : ''}${d.toFixed(1)}</b></span>` : ''}</div>`;
  }
  // consiglio editoriale
  const consiglio = r['Consiglio'] ? `<div class="dsec">Consiglio ${esc(r['Consiglio rif.'] || '')}</div>
    <div><i>“${esc(String(r['Consiglio']).slice(0, 400))}”</i></div>` : '';
  // simili con nostro punteggio
  let similiHtml = '';
  const sims = String(r['Simili'] || '').split('|').map(s => s.trim()).filter(Boolean);
  if (sims.length) {
    similiHtml = '<div class="dsec">Simili in squadra (nostro punteggio)</div><div>' + sims.map(s => {
      const m = byName(s);
      return m ? `<span class="chip"><b>${esc(s)}</b> ${fmt(m['Punteggio Asta (/100)'], 1)} · ${fmt(m[PRICE])}</span>` : `<span class="chip">${esc(s)}</span>`;
    }).join('') + '</div>';
  }
  const dett = r['Dettaglio infortunio'] ? `<div>🏥 <b class="down">${esc(r['Dettaglio infortunio'])}</b></div>` : '';
  const opts = state.setup.teams.map((t, i) => `<option value="${i}"${i === state.setup.mine ? ' selected' : ''}>${esc(t)}</option>`).join('');
  return `<div class="dhead"><span class="nm">${esc(n)}</span><span class="sub">${esc(r['Ruolo'])} · ${esc(r[TEAMCOL])}${eta}${naz}</span>
    ${gem ? '<span class="badge gem">GEM</span>' : ''}${inj ? '<span class="badge inj">INFORTUNATO</span>' : ''}</div>
    ${dett}
    <div class="drow"><span>Prz <span class="dbig">${fmt(r[PRICE])}</span></span>
    <span>Punteggio <span class="dbig">${fmt(r['Punteggio Asta (/100)'], 1)}</span></span>
    <span>FM prev <b>${fmt(r[FMP], 1)}</b> · live <b>${fmt(r[FML], 1)}</b></span>
    <span>Trend <b class="${tcls}">${esc(trend || '—')}</b>${cons}</span></div>
    <div class="dsec">Stagione scorsa${GOLP ? ' — ' + esc(GOLP.replace('Gol ', '')) : ''}</div>
    <div>${seasonLine(0, r[GOLP], r[XGP], r[ASSP], r[XAP], r[PRESP])}</div>
    ${GOLC ? `<div class="dsec">Stagione live — ${esc(GOLC.replace('Gol ', ''))}</div><div>${seasonLine(0, r[GOLC], r[XGC], r[ASSC], r[XAC], r[PRESC])}</div>` : ''}
    <div class="dsec">Stato</div>
    <div class="drow"><span>Titolarità ${tit === null ? '—' : `<b>${Math.round(tit)}%</b> <span class="bar"><i style="width:${Math.min(100, Math.max(0, tit))}%"></i></span>`}</span>
    <span>Indice <b>${fmt(r['Indice Esterno'])}</b></span>
    <span>Resist. infort. <b>${esc(r['Resist. infort.'] || '—')}</b></span>
    <span>Gol/ass prev. <b>${esc(r['Gol prev.'] || '—')}/${esc(r['Assist prev.'] || '—')}</b></span></div>
    <div style="margin-top:4px">${skills}</div>
    ${r['Motivo'] && r['Motivo'] !== '-' ? `<div><i>${esc(r['Motivo'])}</i></div>` : ''}
    ${formaHtml}
    ${consiglio}
    ${similiHtml}
    ${r['Alternative Affini'] ? `<div class="dsec">Alternative</div><div>${esc(r['Alternative Affini'])}</div>` : ''}
    <div class="row" style="margin-top:8px">
      <select id="as-team">${opts}</select>
      <input id="as-price" type="number" min="1" value="${Math.round(num(r[PRICE]) || 1)}" style="width:80px">
      <button id="as-go">${a ? 'Riassegna' : 'Assegna'}</button>
      ${a ? '<button id="as-rm">Svincola</button>' : ''}
    </div>
    ${shop ? `<div class="row">📝 target <input id="sh-target" type="number" min="0" value="${esc(shop.target || '')}" style="width:70px">
      <input id="sh-note" value="${esc(shop.note || '')}" placeholder="nota…" style="flex:1;min-width:120px">
      <button id="sh-save">Salva</button><button id="sh-rm">Togli</button></div>`
    : `<div class="row"><button id="sh-add">+ Lista spesa</button></div>`}`;
}

function bindDetail(tb) {
  const go = $('as-go');
  if (!go) return;
  go.onclick = () => {
    const t = +$('as-team').value, p = +$('as-price').value || 1;
    assign(expanded, t, p); expanded = null; renderAll();
  };
  const rm = $('as-rm');
  if (rm) rm.onclick = () => { unassign(expanded); expanded = null; renderAll(); };
  $('sh-save') && ($('sh-save').onclick = () => {
    state.shop[expanded] = { target: $('sh-target').value, note: $('sh-note').value };
    save(); renderAll();
  });
  const add = $('sh-add');
  if (add) add.onclick = () => { state.shop[expanded] = { target: '', note: '' }; save(); renderAll(); };
  const sr = $('sh-rm');
  if (sr) sr.onclick = () => { delete state.shop[expanded]; save(); renderAll(); };
}

function toggleStar(n) {
  const i = state.stars.indexOf(n);
  if (i >= 0) state.stars.splice(i, 1); else state.stars.push(n);
  save(); renderList();
}
function assign(n, t, p) { state.hist.push({ op: 'assign', n, prev: state.assigned[n] || null }); state.assigned[n] = { t, p }; save(); }
function unassign(n) { state.hist.push({ op: 'unassign', n, prev: state.assigned[n] || null }); delete state.assigned[n]; save(); }

// ---------- squadre ----------
function renderTeams() {
  const ts = teamStats(), me = ts[state.setup.mine] || ts[0];
  const slotHtml = t => ROLES.map(r => `${r} ${t.per[r].length}/${state.setup.slots[r] || 0}`).join(' · ');
  const rosHtml = (t, removable) => {
    const items = [];
    ROLES.forEach(r => t.per[r].forEach(x => items.push(`<li>${esc(x.n)} (${r}) — ${x.p}${removable ? ` <button class="rm" data-rm="${esc(x.n)}">✕</button>` : ''}</li>`)));
    return items.length ? `<ul class="roster">${items.join('')}</ul>` : '<i>rosa vuota</i>';
  };
  $('myteam').innerHTML = `<div class="card"><h2>⭐ ${esc(me.name)} (mia)</h2>
    <div class="row"><b>Residuo: ${me.left}</b><span>Speso: ${me.spent}</span><span>Max offerta: <b>${me.maxBid}</b></span></div>
    <div>${slotHtml(me)}</div>${rosHtml(me, true)}</div>`;
  const need = ROLES.filter(r => me.per[r].length < (+state.setup.slots[r] || 0));
  const alerts = need.map(r => {
    const who = ts.filter(t => t.i !== me.i && t.per[r].length < (+state.setup.slots[r] || 0)).map(t => esc(t.name)).join(', ');
    return who ? `<div>⚠️ ${r}: cercano anche ${who}</div>` : '';
  }).join('');
  $('opps').innerHTML = alerts + ts.filter(t => t.i !== me.i).map(t =>
    `<div class="card"><b>${esc(t.name)}</b> — residuo ${t.left}, speso ${t.spent}, max ${t.maxBid}<br>${slotHtml(t)}${rosHtml(t, true)}</div>`
  ).join('');
  $('opps').querySelectorAll('[data-rm]').forEach(b => b.onclick = () => { unassign(b.dataset.rm); renderAll(); });
  $('myteam').querySelectorAll('[data-rm]').forEach(b => b.onclick = () => { unassign(b.dataset.rm); renderAll(); });
}

// ---------- setup ----------
function renderSetup() {
  const s = state.setup;
  $('s-credits').value = s.credits;
  $('s-por').value = s.slots.POR; $('s-dif').value = s.slots.DIF; $('s-cen').value = s.slots.CEN; $('s-att').value = s.slots.ATT;
  $('s-teams').innerHTML = s.teams.map((t, i) =>
    `<div class="row"><input data-t="${i}" value="${esc(t)}"><label><input type="radio" name="mine" value="${i}"${i === s.mine ? ' checked' : ''}> mia</label>${s.teams.length > 2 ? `<button class="rm" data-del="${i}">✕</button>` : ''}</div>`
  ).join('');
  $('s-teams').querySelectorAll('[data-del]').forEach(b => b.onclick = () => {
    const i = +b.dataset.del;
    state.setup.teams.splice(i, 1);
    Object.keys(state.assigned).forEach(n => { if (state.assigned[n].t === i) delete state.assigned[n]; else if (state.assigned[n].t > i) state.assigned[n].t--; });
    if (state.setup.mine >= state.setup.teams.length) state.setup.mine = 0;
    save(); renderAll();
  });
  renderCols();
}

function renderCols() {
  const box = $('s-cols');
  if (!DATA.length) { box.innerHTML = '<i>Carica prima il JSON dal Listone per configurare le colonne.</i>'; $('s-prevh').innerHTML = ''; $('s-prevb').innerHTML = ''; return; }
  const vis = new Set(visibleCols());
  box.innerHTML = HEADERS.map(h => `<label><input type="checkbox" data-col="${esc(h)}"${vis.has(h) ? ' checked' : ''}> ${esc(shortLbl(h))}</label>`).join('');
  box.querySelectorAll('[data-col]').forEach(cb => cb.onchange = () => {
    const sel = [...box.querySelectorAll('[data-col]:checked')].map(x => x.dataset.col);
    state.cols = HEADERS.filter(h => sel.includes(h));
    save(); renderCols(); renderList();
  });
  const cols = visibleCols();
  $('s-prevh').innerHTML = cols.map(c => `<th>${esc(shortLbl(c))}</th>`).join('');
  $('s-prevb').innerHTML = DATA.slice(0, 3).map(r =>
    `<tr>${cols.map(c => `<td>${esc(r[c])}</td>`).join('')}</tr>`).join('');
}

// ---------- infortunati ----------
function renderInf() {
  const rows = DATA.filter(r => r['Dettaglio infortunio'] || isTrue(r['Infortunato']))
    .sort((a, b) => String(a['Calciatore']).localeCompare(String(b['Calciatore'])));
  $('infcount').textContent = rows.length + ' indisponibili';
  $('infbody').innerHTML = rows.map(r => {
    const n = r['Calciatore'], a = state.assigned[n];
    return `<tr${a ? ' class="taken"' : ''}><td><b>${esc(n)}</b></td><td>${esc(roleOf(r['Ruolo']))}</td>
      <td>${esc(r[TEAMCOL])}</td><td>${esc(r['Dettaglio infortunio'] || 'infortunato')}</td>
      <td>${a ? esc(state.setup.teams[a.t]) + ' ' + a.p : 'libero'}</td></tr>`;
  }).join('');
}

// ---------- serie A ----------
function setRose(rose) {
  ROSE = rose.slice().sort((a, b) => String(a.squadra).localeCompare(String(b.squadra)));
  try { localStorage.setItem(LSR, JSON.stringify(ROSE)); } catch (e) {}
  $('rosestatus').textContent = ROSE.length + ' squadre caricate';
  $('roseteam').innerHTML = '<option value="-1">Tutte le squadre</option>' +
    ROSE.map((t, i) => `<option value="${i}">${esc(t.squadra)}</option>`).join('');
  renderRose();
}
function roseCard(t) {
  const byRole = { POR: [], DIF: [], CEN: [], ATT: [] }, other = [];
  (t.formazione || []).forEach(s => {
    const m = DATA.find(r => String(r['Calciatore']).split(' ')[0] === s);
    if (m) byRole[roleOf(m['Ruolo'])].push({ s, m });
    else other.push(s);
  });
  const jumpScore = x => {
    const sc = fmt(x.m['Punteggio Asta (/100)'], 1);
    return `<button data-jump="${esc(x.s)}">${esc(x.s)} <b>${sc}</b></button>`;
  };
  const fgroups = ['POR', 'DIF', 'CEN', 'ATT'].filter(r => byRole[r].length)
    .map(r => `<div><b>${r}</b> ${byRole[r].map(jumpScore).join(' ')}</div>`).join('')
    + (other.length ? `<div><b>?</b> ${other.map(s => `<button data-jump="${esc(s)}">${esc(s)}</button>`).join(' ')}</div>` : '');
  const jump = s => `<button data-jump="${esc(s)}">${esc(s)}</button>`;
  return `<div class="card"><h2>${esc(t.squadra)} ${t.modulo ? '· <b>' + esc(t.modulo) + '</b>' : ''}</h2>
    <div class="dsec">Formazione probabile per ruolo (click = cerca nel listone)</div>
    ${fgroups || '—'}
    <div class="dsec">Rigoristi</div><div>${(t.rigoristi || []).map(esc).join(' · ') || '—'}</div>
    <div class="dsec">Migliori</div><div>${(t.migliori || []).map(esc).join(' · ') || '—'}</div></div>`;
}
function renderRose() {
  if (!ROSE.length) { $('rosecard').innerHTML = '<i>Carica il JSON rose (output pipeline) per vedere moduli e formazioni.</i>'; return; }
  const v = +$('roseteam').value;
  const list = v >= 0 ? [ROSE[v]] : ROSE;
  $('rosecard').innerHTML = list.map(roseCard).join('');
  $('rosecard').querySelectorAll('[data-jump]').forEach(b => b.onclick = () => {
    filt.q = b.dataset.jump; $('q').value = filt.q;
    document.querySelector('nav button[data-view=list]').click();
    renderList();
  });
}

// ---------- shell ----------
function renderAll() { renderList(); renderTeams(); renderSetup(); renderInf(); renderRose(); }

function readFile(file, cb) {
  const rd = new FileReader();
  rd.onload = () => {
    try {
      const j = JSON.parse(rd.result);
      const rows = Array.isArray(j) ? j : j.players || j.records || j.data || j.rows;
      if (!rows || !rows.length) throw 0;
      setData(rows);
    } catch (e) { alert('JSON non valido: serve array di righe (sidecar pipeline)'); }
  };
  rd.readAsText(file);
}

function init() {
  state = load();
  fetch('config.json').then(r => r.json()).then(cfg => { if (!state) { state = blankState(cfg); save(); } renderSetup(); })
    .catch(() => { if (!state) { state = blankState(BUILTIN); save(); } renderSetup(); });
  try { const d = JSON.parse(localStorage.getItem(LSD)); if (d && d.length) setData(d); } catch (e) {}
  try { const rz = JSON.parse(localStorage.getItem(LSR)); if (rz && rz.length) setRose(rz); } catch (e) {}
  $('rosefile').onchange = e => {
    const f = e.target.files[0]; if (!f) return;
    const rd = new FileReader();
    rd.onload = () => { try { const j = JSON.parse(rd.result); if (!j.length) throw 0; setRose(j); } catch (err) { alert('Rose JSON non valido'); } };
    rd.readAsText(f);
  };
  $('roseteam').onchange = renderRose;
  document.querySelectorAll('nav button').forEach(b => b.onclick = () => {
    document.querySelectorAll('nav button').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    document.querySelectorAll('.view').forEach(v => v.hidden = true);
    $('view-' + b.dataset.view).hidden = false;
  });
  $('file').onchange = e => e.target.files[0] && readFile(e.target.files[0]);
  let deb; $('q').oninput = e => { clearTimeout(deb); deb = setTimeout(() => { filt.q = e.target.value; renderList(); }, 120); };
  ['ALL', ...ROLES].forEach(r => {
    const b = document.createElement('button');
    b.textContent = r === 'ALL' ? 'Tutti' : r;
    b.className = r === 'ALL' ? 'on' : '';
    b.onclick = () => { filt.role = r; $('rolebtns').querySelectorAll('button').forEach(x => x.classList.remove('on')); b.classList.add('on'); renderList(); };
    $('rolebtns').appendChild(b);
  });
  $('f-free').onchange = e => { filt.free = e.target.checked; renderList(); };
  $('f-gem').onchange = e => { filt.gem = e.target.checked; renderList(); };
  $('f-star').onchange = e => { filt.star = e.target.checked; renderList(); };
  $('f-shop').onchange = e => { filt.shop = e.target.checked; renderList(); };
  $('undo').onclick = () => {
    const h = state.hist.pop();
    if (!h) return;
    if (h.prev) state.assigned[h.n] = h.prev; else delete state.assigned[h.n];
    save(); renderAll();
  };
  $('s-add').onclick = () => { state.setup.teams.push('Squadra ' + (state.setup.teams.length + 1)); save(); renderAll(); };
  $('s-save').onclick = () => {
    state.setup.credits = +$('s-credits').value || state.setup.credits;
    state.setup.slots = { POR: +$('s-por').value || 0, DIF: +$('s-dif').value || 0, CEN: +$('s-cen').value || 0, ATT: +$('s-att').value || 0 };
    $('s-teams').querySelectorAll('[data-t]').forEach(inp => state.setup.teams[+inp.dataset.t] = inp.value || ('Squadra ' + (+inp.dataset.t + 1)));
    const m = document.querySelector('input[name=mine]:checked');
    if (m) state.setup.mine = +m.value;
    save(); renderAll();
  };
  $('s-export').onclick = () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(state)], { type: 'application/json' }));
    a.download = 'asta-stato.json'; a.click();
  };
  $('s-import').onchange = e => {
    const f = e.target.files[0]; if (!f) return;
    const rd = new FileReader();
    rd.onload = () => { try { state = JSON.parse(rd.result); save(); renderAll(); } catch (err) { alert('Stato non valido'); } };
    rd.readAsText(f);
  };
  $('s-reset').onclick = () => { if (confirm('Azzera assegnazioni?')) { state.assigned = {}; state.hist = []; save(); renderAll(); } };
  renderAll();
}
document.addEventListener('DOMContentLoaded', init);

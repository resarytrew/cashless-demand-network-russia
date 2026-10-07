/* Presentation of saved results only. Coordinates below are editorial, never geographic. */
'use strict';
const $ = id => document.getElementById(id);
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const nf = new Intl.NumberFormat('ru-RU', {maximumFractionDigits: 0});
const pct = v => (100 * v).toLocaleString('ru-RU', {maximumFractionDigits: 1}) + '%';
const safe = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const states = {stable_core:'Устойчивое ядро', expansive_core:'Расширяющееся ядро', transition:'Переходная область', unresolved:'Неопределённая граница'};
const notes = {
 A:['Перекрывающийся профиль','Существенная часть ядра сохраняется, но метрическое отделение слабее сетевой связности. Высокие внешние зарплаты не устанавливают отраслевой или добывающий механизм.'],
 B:['Вложенный внутригородской профиль','Все 98 референсных участников относятся к внутригородским территориям федеральных городов. Это часть данной страты, а не все федеральные города. Граница с E изменчива.'],
 C:['Контекстный, неразрешённый','Компактность ослабевает после контекстных контролей. Сохранение некоторых участников при возмущении не устраняет эту оговорку.'],
 D:['Компактное ядро, изменчивые границы','Внутреннее сходство выражено, но точный состав меняется при изменении параметров и алгоритма. Высокое сохранение ядра сочетается с включением соседних территорий.'],
 E:['Вложенный, зависимый от контекста','Исходная компактность частично объясняется географией и городским масштабом. B и E могут объединяться при смене алгоритма или возмущении сети.'],
 F:['Переходная область','Точный состав чувствителен к параметрам; соседство распределяется между D и G, частично A. Внешние показатели дополняют интерпретацию, не делают границу устойчивой.'],
 G:['Широкий макропрофиль','Крупнейшая группа охватывает около половины панели. Широкое ядро часто сохраняется, но контекстные эффекты и нестабильность части участников ограничивают точную интерпретацию.']
};
let data, selectedId, searchLimit = 30;
const money = v => v == null ? 'Нет данных' : nf.format(v) + ' ₽';
const regionLabel = region => region == null ? 'Внешнее соответствие не установлено' : /^\d+$/.test(String(region)) ? `Код региона: ${String(region).padStart(2,'0')}` : String(region);
const color = p => data.colors[p] || '#798277';
const communityProfile = c => Object.keys(data.profileCommunities).find(p => data.profileCommunities[p] === c);
const communityColor = c => color(communityProfile(c) || 'micro');

async function load() {
  try {
    const response = await fetch('data/research.json');
    if (!response.ok) throw Error('HTTP ' + response.status);
    data = await response.json();
    if (data.schema !== 1 || data.municipalities.length !== 1904) throw Error('Unexpected data contract');
    if (!window.d3?.sankey) throw Error('Visualization library unavailable');
    $('load-status').textContent = '';
    initProfiles(); initHero(); renderFlows(); initSearch(); initMap(); initBoundary(); renderWages(); initReveals();
    window.researchReady = true;
  } catch (error) {
    $('load-status').replaceChildren(document.createTextNode('Не удалось загрузить интерактивные данные. Основной текст доступен ниже. '));
    const button = document.createElement('button'); button.textContent = 'Повторить'; button.onclick = () => location.reload(); $('load-status').append(button);
    console.error('Research presentation:', error);
  }
}

function initProfiles() {
  for (const p of data.profiles) {
    const button = document.createElement('button'); button.dataset.profile = p.technical_label;
    button.style.setProperty('--profile', color(p.technical_label));
    button.innerHTML = `${p.technical_label}<small>${nf.format(p.n)}</small>`;
    button.setAttribute('aria-label', `Профиль ${p.technical_label}, ${p.n} муниципалитетов`);
    button.onclick = () => {
      if (document.startViewTransition && !reduced.matches) document.startViewTransition(() => selectProfile(p.technical_label));
      else selectProfile(p.technical_label);
    };
    $('profile-tabs').append(button);
  }
  selectProfile('D');
}

function selectProfile(letter) {
  const profile = data.profiles.find(p => p.technical_label === letter);
  document.querySelectorAll('[data-profile]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.profile === letter)));
  $('profile-stage').style.setProperty('--profile', color(letter));
  $('profile-letter').textContent = letter; $('profile-name').textContent = profile.display_name;
  $('profile-status').textContent = notes[letter][0]; $('profile-note').textContent = notes[letter][1];
  $('profile-count').textContent = nf.format(profile.n); $('profile-share').textContent = pct(profile.n / data.municipalities.length);
  $('profile-wage').textContent = money(profile.wage_median);
  $('profile-size').replaceChildren();
  for (let i = 0; i < 100; i++) {const mark = document.createElement('i'); if (i >= Math.round(profile.share * 100)) mark.className = 'off'; $('profile-size').append(mark);}
}

function initHero() {
  const canvas = $('constellation'), ctx = canvas.getContext('2d');
  const W = 900, H = 820, center = [470, 395];
  const letters = Object.keys(data.profileCommunities);
  const anchors = letters.map((_, i) => {const angle = -Math.PI / 2 + i * Math.PI * 2 / 7; return [center[0] + 265 * Math.cos(angle), center[1] + 265 * Math.sin(angle)];});
  const hash = n => {const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x);};
  const points = data.municipalities.map(r => {
    const index = letters.indexOf(r.profile), a = anchors[index] || center;
    const angle = hash(r.id + 1) * Math.PI * 2, radius = Math.sqrt(hash(r.id + 4000)) * (r.profile === 'G' ? 87 : 54);
    const hard = [a[0] + Math.cos(angle) * radius, a[1] + Math.sin(angle) * radius];
    const sum = d3.sum(r.affinity);
    const soft = sum > 0 ? [d3.sum(anchors, (p, i) => p[0] * r.affinity[i]) / sum, d3.sum(anchors, (p, i) => p[1] * r.affinity[i]) / sum] : center.slice();
    const spread = 18 + 49 * (1 - r.margin);
    soft[0] += Math.cos(angle) * spread * Math.sqrt(hash(r.id + 50));
    soft[1] += Math.sin(angle) * spread * Math.sqrt(hash(r.id + 50));
    return {hard, soft, phase:hash(r.id + 7) * Math.PI * 2, color:color(r.profile), r, angle};
  });
  let blend = 1, target = 1, paused = reduced.matches, visible = true, raf = 0, lastTime = 0, time = 0;
  const resize = () => {
    const ratio = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.round(canvas.clientWidth * ratio); canvas.height = Math.round(canvas.clientWidth * H / W * ratio);
    ctx.setTransform(canvas.width / W, 0, 0, canvas.height / H, 0, 0); draw();
  };
  function draw() {
    ctx.clearRect(0, 0, W, H);
    ctx.strokeStyle = '#c7d0bf'; ctx.lineWidth = .7;
    [155, 265, 336].forEach(r => {ctx.beginPath();ctx.arc(...center, r, 0, Math.PI * 2);ctx.stroke();});
    ctx.setLineDash([2, 7]); ctx.beginPath();ctx.moveTo(center[0], 38);ctx.lineTo(center[0], 749);ctx.moveTo(110, center[1]);ctx.lineTo(825, center[1]);ctx.stroke();ctx.setLineDash([]);
    for (const p of points) {
      const x = p.hard[0] + (p.soft[0] - p.hard[0]) * blend;
      const y = p.hard[1] + (p.soft[1] - p.hard[1]) * blend;
      const wave = paused || reduced.matches ? 0 : Math.sin(time * .35 + p.phase) * 2.5;
      const phi = Math.atan2(p.hard[1] - center[1], p.hard[0] - center[0]);
      const tail = [center[0] + 318 * Math.cos(phi - .35), center[1] + 318 * Math.sin(phi - .35)];
      ctx.globalAlpha = .09;ctx.strokeStyle = p.color;ctx.lineWidth = .65;ctx.beginPath();ctx.moveTo(...tail);
      ctx.bezierCurveTo(tail[0] - Math.sin(phi) * 130, tail[1] + Math.cos(phi) * 130, x + Math.sin(phi) * 60, y - Math.cos(phi) * 60, x, y + wave);ctx.stroke();
      ctx.globalAlpha = .65;ctx.fillStyle = p.color;ctx.beginPath();ctx.arc(x, y + wave, 1.45 + p.r.margin * .7, 0, Math.PI * 2);ctx.fill();
    }
    ctx.globalAlpha = 1;ctx.fillStyle = '#f2f3eb';ctx.beginPath();ctx.arc(...center, 71, 0, Math.PI * 2);ctx.fill();
    ctx.fillStyle = '#174f38';ctx.textAlign = 'center';ctx.font = '500 36px Manrope';ctx.fillText('1 904',center[0],center[1] + 3);ctx.font = '10px Manrope';ctx.fillStyle = '#627165';ctx.fillText('территории · одна сеть', center[0],center[1] + 25);
  }
  function tick(timestamp) {
    raf = 0;if (!visible || document.hidden) return;
    const elapsed = Math.min((timestamp - lastTime) / 1000 || 0, .05);lastTime = timestamp;
    if (!paused && !reduced.matches) time += elapsed;
    blend += (target - blend) * .075;
    if (Math.abs(target - blend) < .001) blend = target;
    draw();if ((!paused && !reduced.matches) || blend !== target) raf = requestAnimationFrame(tick);
  }
  function start() {if (!raf && visible && !document.hidden) raf = requestAnimationFrame(tick);}
  function setPaused(value) {paused = value;$('motion-toggle').setAttribute('aria-pressed', String(paused));$('motion-toggle').textContent = paused ? 'Продолжить движение' : 'Приостановить движение';draw();start();}
  $('motion-toggle').onclick = () => setPaused(!paused);
  document.querySelectorAll('[data-layout]').forEach(button => button.onclick = () => {
    target = button.dataset.layout === 'soft' ? 1 : 0;
    document.querySelectorAll('[data-layout]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    if (reduced.matches) {blend = target;draw();} else start();
  });
  new IntersectionObserver(entries => {visible = entries[0].isIntersecting; if (visible) start();else {cancelAnimationFrame(raf);raf = 0;}}, {threshold:0}).observe(canvas);
  new ResizeObserver(resize).observe(canvas);
  document.addEventListener('visibilitychange', () => {if (document.hidden) {cancelAnimationFrame(raf);raf = 0;}else start();});
  reduced.addEventListener('change', () => {setPaused(reduced.matches);if (reduced.matches) {blend = target;draw();}});
  document.fonts.ready.then(draw);setPaused(paused);resize();start();
}

function renderFlows() {
  const svg = d3.select('#flow-chart');
  const nodes = new Map();
  data.flows.forEach(f => {nodes.set(`${f.step}-${f.source}`, {id:`${f.step}-${f.source}`, layer:f.step, community:f.source});nodes.set(`${f.step + 1}-${f.target}`, {id:`${f.step + 1}-${f.target}`,layer:f.step + 1,community:f.target});});
  const graph = d3.sankey().nodeId(d => d.id).nodeWidth(5).nodePadding(12).nodeAlign(d3.sankeyLeft).nodeSort((a,b) => a.community - b.community).extent([[32,12],[1120,452]])({nodes:[...nodes.values()], links:data.flows.map(f => ({source:`${f.step}-${f.source}`,target:`${f.step + 1}-${f.target}`,value:f.n}))});
  const defs = svg.append('defs');
  graph.links.forEach((l,i) => {const grad = defs.append('linearGradient').attr('id',`flow-gradient-${i}`).attr('gradientUnits','userSpaceOnUse').attr('x1',l.source.x1).attr('x2',l.target.x0);grad.append('stop').attr('offset','0%').attr('stop-color',communityColor(l.source.community));grad.append('stop').attr('offset','100%').attr('stop-color',communityColor(l.target.community));});
  const links = svg.append('g').selectAll('path').data(graph.links).join('path').attr('class','flow-link').attr('d',d3.sankeyLinkHorizontal()).attr('fill','none').attr('stroke',(_,i) => `url(#flow-gradient-${i})`).attr('stroke-width',d => Math.max(1,d.width)).attr('opacity',.32).attr('tabindex',0).attr('role','button').attr('aria-label',d => describe(d));
  function describe(d) {return `${data.flowMonths[d.source.layer].slice(0,7)} → ${data.flowMonths[d.target.layer].slice(0,7)}: сообщество ${d.source.community} → ${d.target.community}; ${nf.format(d.value)} муниципалитетов`;}
  function highlight(event,d) {links.attr('opacity',link => link === d ? .85 : .12);$('flow-detail').textContent = describe(d);}
  links.on('pointerenter focus click',highlight).on('pointerleave',() => links.attr('opacity',.32)).on('blur',() => links.attr('opacity',.32)).on('keydown',(event,d) => {if (event.key === 'Enter' || event.key === ' ') {event.preventDefault();highlight(event,d);}if(event.key === 'Escape') {links.attr('opacity',.32);$('flow-detail').textContent = 'Все 1 904 муниципалитета на каждом срезе.';}});
  links.append('title').text(describe);
  const group = svg.append('g').selectAll('g').data(graph.nodes).join('g');
  group.append('rect').attr('x',d => d.x0).attr('y',d => d.y0).attr('width',d => d.x1-d.x0).attr('height',d => Math.max(1,d.y1-d.y0)).attr('fill',d => communityColor(d.community));
  group.append('text').attr('x',d => d.layer === 3 ? d.x1 + 8 : d.x0 - 7).attr('y',d => (d.y0 + d.y1)/2 + 3).attr('text-anchor',d => d.layer === 3 ? 'start' : 'end').attr('font-size',9).attr('fill','#435744').text(d => d.layer === 3 ? (communityProfile(d.community) || d.community) : d.community);
}

function initSearch() {
  $('municipality-search').oninput = () => {searchLimit=30;renderSearch();};
  $('profile-filter').onchange = () => {searchLimit=30;renderSearch();};
  $('show-more').onclick = () => {searchLimit += 30;renderSearch();};
  renderSearch();
  const first = data.municipalities.find(r => r.name.includes('Казань')) || data.municipalities.find(r => r.profile === 'F');
  selectMunicipality(first);
}

function renderSearch() {
  const q = $('municipality-search').value.trim().toLocaleLowerCase('ru'), profile = $('profile-filter').value;
  const rows = data.municipalities.filter(r => (!profile || r.profile === profile) && r.name.toLocaleLowerCase('ru').includes(q));
  $('search-count').textContent = rows.length ? `Найдено ${nf.format(rows.length)} · показано ${Math.min(searchLimit,rows.length)}` : 'Совпадений нет. Измените запрос или выберите все профили.';
  $('search-results').replaceChildren();
  rows.slice(0, searchLimit).forEach(r => {
    const b = document.createElement('button');b.style.setProperty('--profile',color(r.profile));b.dataset.municipality = r.id;
    b.innerHTML = `<span>${r.profile === 'micro' ? '·' : r.profile}</span><span>${safe(r.name)}<small>${safe(regionLabel(r.region))}</small></span>`;
    b.setAttribute('aria-pressed',String(r.id === selectedId));b.onclick = () => selectMunicipality(r);$('search-results').append(b);
  });
  $('show-more').hidden = rows.length <= searchLimit;
}

function selectMunicipality(r) {
  selectedId = r.id;
  document.dispatchEvent(new CustomEvent('municipality-selected', {detail:r.id}));
  document.querySelectorAll('[data-municipality]').forEach(b => b.setAttribute('aria-pressed',String(Number(b.dataset.municipality) === r.id)));
  const timeline = r.trajectory.map((c,i) => `<span style="--profile:${communityColor(c)}" title="${data.months[i].slice(0,7)}: сообщество ${c}">${c}</span>`).join('');
  $('municipality-detail').innerHTML = `<div class="detail-top"><span>${safe(regionLabel(r.region))}</span><span>Базовый профиль ${safe(r.profile)}</span></div><h3>${safe(r.name)}</h3><p class="footnote" style="margin-top:12px">${states[r.stability] || safe(r.stability)} · сводный профиль ${safe(r.consensus)}</p><dl class="detail-stats"><div><dt>${r.population == null ? 'Нет данных' : nf.format(r.population)}</dt><dd>население, 2024</dd></div><div><dt>${money(r.wage)}</dt><dd>зарплата работников, 2024</dd></div><div><dt>${r.switches}</dt><dd>смен сообщества за 24 месяца</dd></div></dl><p class="detail-label">24 месяца в сети <span class="footnote">/ исходные ID сообществ</span></p><div class="trajectory" role="img" aria-label="${safe(r.trajectory.map((c,i) => data.months[i].slice(0,7) + ': ' + c).join('; '))}">${timeline}</div><div class="trajectory-years"><span>Январь 2023</span><span>Декабрь 2024</span></div><p class="detail-label">Близость к профилям по сохранённым проверкам</p><div class="affinity">${Object.keys(data.profileCommunities).map((p,i) => `<div style="--profile:${color(p)}"><strong>${p}</strong><span>${pct(r.affinity[i])}</span></div>`).join('')}</div><p class="footnote">Цвета различают сообщества; серый используется для ID вне A–G. Это траектория принадлежности к сообществам, не график роста расходов. Доли близости не являются вероятностями.</p>`;
}

function initMap() {
  const svg=d3.select('#municipal-map'), group=svg.append('g');
  const byId=new Map(data.municipalities.map(r=>[r.id,r]));
  const stateColors={stable_core:'#235d43',expansive_core:'#72966a',transition:'#b99258',unresolved:'#b6b8ae'};
  const communityColors={0:'#78866f',1:color('A'),2:'#4c7872',3:color('B'),4:'#887c9d',5:'#9b8d73',6:'#a1815b',7:color('C'),8:color('D'),9:color('E'),10:color('F'),11:color('G')};
  let paths, layer='profile', month=23, playing=null, loaded=false;
  const zoom=d3.zoom().scaleExtent([1,12]).extent([[0,0],[1200,540]]).translateExtent([[-200,-200],[1400,740]]).filter(event=>event.type!=='wheel'&&(!event.button)).on('zoom',event=>group.attr('transform',event.transform));
  svg.call(zoom).on('dblclick.zoom',null);
  const applyZoom=(factor)=>svg.transition().duration(reduced.matches?0:300).call(zoom.scaleBy,factor);
  $('map-zoom-in').onclick=()=>applyZoom(1.7);$('map-zoom-out').onclick=()=>applyZoom(1/1.7);
  $('map-reset').onclick=()=>svg.transition().duration(reduced.matches?0:300).call(zoom.transform,d3.zoomIdentity);
  function pause(){clearInterval(playing);playing=null;$('map-play').setAttribute('aria-pressed','false');$('map-play').innerHTML='▶ <span>24 месяца</span>';}
  function draw(){
    const label=new Date(data.months[month]+'T12:00:00').toLocaleDateString('ru-RU',{month:'long',year:'numeric'}).replace(' г.','');
    $('map-month-label').textContent=label;$('map-month').value=month;
    $('map-month').disabled=layer!=='profile';$('map-play').disabled=layer!=='profile';
    if(paths)paths.attr('fill',f=>{const r=byId.get(f.properties.id);return layer==='profile'?communityColors[r.trajectory[month]]||'#8b8d87':layer==='stability'?stateColors[r.stability]:d3.interpolateRgb('#d8dfcb','#225e42')(Math.min(r.switches/6,1));});
    let legend;
    if(layer==='profile')legend=Object.keys(communityColors).map(c=>[communityColors[c],month===23&&communityProfile(+c)?`${communityProfile(+c)} · ID ${c}`:`ID ${c}`]);
    else if(layer==='stability')legend=Object.entries(stateColors).map(([s,c])=>[c,states[s]]);
    else legend=[['#d8dfcb','0 смен'],['#82a183','3 смены'],['#225e42','6 и более']];
    $('map-legend').innerHTML=legend.map(([c,text])=>`<span><i style="background:${c}"></i>${text}</span>`).join('');
    if(layer!=='profile')$('map-month-label').textContent=layer==='stability'?'Сводные проверки':'Весь период 2023–2024';
  }
  $('map-month').oninput=()=>{pause();month=Number($('map-month').value);draw();};
  $('map-play').onclick=()=>{if(playing){pause();return;}if(month===23)month=0;draw();$('map-play').setAttribute('aria-pressed','true');$('map-play').innerHTML='Ⅱ <span>Пауза</span>';playing=setInterval(()=>{if(month===23){pause();return;}month++;draw();},1000);};
  document.querySelectorAll('[data-map-layer]').forEach(b=>b.onclick=()=>{pause();layer=b.dataset.mapLayer;document.querySelectorAll('[data-map-layer]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));draw();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
  reduced.addEventListener('change',()=>{if(reduced.matches)pause();});
  const observer=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting&&!loaded){loaded=true;loadGeometry();}if(!e.isIntersecting)pause();}),{rootMargin:'250px'});
  observer.observe(document.querySelector('.map-exhibit'));
  function showSelection(id){if(paths)paths.attr('stroke',f=>f.properties.id===id?'#112e20':'#f2f3eb').attr('stroke-width',f=>f.properties.id===id?2.5:.45).filter(f=>f.properties.id===id).raise();}
  document.addEventListener('municipality-selected',event=>showSelection(event.detail));
  async function loadGeometry(){
    try{
      $('map-status').textContent='Загружаем границы 1 903 муниципалитетов…';
      const response=await fetch('data/municipalities.geojson');if(!response.ok)throw Error('Map response '+response.status);
      const geo=await response.json();
      if(geo.features.length!==1903)throw Error('Map coverage mismatch');
      const projection=d3.geoConicEqualArea().rotate([-100,0]).center([0,63]).parallels([50,70]).fitExtent([[25,25],[1175,515]],geo);
      const path=d3.geoPath(projection);
      svg.append('path').attr('class','map-graticule').attr('d',path(d3.geoGraticule().extent([[18,40],[190,84]]).step([20,10])())).attr('fill','none').attr('stroke','#d3dacb').attr('stroke-width',.4).lower();
      paths=group.selectAll('path').data(geo.features).join('path').attr('class','municipality-path').attr('d',path).attr('stroke','#f2f3eb').attr('stroke-width',.45).attr('vector-effect','non-scaling-stroke').attr('data-map-id',f=>f.properties.id);
      paths.append('title').text(f=>byId.get(f.properties.id).name);
      paths.on('pointerenter',(event,f)=>{const r=byId.get(f.properties.id);$('map-tooltip').hidden=false;$('map-tooltip').textContent=`${r.name} · ${layer==='profile'?'ID '+r.trajectory[month]:layer==='stability'?states[r.stability]:r.switches+' смен'}`;}).on('pointermove',event=>{const bounds=document.querySelector('.map-surface').getBoundingClientRect();$('map-tooltip').style.left=Math.max(8,Math.min(event.clientX-bounds.left+12,bounds.width-270))+'px';$('map-tooltip').style.top=Math.max(8,event.clientY-bounds.top-60)+'px';}).on('pointerleave',()=>{$('map-tooltip').hidden=true;}).on('click',(event,f)=>{selectMunicipality(byId.get(f.properties.id));$('map-status').textContent=byId.get(f.properties.id).name+' · паспорт ниже';$('map-status').hidden=false;});
      $('map-status').hidden=true;draw();showSelection(selectedId);window.researchMapReady=true;
    }catch(error){$('map-status').hidden=false;$('map-status').replaceChildren(document.createTextNode('Карта недоступна. Поиск и паспорта работают ниже. '));const b=document.createElement('button');b.textContent='Повторить';b.onclick=loadGeometry;$('map-status').append(b);console.error('Map:',error);}
  }
  window.loadResearchMap=()=>{if(!loaded){loaded=true;return loadGeometry();}return Promise.resolve();};
  draw();
}

function initBoundary() {
  const svg = d3.select('#boundary-chart');
  svg.append('ellipse').attr('class','outer-boundary').attr('cx',330).attr('cy',195).attr('rx',115).attr('ry',115).attr('fill','#dbe6cb').attr('stroke','#7a886b').attr('stroke-dasharray','4 5');
  svg.append('circle').attr('cx',300).attr('cy',195).attr('r',95).attr('fill','none').attr('stroke','#246c4e').attr('stroke-width',1.5);
  const sample = d3.range(120).map(i => {const a=i*2.3999632297;const radius = Math.sqrt((i+.5)/120)*88;return {x:300+Math.cos(a)*radius,y:195+Math.sin(a)*radius,inside:true};});
  const outside = d3.range(100).map(i => {const a=i*2.3999632297;const radius=125+Math.sqrt(i/100)*70;return {x:325+Math.cos(a)*radius,y:195+Math.sin(a)*radius*.8,inside:false};});
  svg.selectAll('circle.mark').data([...sample,...outside]).join('circle').attr('class','mark').attr('cx',d=>d.x).attr('cy',d=>d.y).attr('r',2.8).attr('fill',d=>d.inside?'#246c4e':'#9d937c').attr('opacity',d=>d.inside?.9:.18);
  svg.append('text').attr('x',300).attr('y',326).attr('text-anchor','middle').attr('font-size',11).attr('fill','#246c4e').text('Исходное ядро');
  const label = svg.append('text').attr('x',330).attr('y',50).attr('text-anchor','middle').attr('font-size',11).attr('fill','#7e7059').text('Граница исходной группы');
  document.querySelectorAll('[data-boundary]').forEach(b => b.onclick = () => {
    const expanded = b.dataset.boundary === 'expanded';
    document.querySelectorAll('[data-boundary]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));
    svg.select('.outer-boundary').interrupt().transition().duration(reduced.matches?0:800).ease(d3.easeCubicInOut).attr('rx',expanded?226:115).attr('ry',expanded?166:115);
    svg.selectAll('circle.mark').interrupt().transition().duration(reduced.matches?0:500).attr('opacity',d=>d.inside?.9:expanded?.65:.18);
    label.text(expanded?'Группа назначения включает соседей':'Граница исходной группы');
  });
}

function renderWages() {
  const svg = d3.select('#wage-chart'), x = d3.scaleLinear().domain([0,180000]).range([38,540]);
  svg.selectAll('.grid').data([0,50000,100000,150000]).join('line').attr('x1',d=>x(d)).attr('x2',d=>x(d)).attr('y1',26).attr('y2',290).attr('stroke','#cbd1c3').attr('stroke-dasharray','2 5');
  svg.selectAll('.tick').data([0,50000,100000,150000]).join('text').attr('x',d=>x(d)).attr('y',316).attr('text-anchor','middle').attr('font-size',10).attr('fill','#627165').text(d=>d===0?'0':`${d/1000} тыс. ₽`);
  data.profiles.forEach((p,i)=>{const y=40+i*39;svg.append('line').attr('x1',x(0)).attr('x2',x(p.wage_median)).attr('y1',y).attr('y2',y).attr('stroke',color(p.technical_label)).attr('stroke-width',1.3);svg.append('circle').attr('cx',x(p.wage_median)).attr('cy',y).attr('r',5).attr('fill',color(p.technical_label));svg.append('text').attr('x',12).attr('y',y+4).attr('font-size',12).attr('fill',color(p.technical_label)).text(p.technical_label);svg.append('text').attr('x',x(p.wage_median)+12).attr('y',y+4).attr('font-size',11).attr('fill','#233b30').text(nf.format(p.wage_median));});
}

function initReveals() {
  if (!reduced.matches) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {if(entry.isIntersecting){entry.target.classList.add('is-visible');observer.unobserve(entry.target);}}), {threshold:.1});
    document.querySelectorAll('.chapter h2,.data-strip,.method-layout,.profile-stage,.evidence-grid,.material-links').forEach(el => {el.classList.add('reveal-ready');observer.observe(el);});
  }
  const navObserver = new IntersectionObserver(entries => {entries.forEach(e => {if(e.isIntersecting){document.querySelectorAll('nav a').forEach(a => {if(a.hash === '#'+e.target.id)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');});}});},{rootMargin:'-20% 0px -55% 0px'});
  document.querySelectorAll('.chapter').forEach(el=>navObserver.observe(el));
}

// Used by the repeatable PDF export. All seven profiles accompany the selected example.
window.prepareResearchPrint = async function() {
  if (!window.researchReady) throw Error('Data not ready');
  await window.loadResearchMap();
  if (!window.researchMapReady) throw Error('Map is not ready for print');
  const repository='https://github.com/resarytrew/cashless-demand-network-russia';
  document.querySelectorAll('.material-links a').forEach(a=>{
    if(a.hasAttribute('download'))a.href=repository+'/tree/main/site';
  });
  $('full-atlas-link').href=repository+'/tree/main/outputs/stability_atlas_v2_2_1';
  document.querySelector('.source-note a').href=repository+'/blob/main/site/data/manifest.json';
  document.querySelectorAll('.reveal-ready').forEach(el=>el.classList.add('is-visible'));
  document.querySelector('.limitations').open=true;
  selectProfile('D');
  if (!document.querySelector('.profile-print-list')) {
    const list=document.createElement('div');list.className='profile-print-list';
    list.innerHTML=data.profiles.map(p=>`<article><b style="color:${color(p.technical_label)}">${p.technical_label}</b><div><h3>${safe(p.display_name)}</h3><p>${safe(notes[p.technical_label][0])}. ${safe(notes[p.technical_label][1])}</p></div><span>${p.n}</span></article>`).join('');$('profile-stage').after(list);
    const address=document.createElement('p');address.className='print-address';address.textContent='Код, конфигурации и полные результаты: https://github.com/resarytrew/cashless-demand-network-russia';document.querySelector('.materials').append(address);
  }
  await document.fonts.ready;
};
load();

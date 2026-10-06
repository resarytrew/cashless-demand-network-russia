'use strict';
const $ = id => document.getElementById(id);
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const nf = new Intl.NumberFormat('ru-RU', {maximumFractionDigits:0});
const pct = n => (n * 100).toLocaleString('ru-RU',{maximumFractionDigits:1}) + '%';
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = value => value == null ? 'Нет данных' : nf.format(value) + ' ₽';
// Display aliases and colours only. Saved numerical data and scientific labels are unchanged.
const profiles = {
 A:{name:'Высокий уровень расходов',short:'Высокие расходы',color:'#bd603e',tint:'#f1e3d6',status:'Выраженное сходство, размытые границы',note:'Высокий уровень расходов объединяет территории, которые могут находиться далеко друг от друга. Значительная часть группы сохраняется при проверках, но её нельзя считать полностью обособленной.',technical:'Перекрывающийся сетевой профиль. Отраслевой или добывающий механизм не установлен.'},
 B:{name:'Внутригородской профиль',short:'Внутригородской',color:'#ba8a2d',tint:'#f2e9d2',status:'Предварительный портрет',note:'Все 98 территорий этого профиля находятся внутри городов федерального значения. Это лишь часть таких территорий. При другом способе анализа их окружение может объединяться с соседним профилем.',technical:'Вложенный федеральный внутригородской подтип. Точная граница B/E изменчива.'},
 C:{name:'Низкие расходы: вывод остаётся открытым',short:'Низкие · вывод открыт',color:'#7e668f',tint:'#eae3ed',status:'Интерпретация ограничена',note:'У этой небольшой группы сравнительно низкий уровень расходов. Однако её сходство существенно зависит от территориального контекста. Оснований считать её самостоятельным устойчивым типом недостаточно.',technical:'C остаётся контекстным и неразрешённым. Сохранение участников при возмущении не устраняет ограничения контекстных проверок.'},
 D:{name:'Умеренно высокий уровень расходов',short:'Умеренно высокие',color:'#315dc5',tint:'#e4eaf6',status:'Сходство сохраняется, состав меняется',note:'Территории заметно похожи между собой. При проверках большинство участников остаются вместе, но к ним могут присоединяться соседи. Поэтому чёткая граница группы менее устойчива, чем её основа.',technical:'Компактное ядро D при изменчивой точной границе. Среднее retention: 0,975817; precision: 0,511661 по 50 возмущениям.'},
 E:{name:'Повышенный уровень расходов',short:'Повышенные · предварительно',color:'#a85473',tint:'#f0e1e7',status:'Предварительный портрет',note:'Исходная группа выглядит похожей по расходам, но часть этого сходства объясняется географией и городским масштабом. Её состав может объединяться с внутригородским профилем.',technical:'Вложенный, контекстно зависимый профиль E. Нельзя интерпретировать как универсальный самостоятельный тип.'},
 F:{name:'Переходный профиль',short:'Переходный',color:'#cf654c',tint:'#f5e3da',status:'Между соседними портретами',note:'Эти территории находятся между несколькими профилями спроса. При изменении способа анализа их отнесение меняется особенно заметно. Здесь важнее видеть близость к соседям, чем закреплять единственную метку.',technical:'Точный состав F чувствителен к k, alpha, алгоритму и возмущениям; значимы границы D/F и F/G. Внешняя интерпретация не повышает статус точной устойчивости.'},
 G:{name:'Широкий профиль с невысокими расходами',short:'Широкий · невысокие расходы',color:'#637d96',tint:'#e2e9ed',status:'Самая многочисленная группа',note:'Около половины исследованных территорий образуют широкий профиль с невысоким уровнем расходов. Он часто сохраняет значительную часть участников, но география и местный контекст объясняют часть сходства.',technical:'Широкий макропрофиль G с оговоркой о фоновом характере. Устойчивость каждого конкретного участника не установлена.'}
};
const stateNames={stable_core:'Сходство устойчиво',expansive_core:'Сходство сохраняется, окружение шире',transition:'Между несколькими профилями',unresolved:'Однозначного вывода нет'};
const extras={0:'#858898',2:'#847566',4:'#9b7c79',5:'#ab9876',6:'#8584a9'};
let data, selectedId, selectedProfile='D', searchLimit=20, geometryPromise;
const color = key => profiles[key]?.color || '#9194a0';
const profileFor = c => Object.keys(data.profileCommunities).find(p=>data.profileCommunities[p]===c);
const communityColor = c => color(profileFor(c)) === '#9194a0' ? extras[c] || '#9194a0' : color(profileFor(c));
const monthLabel = n => new Date(data.months[n]+'T12:00:00').toLocaleDateString('ru-RU',{month:'long',year:'numeric'}).replace(' г.','');
const shortName = name => name.replace(/^городской округ (город )?/i,'').replace(/^муниципальное образование (город )?/i,'').replace(/^муниципальный округ /i,'').replace(/ муниципальный район$/i,' район');
const region = value => value == null ? 'Внешнее соответствие не установлено' : /^\d+$/.test(String(value)) ? 'Код региона: '+String(value).padStart(2,'0') : String(value);
function transition(fn){if(document.startViewTransition&&!reduced.matches)document.startViewTransition(fn);else fn();}

async function load(){
 try{
  const response=await fetch('data/research.json');if(!response.ok)throw Error('Data HTTP '+response.status);
  data=await response.json();if(data.schema!==1||data.municipalities.length!==1904)throw Error('Unexpected data contract');
  if(!window.d3?.sankey)throw Error('Visualization library unavailable');
  $('load-status').textContent='';
  initProfiles();initSearch();initMap();initHero();initChanges();renderFlows();
  await initEvidence();
  await document.fonts.ready;
  if(window.initAtlasMotion)await window.initAtlasMotion();else initReveal();
  initScrollChapters();
  window.ScrollTrigger?.refresh();
  window.researchReady=true;
 }catch(error){$('load-status').replaceChildren(document.createTextNode('Не удалось загрузить атлас. Основные выводы и методология доступны ниже. '));const b=document.createElement('button');b.textContent='Повторить';b.onclick=()=>location.reload();$('load-status').append(b);console.error(error);}
}
function loadGeometry(){
 if(!geometryPromise)geometryPromise=fetch('data/municipalities.geojson').then(r=>{if(!r.ok)throw Error('Map HTTP '+r.status);return r.json();}).then(geo=>{if(geo.features.length!==1903)throw Error('Map coverage mismatch');return geo;}).catch(error=>{geometryPromise=null;throw error;});
 return geometryPromise;
}

function initHero(){
 const canvas=$('hero-canvas'),ctx=canvas.getContext('2d'),W=1000,H=760;
 const letters=Object.keys(profiles),anchors=letters.map((p,i)=>[530+250*Math.cos(i/7*Math.PI*2-.9),370+245*Math.sin(i/7*Math.PI*2-.9)]);
 const hash=n=>{const x=Math.sin(n*127.1+311.7)*43758.5453;return x-Math.floor(x);};
 let paused=reduced.matches,visible=true,frame=0,last=0,time=0,scrollProgress=0,geoPoints=null,mapImage=null;
 const dots=data.municipalities.map(r=>{const a=anchors[letters.indexOf(r.profile)]||[510,360],theta=hash(r.id+1)*Math.PI*2,radius=Math.sqrt(hash(r.id+500))*65;return {r,x:a[0]+Math.cos(theta)*radius,y:a[1]+Math.sin(theta)*radius,theta};});
 function resize(){const dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(canvas.clientWidth*dpr);canvas.height=Math.round(canvas.clientHeight*dpr);const scale=Math.min(canvas.width/W,canvas.height/H);ctx.setTransform(scale,0,0,scale,(canvas.width-W*scale)/2,(canvas.height-H*scale)/2);draw();}
 function draw(){
  ctx.clearRect(0,0,W,H);const mix=geoPoints?(reduced.matches?.35:scrollProgress):1;
  if(mapImage){ctx.globalAlpha=(1-mix)*.5;ctx.drawImage(mapImage,0,0);ctx.globalAlpha=1;}
  for(const p of dots){const base=geoPoints?.get(p.r.id);const start=base||[510,700];const x=start[0]+(p.x-start[0])*mix,y=start[1]+(p.y-start[1])*mix;const wave=paused?0:Math.sin(time*.6+p.theta)*2;
   if(mix>.2&&p.r.id%3===0){ctx.beginPath();ctx.moveTo(x,y);ctx.bezierCurveTo(x+70,y-95,550+p.theta*25,300,560,365);ctx.strokeStyle=color(p.r.profile);ctx.lineWidth=.8;ctx.globalAlpha=.04*mix;ctx.stroke();}
   ctx.globalAlpha=base||!geoPoints?.size? .8 : mix*.8;ctx.fillStyle=color(p.r.profile);ctx.beginPath();ctx.arc(x,y+wave,2.25+(p.r.margin||0)*1.4,0,Math.PI*2);ctx.fill();
  }
  ctx.globalAlpha=1;
 }
 function tick(stamp){frame=0;if(!visible||document.hidden)return;time+=Math.min((stamp-last)/1000||0,.05);last=stamp;draw();if(!paused&&!reduced.matches)frame=requestAnimationFrame(tick);}
 window.setHeroProgress=value=>{scrollProgress=value;canvas.dataset.progress=value.toFixed(3);draw();};
 function start(){if(!frame&&visible&&!document.hidden&&!paused&&!reduced.matches)frame=requestAnimationFrame(tick);}
 function pause(value){paused=value;$('motion-toggle').setAttribute('aria-pressed',String(paused));$('motion-toggle').textContent=paused?'▶':'Ⅱ';$('motion-toggle').setAttribute('aria-label',paused?'Продолжить анимацию':'Приостановить анимацию');draw();start();}
 $('motion-toggle').onclick=()=>pause(!paused);reduced.addEventListener('change',()=>pause(reduced.matches));
 new ResizeObserver(resize).observe(canvas);new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;if(visible)start();else{cancelAnimationFrame(frame);frame=0;}},{threshold:0}).observe(canvas);
 document.addEventListener('visibilitychange',()=>{if(document.hidden){cancelAnimationFrame(frame);frame=0;}else start();});
 loadGeometry().then(geo=>{const projection=d3.geoConicEqualArea().rotate([-100,0]).center([0,63]).parallels([50,70]).fitExtent([[35,110],[975,645]],geo),path=d3.geoPath(projection);geoPoints=new Map(geo.features.map(f=>[f.properties.id,path.centroid(f)]));mapImage=document.createElement('canvas');mapImage.width=W;mapImage.height=H;const mc=mapImage.getContext('2d'),mp=d3.geoPath(projection,mc);mc.fillStyle='#d2c8b8';for(const f of geo.features){mc.beginPath();mp(f);mc.fill();}draw();}).catch(()=>{/* The conceptual points remain available if geometry cannot load. */});
 resize();pause(paused);start();
}

function initProfiles(){
 for(const [p,display] of Object.entries(profiles)){const b=document.createElement('button');b.dataset.profile=p;b.style.setProperty('--profile',display.color);b.textContent=display.short;b.setAttribute('aria-label',display.name);b.onclick=()=>{selectProfile(p);if(!reduced.matches&&window.gsap)gsap.fromTo('#profile-name,#profile-note',{opacity:.4},{opacity:1,duration:.35,ease:'power2.out',overwrite:true});};$('profile-tabs').append(b);}
 selectProfile('A');
}
function selectProfile(p,automatic=false){
 if(!automatic)window.atlasTours?.profiles?.pause();
 selectedProfile=p;const source=data.profiles.find(r=>r.technical_label===p),display=profiles[p];
 document.querySelectorAll('[data-profile]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.profile===p)));
 $('profile-stage').style.setProperty('--profile',display.color);$('profile-stage').style.setProperty('--tint',display.tint);
 $('profile-name').textContent=display.name;$('profile-status').textContent=display.status;$('profile-note').textContent=display.note;
 $('profile-count').textContent=nf.format(source.n);$('profile-share').textContent=pct(source.n/1904);$('profile-wage').textContent=money(source.wage_median);
 $('profile-dotfield').replaceChildren();for(let i=0;i<100;i++){const mark=document.createElement('i');mark.className=i<Math.round(source.n/1904*100)?'on':'';$('profile-dotfield').append(mark);}
 window.atlasTours?.profiles?.refresh();
 $('profile-technical-content').innerHTML=`<p>Код в исследовании: <strong>${p}</strong>. Полное название: ${escapeHTML(source.display_name)}.</p><p>${escapeHTML(display.technical)}</p><p>Состав относится к декабрю 2024 года. Медиана зарплаты: ${money(source.wage_median)}. Это описательное внешнее сопоставление, не причинный вывод.</p><a class="text-link" href="methodology.html#profiles">Методология и статусы профилей ↗</a>`;
}

function initSearch(){
 const field=$('municipality-search');
 field.addEventListener('input',()=>{searchLimit=20;renderSearch();});field.addEventListener('focus',()=>{if(field.value.trim())renderSearch();});
 field.addEventListener('keydown',event=>{if(event.key==='Escape'){$('search-dropdown').hidden=true;}if(event.key==='ArrowDown'){$('search-results').querySelector('button')?.focus();event.preventDefault();}if(event.key==='Enter'){$('search-results').querySelector('button')?.click();}});
 $('clear-search').onclick=()=>{field.value='';$('search-dropdown').hidden=true;$('clear-search').hidden=true;field.focus();};
 $('show-more').onclick=()=>{searchLimit+=20;renderSearch();};
 document.addEventListener('pointerdown',event=>{if(!event.target.closest('.search-box'))$('search-dropdown').hidden=true;});
 for(const query of ['Казань','Владивосток','Абазинский']){const r=data.municipalities.find(r=>r.name.includes(query));if(!r)continue;const b=document.createElement('button');b.textContent=shortName(r.name);b.onclick=()=>{selectMunicipality(r,true);field.value='';$('search-dropdown').hidden=true;};$('quick-places').append(b);}
 selectMunicipality(data.municipalities.find(r=>r.name.includes('Казань'))||data.municipalities[0]);
}
function renderSearch(){
 const query=$('municipality-search').value.trim().toLocaleLowerCase('ru');$('clear-search').hidden=!query;$('search-dropdown').hidden=!query;
 const rows=data.municipalities.filter(r=>r.name.toLocaleLowerCase('ru').includes(query));
 $('search-count').textContent=rows.length?`Найдено: ${nf.format(rows.length)}. Показано: ${Math.min(searchLimit,rows.length)}.`:'Совпадений нет. Попробуйте другое название.';
 $('search-results').replaceChildren();rows.slice(0,searchLimit).forEach(r=>{const b=document.createElement('button');b.dataset.municipality=r.id;b.style.setProperty('--profile',color(r.profile));b.innerHTML=`<span class="result-color" aria-hidden="true"></span><span>${escapeHTML(r.name)}<small>${escapeHTML(region(r.region))}</small></span>`;b.onclick=()=>{selectMunicipality(r,true);$('search-dropdown').hidden=true;$('municipality-search').value=shortName(r.name);};$('search-results').append(b);});$('show-more').hidden=rows.length<=searchLimit;
}
function selectMunicipality(r,focus=false){
 selectedId=r.id;const display=profiles[r.profile];const summary=display?.name||'Малое техническое сообщество';
 $('municipality-detail').style.setProperty('--profile',color(r.profile));
 const change=r.switches===0?'Группа не менялась за все 24 месяца.':`Число смен группы за два года: ${r.switches}.`;
 const topAffinity=Object.entries(profiles).map(([p,display],i)=>({display,value:r.affinity[i]})).sort((a,b)=>b.value-a.value).slice(0,3);
 const proximity=`<div class="place-proximity"><h4>Близость к разным профилям</h4>${topAffinity.map(({display,value})=>`<div><span>${escapeHTML(display.short)}</span><strong>${pct(value)}</strong><i style="--share:${value*100}%;--profile:${display.color}"></i></div>`).join('')}<p>Три наибольшие доли близости по сохранённым проверкам. Это не вероятности принадлежности.</p></div>`;
 const story=r.switches===0?'Эта территория сохраняла сходное окружение на протяжении двух лет.':'Её окружение по структуре и уровню расходов менялось со временем.';
 $('municipality-detail').innerHTML=`<p class="place-tag">${escapeHTML(summary)}</p><h3>${escapeHTML(shortName(r.name))}</h3><p class="place-official">${escapeHTML(r.name)}</p><p class="place-summary">${story}</p><div class="place-stats"><div><strong>${r.population==null?'Нет данных':nf.format(r.population)}</strong><span>население, 2024</span></div><div><strong>${money(r.wage)}</strong><span>зарплата работников, 2024</span></div></div><p class="place-history-title">Как менялось окружение</p><div class="trajectory" role="img" aria-label="${escapeHTML(r.trajectory.map((c,i)=>monthLabel(i)+': группа '+c).join('; '))}">${r.trajectory.map((c,i)=>`<i style="--profile:${communityColor(c)}" title="${monthLabel(i)}; группа ${c}"></i>`).join('')}</div><div class="trajectory-years"><span>Январь 2023</span><span>Декабрь 2024</span></div><p class="place-change-note">${change}</p><button class="place-profile-link">${display?'Изучить этот профиль ↗':'О технических случаях ↗'}</button>${proximity}<details class="technical-detail"><summary>Данные и исследовательские детали <span>+</span></summary><div><p>${escapeHTML(region(r.region))}. Исходный профиль: ${escapeHTML(r.profile)}; сводный: ${escapeHTML(r.consensus)}.</p><p>${escapeHTML(stateNames[r.stability]||r.stability)}. Численность занятых: ${r.employment==null?'нет данных':nf.format(r.employment)}.</p><p>Доли близости по сохранённым проверкам:</p><div class="affinity">${Object.keys(profiles).map((p,i)=>`<div style="--profile:${color(p)}"><strong>${p}</strong><span>${pct(r.affinity[i])}</span></div>`).join('')}</div><p>Доли близости не являются вероятностями. Зарплата работников не измеряет доход всех жителей. Изменение группы не равно росту или падению расходов.</p><p class="technical-trajectory">Сохранённые ID сообществ: ${r.trajectory.join(', ')}.</p><a href="methodology.html" class="text-link">Методология ↗</a></div></details>`;
 $('municipality-detail').querySelector('.place-profile-link').onclick=()=>{if(display){selectProfile(r.profile);window.atlasNavigate?window.atlasNavigate($('profiles')):$('profiles').scrollIntoView({behavior:'instant'});}else location.href='methodology.html#profiles';};
 document.dispatchEvent(new CustomEvent('territory-selected',{detail:{id:r.id,focus}}));
 if(focus&&innerWidth<768)(window.atlasNavigate?window.atlasNavigate($('municipality-detail')):$('municipality-detail').scrollIntoView({behavior:'instant',block:'nearest'}));
}

function initMap(){
 const svg=d3.select('#municipal-map'),group=svg.append('g').attr('class','map-geography'),byId=new Map(data.municipalities.map(r=>[r.id,r]));
 let paths,geoPath,layer='profile',month=23,timer=null,loadedPromise;
 const stateColors={stable_core:'#315dc5',expansive_core:'#8da4d5',transition:'#ce704f',unresolved:'#aaa6ad'};
 const zoom=d3.zoom().scaleExtent([1,14]).extent([[0,0],[1100,590]]).translateExtent([[-200,-200],[1300,790]]).filter(event=>event.type!=='wheel'&&!event.button).on('zoom',event=>group.attr('transform',event.transform));svg.call(zoom).on('dblclick.zoom',null);
 const zoomTo=factor=>svg.transition().duration(reduced.matches?0:350).call(zoom.scaleBy,factor);
 $('map-zoom-in').onclick=()=>zoomTo(1.65);$('map-zoom-out').onclick=()=>zoomTo(1/1.65);$('map-reset').onclick=()=>svg.transition().duration(reduced.matches?0:350).call(zoom.transform,d3.zoomIdentity);
 function pause(){clearInterval(timer);timer=null;$('map-play').textContent='▶';$('map-play').setAttribute('aria-pressed','false');$('map-play').setAttribute('aria-label','Воспроизвести изменения за 24 месяца');}
 function draw(){
  $('map-month-label').textContent=layer==='profile'?monthLabel(month):layer==='switches'?'Два года целиком':'Сводные проверки';$('map-month').value=month;$('map-month').disabled=layer!=='profile';$('map-play').disabled=layer!=='profile';
  paths?.attr('fill',f=>{const r=byId.get(f.properties.id);return layer==='profile'?communityColor(r.trajectory[month]):layer==='stability'?stateColors[r.stability]:d3.interpolateRgb('#e0d8ca','#bb513b')(Math.min(r.switches/6,1));});
  let legend;if(layer==='profile'){
   const communities=[...new Set(data.municipalities.map(r=>r.trajectory[month]))].sort((a,b)=>a-b);
   legend=communities.map(c=>[communityColor(c),month===23?(profiles[profileFor(c)]?.short||'Малая группа'):'Группа '+c]);
   if(month===23){const seen=new Set();legend=legend.filter(row=>{if(seen.has(row[1]))return false;seen.add(row[1]);return true;});}
  }else if(layer==='stability')legend=Object.entries(stateColors).map(([s,c])=>[c,stateNames[s]]);else legend=[['#e0d8ca','Без смены группы'],['#ce9580','Три смены'],['#bb513b','Шесть и более']];
  $('map-legend').innerHTML=legend.map(([c,t])=>`<span><i style="background:${c}"></i>${escapeHTML(t)}</span>`).join('');
 }
 $('map-month').oninput=()=>{pause();month=+$('map-month').value;draw();};
 $('map-play').onclick=()=>{if(timer){pause();return;}if(month===23)month=0;draw();$('map-play').textContent='Ⅱ';$('map-play').setAttribute('aria-pressed','true');$('map-play').setAttribute('aria-label','Приостановить изменения');timer=setInterval(()=>{if(month===23){pause();return;}month++;draw();},1100);};
 function selectLayer(next,automatic=false){
  if(!automatic)window.atlasTours?.map?.pause();pause();layer=next;
  document.querySelectorAll('[data-map-layer]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.mapLayer===layer)));draw();
  if(automatic&&!reduced.matches&&window.gsap)gsap.fromTo('#municipal-map',{opacity:.6},{opacity:1,duration:.85,ease:'power2.out',overwrite:true});
  window.atlasTours?.map?.refresh();
 }
 window.atlasMap={getLayer:()=>layer,selectLayer};
 document.querySelectorAll('[data-map-layer]').forEach(b=>b.onclick=()=>selectLayer(b.dataset.mapLayer));
 function select(id,focus){if(!paths)return;paths.attr('stroke',f=>f.properties.id===id?'#202532':'#f7f4ee').attr('stroke-width',f=>f.properties.id===id?2.3:.45).filter(f=>f.properties.id===id).raise();if(focus){const f=paths.data().find(f=>f.properties.id===id);if(f){const [[x0,y0],[x1,y1]]=geoPath.bounds(f),k=Math.max(1.3,Math.min(6,Math.min(800/(x1-x0),430/(y1-y0))));svg.transition().duration(reduced.matches?0:800).call(zoom.transform,d3.zoomIdentity.translate(550-k*(x0+x1)/2,295-k*(y0+y1)/2).scale(k));}else{$('map-status').hidden=false;$('map-status').textContent='Для этой территории географическое соответствие не установлено. Данные показаны в её портрете.';}}}
 document.addEventListener('territory-selected',event=>select(event.detail.id,event.detail.focus));
 async function render(){
  try{
   const geo=await loadGeometry();const projection=d3.geoConicEqualArea().rotate([-100,0]).center([0,63]).parallels([50,70]).fitExtent([[20,20],[1080,550]],geo);geoPath=d3.geoPath(projection);
   paths=group.selectAll('path').data(geo.features).join('path').attr('class','municipality-path').attr('d',geoPath).attr('data-map-id',f=>f.properties.id).attr('vector-effect','non-scaling-stroke');
   paths.append('title').text(f=>byId.get(f.properties.id).name);
   paths.on('pointerenter',(event,f)=>{const r=byId.get(f.properties.id);$('map-tooltip').hidden=false;$('map-tooltip').textContent=shortName(r.name)+(month===23&&layer==='profile'?' · '+(profiles[r.profile]?.short||'Малая группа'):'');}).on('pointermove',event=>{const b=document.querySelector('.map-surface').getBoundingClientRect();$('map-tooltip').style.left=Math.max(8,Math.min(event.clientX-b.left+12,b.width-250))+'px';$('map-tooltip').style.top=Math.max(8,event.clientY-b.top-65)+'px';}).on('pointerleave',()=>{$('map-tooltip').hidden=true;}).on('click',(event,f)=>{selectMunicipality(byId.get(f.properties.id));$('map-tooltip').hidden=true;if(innerWidth<768)(window.atlasNavigate?window.atlasNavigate($('municipality-detail')):$('municipality-detail').scrollIntoView({behavior:'instant',block:'nearest'}));});
   $('map-status').hidden=true;draw();select(selectedId,false);window.researchMapReady=true;window.atlasTours?.map?.refresh();
  }catch(error){$('map-status').hidden=false;$('map-status').replaceChildren(document.createTextNode('Карта недоступна. Поиск и портреты работают. '));const b=document.createElement('button');b.textContent='Повторить';b.onclick=()=>{loadedPromise=render();};$('map-status').append(b);console.error(error);}
 }
 loadedPromise=render();window.loadResearchMap=()=>loadedPromise;
 new IntersectionObserver(es=>{if(!es[0].isIntersecting)pause();},{threshold:0}).observe($('municipal-map'));document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});reduced.addEventListener('change',()=>{if(reduced.matches)pause();});draw();
}

function initChanges(){
 const canvas=$('change-canvas'),ctx=canvas.getContext('2d'),W=800,H=740;let scene=0,active=0,raf=0,view=false;
 const rows=[...data.municipalities].sort((a,b)=>a.switches-b.switches||a.id-b.id);
 function resize(){const dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(canvas.clientWidth*dpr);canvas.height=Math.round(canvas.clientWidth*H/W*dpr);ctx.setTransform(canvas.width/W,0,0,canvas.height/H,0,0);draw();}
 function draw(){ctx.clearRect(0,0,W,H);const columns=44,gap=16;const n=scene===0?476:scene===1?1624:280;const accent=[profiles.F.color,profiles.D.color,profiles.C.color][scene];
  rows.forEach((r,i)=>{const col=i%columns,row=Math.floor(i/columns);const selected=scene===0?r.switches===0:scene===1?r.switches<=2:r.switches>2;const a=selected?(reduced.matches?1:Math.min(1,Math.max(0,active*1.3-i/rows.length*.3))):.65;ctx.globalAlpha=a;ctx.fillStyle=selected?accent:'#d6d1c8';ctx.beginPath();ctx.arc(42+col*gap,25+row*gap,selected?4.8:3.4,0,Math.PI*2);ctx.fill();});ctx.globalAlpha=1;
  $('change-caption').textContent=`${nf.format(n)} ${scene===0?'территорий не меняли группу за весь период.':scene===1?'территории сменили группу не более двух раз.':'территорий сменили группу три раза или больше.'}`;
 }
 function animate(){raf=0;active=Math.min(1,active+.025);draw();if(active<1&&view)raf=requestAnimationFrame(animate);}
 function select(next){if(scene===next&&active===1)return;scene=next;active=reduced.matches?1:0;cancelAnimationFrame(raf);document.querySelectorAll('.story-progress i').forEach((el,i)=>el.classList.toggle('active',i===scene));draw();if(!reduced.matches)raf=requestAnimationFrame(animate);canvas.dataset.scene=scene;}
 const observer=new IntersectionObserver(entries=>{const entering=entries.filter(e=>e.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio);if(entering.length)select(+entering[0].target.dataset.scene);},{rootMargin:'-30% 0px -25% 0px',threshold:[0,.25,.5,.75]});document.querySelectorAll('.story-step').forEach(el=>observer.observe(el));
 new IntersectionObserver(es=>{view=es[0].isIntersecting;if(view&&active<1&&!raf)raf=requestAnimationFrame(animate);else if(!view){cancelAnimationFrame(raf);raf=0;}},{threshold:0}).observe(canvas);
 new ResizeObserver(resize).observe(canvas);reduced.addEventListener('change',()=>{if(reduced.matches){cancelAnimationFrame(raf);raf=0;active=1;draw();}});resize();active=1;draw();window.setPrintScene=()=>{scene=1;active=1;draw();};
}

function renderFlows(){
 const svg=d3.select('#flow-chart'),nodes=new Map();data.flows.forEach(f=>{nodes.set(`${f.step}-${f.source}`,{id:`${f.step}-${f.source}`,layer:f.step,community:f.source});nodes.set(`${f.step+1}-${f.target}`,{id:`${f.step+1}-${f.target}`,layer:f.step+1,community:f.target});});
 const graph=d3.sankey().nodeId(d=>d.id).nodeWidth(7).nodePadding(12).nodeAlign(d3.sankeyLeft).nodeSort((a,b)=>a.community-b.community).extent([[10,14],[1040,502]])({nodes:[...nodes.values()],links:data.flows.map(f=>({source:`${f.step}-${f.source}`,target:`${f.step+1}-${f.target}`,value:f.n}))});
 const defs=svg.append('defs');graph.links.forEach((l,i)=>{const g=defs.append('linearGradient').attr('id',`flow-${i}`).attr('gradientUnits','userSpaceOnUse').attr('x1',l.source.x1).attr('x2',l.target.x0);g.append('stop').attr('offset','0%').attr('stop-color',communityColor(l.source.community));g.append('stop').attr('offset','100%').attr('stop-color',communityColor(l.target.community));});
 const describe=d=>`${data.flowMonths[d.source.layer].slice(0,7)} → ${data.flowMonths[d.target.layer].slice(0,7)}: ${nf.format(d.value)} территорий ${d.source.community===d.target.community?'сохранили группу':'перешли в другую группу'}.`;
 const links=svg.append('g').selectAll('path').data(graph.links).join('path').attr('class','flow-link').attr('d',d3.sankeyLinkHorizontal()).attr('fill','none').attr('stroke',(_,i)=>`url(#flow-${i})`).attr('stroke-width',d=>Math.max(1,d.width)).attr('opacity',.5).attr('tabindex',0).attr('role','button').attr('aria-label',describe);
 function highlight(e,d){links.attr('opacity',l=>l===d ? .9 : .12);$('flow-detail').textContent=describe(d);}
 links.on('pointerenter focus click',highlight).on('pointerleave blur',()=>links.attr('opacity',.5)).on('keydown',(e,d)=>{if(['Enter',' '].includes(e.key)){e.preventDefault();highlight(e,d);}if(e.key==='Escape')links.attr('opacity',.5);});links.append('title').text(describe);
 svg.append('g').selectAll('rect').data(graph.nodes).join('rect').attr('x',d=>d.x0).attr('y',d=>d.y0).attr('width',7).attr('height',d=>Math.max(1,d.y1-d.y0)).attr('fill',d=>communityColor(d.community));
 svg.append('g').selectAll('text').data(graph.nodes.filter(d=>d.layer===3&&d.value>10)).join('text').attr('x',1053).attr('y',d=>(d.y0+d.y1)/2+3).attr('font-size',10).attr('fill',d=>communityColor(d.community)).text(d=>profiles[profileFor(d.community)]?.short||'Малая группа');
}
async function initEvidence(){
 try{
  const response=await fetch('data/evidence.json');if(!response.ok)throw Error('Evidence HTTP '+response.status);
  const evidence=await response.json();if(evidence.schema!==1||!evidence.regional?.grouped_cv?.length)throw Error('Unexpected evidence contract');
  const variables={wage:{title:'Зарплата работников: медиана по территориям, ₽',unit:'₽',note:'Распределение муниципальных показателей зарплаты работников за 2024 год. Это не доход всех жителей.'},population:{title:'Медианная численность населения, человек',unit:'чел.',note:'Население на 1 января 2024 года.'},employment_total:{title:'Медианная численность занятых, человек',unit:'чел.',note:'Численность занятых по обследуемым видам деятельности, 2024 год.'}};
  const format=(value,variable)=>nf.format(+value)+(variable==='wage'?' ₽':'');
  let activeIndicator='wage';
  function compare(variable,automatic=false){
   if(!automatic)window.atlasTours?.indicators?.pause();activeIndicator=variable;
   const positions=[...document.querySelectorAll('.external-row-track')].map(el=>({left:el.querySelector('i').style.left,width:el.querySelector('i').style.width,dot:el.querySelector('b').style.left}));
   document.querySelectorAll('[data-indicator]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.indicator===variable)));
   $('external-chart-title').textContent=variables[variable].title;
   const rows=evidence.profile_statistics.filter(r=>r.variable===variable),maximum=Math.max(...rows.map(r=>+r.q75));
   $('external-axis').innerHTML=`<span>Общая шкала</span><span><i>0</i><i>${format(maximum,variable)}</i></span><span></span>`;
   $('external-bars').innerHTML=rows.map(r=>`<button class="external-row" data-external-profile="${r.profile}" style="--profile:${color(r.profile)}" aria-label="${escapeHTML(profiles[r.profile].name)}: медиана ${format(r.median,variable)}; открыть профиль"><span class="external-row-name">${escapeHTML(profiles[r.profile].short)}<small>${r.n} территорий с данными</small></span><span class="external-row-track" aria-hidden="true"><i style="left:${+r.q25/maximum*100}%;width:${(+r.q75-r.q25)/maximum*100}%"></i><b style="left:${+r.median/maximum*100}%"></b></span><strong>${format(r.median,variable)}</strong></button>`).join('');
   $('external-bars').querySelectorAll('button').forEach(b=>b.onclick=()=>{selectProfile(b.dataset.externalProfile);window.atlasNavigate?window.atlasNavigate($('profiles')):$('profiles').scrollIntoView();});
   $('external-chart-caption').textContent='Точка — медиана. Полоса — середина распределения: от 25-го до 75-го процентиля. '+variables[variable].note+' Нажмите строку, чтобы изучить профиль.';
   $('dfg-reading').innerHTML=['G','F','D'].map(p=>{const r=rows.find(r=>r.profile===p);return `<div style="--profile:${color(p)}"><span>${escapeHTML(profiles[p].short)}</span><strong>${format(r.median,variable)}</strong></div>`;}).join('');
   if(automatic&&!reduced.matches&&window.gsap){
    document.querySelectorAll('.external-row-track').forEach((el,i)=>{if(!positions[i])return;gsap.from(el.querySelector('i'),{left:positions[i].left,width:positions[i].width,duration:.85,ease:'power3.inOut'});gsap.from(el.querySelector('b'),{left:positions[i].dot,duration:.85,ease:'power3.inOut'});});
    gsap.from('.external-row > strong,.dfg-reading strong',{opacity:.2,y:8,stagger:.025,duration:.6,ease:'power2.out'});
   }
   window.atlasTours?.indicators?.refresh();
  }
  window.atlasEvidence={getIndicator:()=>activeIndicator,showIndicator:compare};
  $('wage-effect').textContent=data.summary.effect_sizes.wage.toLocaleString('ru-RU',{minimumFractionDigits:3,maximumFractionDigits:3});
  function prediction(mode){
   const regional=mode==='regional';const model=(regional?evidence.regional.grouped_cv:evidence.prediction.stratified_cv).find(r=>r.model==='random_forest');
   const baseline=regional?evidence.regional.region_only[0].macro_f1:evidence.prediction.permutation_mean.macro_f1;
   const formatScore=n=>(+n).toLocaleString('ru-RU',{minimumFractionDigits:3,maximumFractionDigits:3});
   const rows=[{name:'По независимой статистике',score:model.macro_f1,color:'#315dc5'},{name:regional?'Самый частый профиль':'Перемешанные метки',score:baseline,color:'#92949c'}];
   $('prediction-bars').innerHTML=rows.map(r=>`<div class="prediction-row"><span>${r.name}</span><strong>${formatScore(r.score)}</strong><i style="--share:${r.score*100}%;--profile:${r.color}"></i></div>`).join('');
   $('prediction-explanation').textContent=regional?'Все территории проверяемого региона исключены из обучения. Ориентир — наиболее частый профиль в обучающей части. Результат по регионам неоднороден.':'Территории одного региона могут оказаться и в обучении, и в проверке. Ориентир — средний результат при случайной перестановке меток профилей.';
   document.querySelectorAll('[data-validation]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.validation===mode)));window.ScrollTrigger?.refresh();
  }
  document.querySelectorAll('[data-indicator]').forEach(b=>b.onclick=()=>compare(b.dataset.indicator));
  document.querySelectorAll('[data-validation]').forEach(b=>b.onclick=()=>prediction(b.dataset.validation));
  compare('wage');prediction('regional');$('evidence-status').textContent='';window.researchEvidenceReady=true;
 }catch(error){$('evidence-status').textContent='Не удалось загрузить сравнения. Числа и источники доступны в файле данных ниже.';console.error(error);}
}

function initScrollChapters(){
 if(!window.createAtlasScrollChapter)return;
 const tours=window.atlasTours={};
 $('profile-stage').prepend($('profile-tour-controls'));
 document.querySelector('.external-plot').prepend($('indicator-tour-controls'));
 document.querySelector('.map-column').prepend($('map-tour-controls'));
 const names=Object.keys(profiles);
 tours.profiles=createAtlasScrollChapter({id:'profiles',stage:document.querySelector('.profiles-workspace'),mount:$('profile-tour-controls'),count:names.length,getIndex:()=>names.indexOf(selectedProfile),select:index=>{
  selectProfile(names[index],true);
  gsap.fromTo('#profile-name,#profile-note,.profile-metrics,#profile-dotfield',{opacity:.45,y:10},{opacity:1,y:0,duration:.35,clearProps:'opacity,transform',overwrite:true});
 }});
 if(window.atlasEvidence){
  const indicators=['wage','population','employment_total'];
  tours.indicators=createAtlasScrollChapter({id:'indicators',stage:document.querySelector('.external-plot'),mount:$('indicator-tour-controls'),count:3,getIndex:()=>indicators.indexOf(atlasEvidence.getIndicator()),select:index=>atlasEvidence.showIndicator(indicators[index],true)});
 }
 const layers=['profile','switches','stability'];
 tours.map=createAtlasScrollChapter({id:'map',stage:document.querySelector('.map-column'),mount:$('map-tour-controls'),count:3,getIndex:()=>layers.indexOf(atlasMap.getLayer()),ready:()=>!!window.researchMapReady,select:index=>atlasMap.selectLayer(layers[index],true)});
}

function initReveal(){
 const targets=document.querySelectorAll('.section-heading h2,.flow-heading h2,.profile-stage,.about-section h2,.material-main');
 if(!reduced.matches)targets.forEach(el=>el.classList.add('reveal'));
 const observer=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('is-visible');observer.unobserve(e.target);}}),{threshold:.12});targets.forEach(el=>observer.observe(el));observer.observe($('discovery'));
 const nav=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting)document.querySelectorAll('nav a').forEach(a=>{if(a.hash==='#'+e.target.id)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');});}),{rootMargin:'-15% 0px -60% 0px'});['atlas','profiles','changes'].forEach(id=>nav.observe($(id)));
}

window.prepareResearchPrint=async()=>{
 if(!window.researchReady)throw Error('Data not ready');window.stopAtlasMotion?.();Object.values(window.atlasTours||{}).forEach(t=>t.destroy?.());if(!window.researchEvidenceReady)throw Error('External evidence not ready');await window.loadResearchMap();if(!window.researchMapReady)throw Error('Map not ready');
 document.querySelectorAll('.reveal').forEach(el=>el.classList.add('is-visible'));window.setPrintScene();
 document.querySelector('.transfer-chart .technical-detail').open=true;
 if(!document.querySelector('.profile-print-list')){const list=document.createElement('div');list.className='profile-print-list';list.innerHTML=data.profiles.map(p=>`<article style="--profile:${color(p.technical_label)}"><i></i><div><h3>${escapeHTML(profiles[p.technical_label].name)}</h3><p>${escapeHTML(profiles[p.technical_label].note)}</p><small>Код в исследовании: ${p.technical_label}.</small></div><strong>${p.n}</strong></article>`).join('');document.querySelector('.profiles-workspace').append(list);}
 $('print-appendix').innerHTML=`<h2>Методология и ограничения</h2><p>Строгая панель: 1 904 муниципалитета, январь 2023 — декабрь 2024. Шесть компонент расходов, включая технический остаток «Прочее». Композиция: CLR / геометрия Эйчисона. Уровень: robust-z от log(Total). Веса блоков: 70% и 30%.</p><p>Взвешенная сеть взаимных ближайших соседей, k = 20. Временная связь ω = 2. Louvain, resolution = 0,5, seed = 0. Это референсная спецификация, а не универсальный оптимум. Для статического графа декабря предусмотрено присоединение изолированных узлов; для месячных временных слоёв — нет.</p><p>Границы групп зависят от параметров и алгоритма. C остаётся контекстным и неразрешённым; F — переходным; B/E могут объединяться. Сохранение ядра не означает неизменности границы. Доли близости не являются вероятностями.</p><p>Внешнее сопоставление: 1 903 подтверждённых соответствия, данные о зарплате и занятости — для 1 890 территорий. Эти показатели не участвовали в построении или настройке групп. Проверки исследовательские; причинная связь не установлена. Знаменатель Total и аддитивность категорий остаются ограничениями.</p><p>Срезы потоков соответствуют точным сохранённым меткам на конец июня и декабря. На каждом срезе — 1 904 территории. Геометрия 1 903 территорий упрощена только для отображения. Расчёты и научные статусы при переработке атласа не изменялись.</p><p class="print-address">Полные конфигурации, данные и проверки: https://github.com/resarytrew/cashless-demand-network-russia</p>`;
 document.querySelectorAll('a[href="methodology.html"]').forEach(a=>a.href='https://github.com/resarytrew/cashless-demand-network-russia/tree/main/site');await document.fonts.ready;
};
load();

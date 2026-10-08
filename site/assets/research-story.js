'use strict';

// Presentation of saved profile-card results. No model parameters are changed.
window.initResearchStory = function(cards, openProfile) {
  const byProfile=new Map(cards.map(card=>[card.profile,card]));
  const fmt=new Intl.NumberFormat('ru-RU',{maximumFractionDigits:0});
  const decimal=new Intl.NumberFormat('ru-RU',{maximumFractionDigits:1});
  const percent=value=>decimal.format(value*100)+'%';
  const escape=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const motion=()=>!matchMedia('(prefers-reduced-motion: reduce)').matches;
  const categories=['Food','Health','Catering','Marketplace','Transport'];
  const colors={A:'#d78a67',B:'#d7b76d',C:'#baa4ce',D:'#87a5f1',E:'#d996b2',F:'#ed9a7b',G:'#9eb6c8'};
  const status={SUPPORTED:'Поддержан',PRELIMINARY:'Предварительный',TRANSITION:'Переходный',UNRESOLVED:'Не разрешён'};
  const share=(card,key)=>card.demand.categories.find(item=>item.category===key)?.profile_median_share;
  const animate=target=>{if(window.gsap&&motion())gsap.fromTo(target,{opacity:.35,y:12},{opacity:1,y:0,duration:.45,overwrite:true,ease:'power2.out'});};
  const refresh=()=>requestAnimationFrame(()=>window.ScrollTrigger?.refresh());

  const mount=document.getElementById('comparison-desk');
  mount.innerHTML=`<div class="desk-toolbar"><span class="desk-caption">Выберите пару</span><div class="desk-pairs" role="group" aria-label="Сопоставимые пары">${[['E','Москва'],['G','Два района'],['D','Два города']].map(([key,label],index)=>`<button type="button" data-desk-pair="${key}" aria-pressed="${index===0}">${label}</button>`).join('')}</div><a href="data/profile_cards.json">Исходные значения ↗</a></div><div class="desk-headings" id="desk-headings"></div><div class="desk-metrics" id="desk-metrics"></div><div class="desk-insight" aria-live="polite" id="desk-insight"></div><p class="desk-footnote">Для каждой строки используется одна линейная шкала от нуля. Расходы — декабрь 2024 года; внешние показатели — 2024 год. Пары подобраны по внешним характеристикам, а не по сходству расходов.</p>`;
  const metrics=[['population','Население','чел.'],['wage','Зарплата работников','₽'],['employment_total','Работники организаций','чел.'],['total','Общий показатель расходов','₽'],['marketplace_share','Доля маркетплейсов','%']];
  function drawPair(key){
    const card=byProfile.get(key),pair=card.counterexample;
    document.querySelectorAll('[data-desk-pair]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.deskPair===key)));
    document.getElementById('desk-headings').innerHTML=`<div><span>Сопоставление территорий</span><p>Сходство масштаба.<br>Различие спроса.</p></div>${[['anchor',key],['comparison',pair.comparison_profile]].map(([side,profile])=>`<button type="button" data-desk-profile="${profile}" style="--desk-color:${colors[profile]}"><span>Профиль ${profile} · ${status[byProfile.get(profile).status]}</span><strong>${escape(pair[side+'_display_name'])}</strong><small>Открыть портрет профиля ↗</small></button>`).join('')}`;
    document.getElementById('desk-metrics').innerHTML=metrics.map(([metric,label,unit],index)=>{
      const values=[pair['anchor_'+metric],pair['comparison_'+metric]];
      const maximum=Math.max(...values.filter(Number.isFinite),1e-9);
      return `${index===3?'<p class="desk-divider">Теперь сравним расходы</p>':''}<div class="desk-row"><span>${label}</span>${values.map((value,i)=>`<div class="desk-value" style="--desk-color:${colors[i?pair.comparison_profile:key]}"><strong>${Number.isFinite(value)?unit==='%'?percent(value):fmt.format(value)+' '+unit:'Нет данных'}</strong><div class="desk-ruler" aria-hidden="true">${Number.isFinite(value)?`<i style="--position:${value/maximum*94}%"></i>`:''}</div></div>`).join('')}</div>`;
    }).join('');
    const total=pair.comparison_total/pair.anchor_total-1;
    const market=(pair.comparison_marketplace_share-pair.anchor_marketplace_share)*100;
    const quality=pair.match_quality==='strong'?'Близкая по внешним характеристикам пара.':'Сопоставимость ограничена: масштаб территорий заметно различается.';
    document.getElementById('desk-insight').innerHTML=`<div><strong>${total>=0?'+':'−'}${percent(Math.abs(total))}</strong><span>общий показатель расходов</span></div><div><strong>${market>=0?'+':'−'}${decimal.format(Math.abs(market))} <small>п.п.</small></strong><span>доля маркетплейсов</span></div><p>${quality} Изменения показаны для правой территории относительно левой. Этот пример выявляет различие, но не устанавливает его причину.</p>`;
    mount.querySelectorAll('[data-desk-profile]').forEach(button=>button.onclick=()=>openProfile(button.dataset.deskProfile));
    animate('#desk-headings,#desk-metrics,#desk-insight');refresh();
  }
  mount.querySelectorAll('[data-desk-pair]').forEach(button=>button.onclick=()=>drawPair(button.dataset.deskPair));
  drawPair('E');

  const spectrum=document.getElementById('demand-spectrum');
  spectrum.innerHTML=`<div class="spectrum-toolbar"><div role="group" aria-label="Состав спектра"><button type="button" data-spectrum-mode="sequence" aria-pressed="true">Пять профилей</button><button type="button" data-spectrum-mode="all" aria-pressed="false">Добавить A и C</button></div><span>Медианы · декабрь 2024</span></div><div class="spectrum-labels"><span>Профиль</span><span>Общий показатель расходов, ₽</span><span>Доля общепита, %</span></div><div id="spectrum-rows"></div><p id="spectrum-reading" class="spectrum-reading" aria-live="polite"></p><div class="signature-layout"><div class="signature-intro"><span>Портрет выбранной группы</span><h3 id="signature-title"></h3><p id="signature-status"></p><button type="button" id="signature-open">Открыть полную карточку ↗</button></div><div><div class="signature-legend"><span>● Профиль</span><span>│ Медиана выборки</span></div><div id="signature-bars"></div><p class="desk-footnote">Медианы отдельных долей не образуют полный бюджет. Технический остаток «Прочее» не интерпретируется.</p></div></div>`;
  let chosen='G',all=false;
  const maxTotal=Math.max(...cards.map(card=>card.demand.total_median));
  const maxCatering=Math.max(...cards.map(card=>share(card,'Catering')));
  function select(key){
    chosen=key;const card=byProfile.get(key);
    spectrum.querySelectorAll('[data-spectrum-profile]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.spectrumProfile===key)));
    document.getElementById('signature-title').textContent=key+' · '+card.display_name;
    document.getElementById('signature-status').textContent=status[card.status]+' · '+fmt.format(card.n)+' территорий';
    document.getElementById('signature-open').onclick=()=>openProfile(key);
    document.getElementById('signature-bars').innerHTML=categories.map(category=>{
      const item=card.demand.categories.find(row=>row.category===category);
      const maximum=Math.max(...cards.map(c=>share(c,category)),item.overall_median_share)*1.1;
      return `<div class="signature-row"><span>${escape(item.label)}</span><div class="signature-track" style="--desk-color:${colors[key]}"><i class="signature-median" style="left:${item.overall_median_share/maximum*100}%" title="Медиана выборки: ${percent(item.overall_median_share)}"></i><i class="signature-point" style="left:${item.profile_median_share/maximum*100}%"></i></div><strong>${percent(item.profile_median_share)}<small>в выборке ${percent(item.overall_median_share)}</small></strong></div>`;
    }).join('');animate('#signature-bars');
  }
  function drawSpectrum(){
    const keys=all?[...'GFCADEB']:[...'GFDEB'];
    keys.sort((a,b)=>byProfile.get(a).demand.total_median-byProfile.get(b).demand.total_median);
    document.getElementById('spectrum-rows').innerHTML=keys.map(key=>{const card=byProfile.get(key);return `<button type="button" class="spectrum-row" data-spectrum-profile="${key}" aria-pressed="${key===chosen}" style="--desk-color:${colors[key]}"><span><b>${key}</b><small>${status[card.status]}</small></span><span class="spectrum-measure"><i style="--position:${card.demand.total_median/maxTotal*70}%"></i><strong style="left:${card.demand.total_median/maxTotal*70}%">${fmt.format(card.demand.total_median)}</strong></span><span class="spectrum-measure"><i style="--position:${share(card,'Catering')/maxCatering*70}%"></i><strong style="left:${share(card,'Catering')/maxCatering*70}%">${percent(share(card,'Catering'))}</strong></span></button>`;}).join('');
    spectrum.querySelectorAll('[data-spectrum-mode]').forEach(button=>button.setAttribute('aria-pressed',String((button.dataset.spectrumMode==='all')===all)));
    document.getElementById('spectrum-reading').textContent=all?'A нарушает общий порядок: показатель расходов выше, чем у D, а доля общепита ниже. Одна шкала не описывает всё разнообразие спроса.':'В последовательности G → F → D → E → B растут оба показателя. Выберите строку, чтобы увидеть структуру расходов группы.';
    spectrum.querySelectorAll('[data-spectrum-profile]').forEach(button=>button.onclick=()=>select(button.dataset.spectrumProfile));
    if(!keys.includes(chosen))chosen='G';select(chosen);refresh();
  }
  spectrum.querySelectorAll('[data-spectrum-mode]').forEach(button=>button.onclick=()=>{all=button.dataset.spectrumMode==='all';drawSpectrum();});
  drawSpectrum();
};

import {chromium} from '@playwright/test';
import {spawn} from 'node:child_process';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const dest=path.join(root,'tmp/pdfs');await mkdir(dest,{recursive:true});
const server=spawn('python',['-m','http.server','8766','--bind','127.0.0.1','--directory','site'],{cwd:root,windowsHide:true,stdio:'ignore'});
let browser;
try{
 for(let i=0;i<80;i++){try{if((await fetch('http://127.0.0.1:8766')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch(process.env.PLAYWRIGHT_CHANNEL ? {channel:process.env.PLAYWRIGHT_CHANNEL} : {});
 const page=await browser.newPage({viewport:{width:1440,height:1018},deviceScaleFactor:1.5,reducedMotion:'reduce'});
 await page.goto('http://127.0.0.1:8766',{waitUntil:'networkidle'});
 await page.waitForFunction(()=>window.researchReady&&window.researchNetworkReady&&window.researchMapReady);
 await page.evaluate(()=>window.prepareResearchPrint());
 const pages=await page.evaluate(async()=>{
  window.ScrollTrigger?.getAll().forEach(t=>t.kill(true));
  const pages=[];
  const copy=(selector,base=document)=>{
   const el=typeof selector==='string'?base.querySelector(selector):selector;if(!el)return '';
   const clone=el.cloneNode(true);const canvases=[...(el.matches('canvas')?[el]:el.querySelectorAll('canvas'))];
   const targets=[...(clone.matches('canvas')?[clone]:clone.querySelectorAll('canvas'))];
   canvases.forEach((c,i)=>{const image=document.createElement('img');image.src=c.toDataURL('image/png');image.className=c.className;image.id=c.id;image.alt=c.getAttribute('aria-label')||'';targets[i].replaceWith(image);});
   clone.querySelectorAll('details').forEach(d=>d.open=true);
   clone.querySelectorAll('br').forEach(br=>br.after(document.createTextNode(' ')));
   clone.querySelectorAll('a[href]').forEach(a=>{const href=a.getAttribute('href');if(href.startsWith('data/')||href.startsWith('assets/'))a.href='https://github.com/resarytrew/cashless-demand-network-russia/blob/main/site/'+href;});
   clone.querySelectorAll('.auto-tour,.story-progress,.hero-actions,.hero-direct,#motion-toggle,.story-scroll-state,.story-link,.story-action,.signature-intro button,.desk-toolbar,.spectrum-toolbar,.indicator-tabs,.validation-tabs,.text-link,.profile-dotfield,.profile-dot-caption,.profile-folio,.search-box,.quick-places,.map-toolbar,.map-time,.map-watermark,.map-status').forEach(x=>x.remove());
   clone.querySelectorAll('[style]').forEach(x=>{x.style.removeProperty('transform');x.style.removeProperty('opacity');});
   return clone.outerHTML;
  };
  const add=(title,html,kind='')=>pages.push({title,html,kind});
  const heading=(title,deck='')=>`<header class="pdf-heading"><h2>${title}</h2>${deck?`<p>${deck}</p>`:''}</header>`;
  add('География спроса',copy('#opening-frame'),'cover');
  const netheading=copy('.network-heading');
  document.querySelectorAll('.network-chapter').forEach((article,i)=>{
   const clone=article.cloneNode(true),map=clone.querySelector('svg');map.classList.remove('network-mobile-map');map.classList.add('pdf-network-map');
   const m=map.outerHTML;map.remove();clone.querySelector('.network-mobile-caption')?.remove();
   add('Связи на карте · '+(i+1),netheading+`<div class="pdf-network-layout">${m}${copy(clone)}</div><p class="pdf-note">Показаны три сохранённых ближайших соседа по спросу. Линии не обозначают денежные потоки или маршруты покупателей. Декабрь 2024 года.</p>`,'network');
  });
  for(const key of ['spending','wage','population']){
   document.querySelector(`[data-hypothesis="${key}"]`).click();
   await new Promise(requestAnimationFrame);
   const section=document.querySelector('#question').cloneNode(true);section.querySelector('.hypothesis-switch')?.remove();
   add('Три взгляда на выборку',copy('.story-copy',section)+copy('.hypothesis-figure',document.querySelector('#question')),'hypothesis');
  }
  for(const key of ['E','G','D']){
   document.querySelector(`[data-desk-pair="${key}"]`).click();
   add('Сопоставление территорий',copy('.crack-heading')+copy('#comparison-desk'),'comparison');
  }
  document.querySelector('[data-spectrum-mode="all"]').click();
  const spectrum=document.querySelector('#demand-spectrum').cloneNode(true);spectrum.querySelector('.signature-layout').remove();
  add('Спектр спроса',copy('.spectrum-heading')+copy(spectrum),'spectrum');
  add('Как устроено сравнение',copy('.reading-key'),'mechanics');
  add('Семь профилей',copy('#profiles .section-heading')+copy('.status-legend')+`<div class="pdf-profile-index">${[...document.querySelectorAll('.walk-portrait')].map(a=>`<div>${copy('.walk-letter',a)}${copy('h3',a)}${copy('.walk-status',a)}</div>`).join('')}</div>`,'profiles-index');
  for(const key of [...'ABCDEFG']){
   document.querySelector(`[data-profile="${key}"]`).click();
   const stage=document.querySelector('#profile-stage');
   const technical=stage.querySelector('#profile-technical-content p');technical.textContent='Код профиля в исследовании: '+key+'. Статус: '+publicStatuses[cardData.cards.find(c=>c.profile===key).status]+'. Численные проверки ниже описывают разные стороны устойчивости и не равнозначны подтверждению неизменного состава группы.';
   const head=copy('.profile-top',stage)+copy('#profile-code',stage)+copy('#profile-name',stage)+copy('#profile-territories',stage)+copy('#profile-note',stage);
   const shell=content=>`<article class="profile-stage pdf-profile" style="${stage.getAttribute('style')}">${content}</article>`;
   add('Профиль '+key+' · спрос и представители',shell(head+copy('.profile-metrics',stage)+`<div class="pdf-block-grid">${copy('.demand-block',stage)}${copy('.representatives-block',stage)}</div>`),'profile');
   add('Профиль '+key+' · интерпретация и границы',shell(copy('#profile-code',stage)+copy('#profile-name',stage)+`<div class="pdf-block-grid">${['.external-block','.counterexample-block','.robustness-block','.practical-block'].map(s=>copy(s,stage)).join('')}</div>`),'profile');
   add('Профиль '+key+' · подробные проверки',shell(copy('#profile-code',stage)+copy('#profile-name',stage)+copy('#profile-technical-content',stage)),'profile-technical');
  }
  document.querySelectorAll('.finding').forEach(a=>add('Наблюдения',copy(a),'finding'));
  for(const key of ['wage','population','employment_total']){
   document.querySelector(`[data-indicator="${key}"]`).click();
   add('Независимый взгляд',copy('#external-evidence .section-heading')+copy('.external-coverage')+copy('.external-workspace')+copy('.external-source'),'external');
  }
  add('Внешние сопоставления',copy('.external-effect')+copy('.transfer-section')+copy('.external-source'),'validation');
  add('Изменения за два года',copy('#changes'),'changes');
  add('Изменения состава групп',copy('#flows'),'flows');
  add('Муниципальный атлас',copy('#atlas .section-heading')+copy('.map-column')+copy('.map-caption'),'atlas');
  add('Пример территории',heading('Казань: портрет территории')+copy('#municipality-detail'),'municipality');
  add('Как читать результат',copy('#discovery'),'discovery');
  add('Границы результата',copy('#limits'),'limits');
  const use=document.querySelector('#possibilities').cloneNode(true);use.querySelector('.capability-contract')?.remove();
  add('Практический сценарий',copy(use),'use');
  add('Возможности и ограничения',copy('.capability-contract'),'contract');
  add('Метод и проверяемость',copy('#about')+copy('#proof'),'proof');
  add('От сравнения к исследованию',copy('#conclusion')+copy('#materials'),'conclusion');
  add('Методология и ограничения',copy('#print-appendix'),'appendix');
  return pages.map(p=>({...p,html:p.html.replaceAll('По мере прокрутки сравним рисунок карты для каждого показателя.','На следующих страницах сравним рисунок карты для каждого показателя.').replaceAll('Затем появятся A и C: они покажут пределы этой последовательности.','Профили A и C показывают пределы этой последовательности.').replaceAll('Найдите город или район. Его портрет покажет, к какому профилю спроса он относится и как менялось его окружение.','Карта показывает профили спроса. Далее приведён портрет Казани. Поиск территорий и смена месяцев доступны в интерактивной версии атласа.').replaceAll('CLR / геометрия Эйчисона','центрированные логарифмические отношения долей / геометрия Эйчисона').replaceAll('robust-z от log(Total)','робастно стандартизированный логарифм общего показателя расходов').replaceAll('Louvain, resolution = 0,5, seed = 0','алгоритм Лувена, разрешение = 0,5, начальное состояние генератора = 0').replaceAll('Знаменатель Total','Знаменатель общего показателя расходов')}));
 });
 const css=await readFile(path.join(root,'scripts/landing_pdf.css'),'utf8');
 await page.evaluate(({pages,css})=>{
  document.querySelectorAll('script').forEach(x=>x.remove());
  document.body.innerHTML=pages.map((p,i)=>`<section class="pdf-page ${p.kind}"><div class="pdf-running"><span>География спроса</span><span>${p.title}</span></div><div class="pdf-content">${p.html}</div><footer class="pdf-footer"><span>По данным СберИндекса и Росстата · 2023–2024</span><span>${String(i+1).padStart(2,'0')} / ${pages.length}</span></footer></section>`).join('');
  const style=document.createElement('style');style.textContent=css;document.head.append(style);
 },{pages,css});
 await page.evaluate(()=>document.fonts.ready);
 const fit=await page.evaluate(()=>[...document.querySelectorAll('.pdf-page')].map((p,i)=>{
  const content=p.querySelector('.pdf-content');const h=content.scrollHeight;const scale=Math.min(1,830/h);if(scale<1)content.style.transform=`scale(${scale})`;return {page:i+1,title:p.querySelector('.pdf-running').innerText,height:h,scale};
 }));
 await writeFile(path.join(dest,'layout.json'),JSON.stringify(fit,null,2));
 await writeFile(path.join(dest,'page-titles.json'),JSON.stringify(pages.map(p=>p.title)));
 await page.emulateMedia({media:'screen'});
 await page.pdf({path:path.join(dest,'landing-edition.pdf'),width:'1440px',height:'1018px',printBackground:true,preferCSSPageSize:false,tagged:true});
 console.log(JSON.stringify({pages:pages.length,minScale:Math.min(...fit.map(x=>x.scale)),small:fit.filter(x=>x.scale<.7)},null,2));
 await page.screenshot({path:path.join(dest,'cover.png')});
}finally{await browser?.close();server.kill();}

const { test, expect } = require('@playwright/test');
test.beforeEach(async({page})=>{await page.emulateMedia({reducedMotion:'reduce'});});
const ready=async page=>{await page.goto('/');await page.waitForFunction(()=>window.researchReady&&window.researchMapReady);};
test('all published routes serve the same current Atlas',async({page})=>{
 for(const route of ['/','/atlas/','/site/']){
  await page.goto(route);await page.waitForFunction(()=>window.researchReady&&window.researchMapReady);
  await expect(page.locator('h1')).toContainText('Россия тратит');
  await expect(page.locator('[data-profile="A"]')).toContainText('Северный ресурсный');
  await page.locator('#municipality-search').fill('Казань');
  await expect(page.locator('#search-results button').first()).toContainText('Казань');
 }
});
test('public journey, territory search and scientific details',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await ready(page);
 await expect(page.locator('.masthead nav a')).toHaveText(['Вопрос','Профили','Открытия','Границы','Изменения','Атлас','Методология']);
 await expect(page.locator('h1')).toContainText('Россия тратит');
 await expect(page.locator('#contrast-pair .place-contrast')).toHaveCount(2);
 await expect(page.locator('#engel-chart .engel-point')).toHaveCount(7);
 await expect(page.locator('#marketplace-scale .market-row')).toHaveCount(7);
 await expect(page.locator('#city-function .people-card')).toHaveCount(2);
 await page.locator('.hero .primary-link').click();await expect(page.locator('#question-title')).toBeInViewport();
 await page.evaluate(()=>window.atlasNavigate(document.querySelector('#atlas')));await expect(page.locator('#municipality-search')).toBeInViewport();
 await page.locator('#municipality-search').fill('Казань');await page.keyboard.press('Enter');
 await expect(page.locator('#municipality-detail h3')).toHaveText('Казань');
 await expect(page.locator('.trajectory i')).toHaveCount(24);
 await expect(page.locator('#municipality-detail .affinity')).not.toBeVisible();
 await page.locator('#municipality-detail summary').click();await expect(page.locator('.affinity > div')).toHaveCount(7);
 await page.locator('.place-profile-link').click();await expect(page.locator('#profile-count')).toHaveText('153');
 await page.locator('[data-profile="F"]').click();await expect(page.locator('#profile-count')).toHaveText('327');
 await expect(page.locator('#profile-technical-content')).not.toBeVisible();
 await page.locator('#municipality-search').fill('not-a-place');await expect(page.locator('#search-count')).toContainText('Совпадений нет');expect(errors).toEqual([]);
});
for(const width of [390,768,1280,1440])test(`responsive public navigation ${width}`,async({page})=>{
 await page.setViewportSize({width,height:900});await ready(page);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await expect(page.locator('.masthead nav')).toBeVisible();
 const links=await page.locator('a[href^="#"]').evaluateAll(as=>as.map(a=>a.getAttribute('href')));
 for(const hash of links)await expect(page.locator(hash).first()).toBeAttached();
 await expect(page.locator('#motion-toggle')).toHaveAttribute('aria-pressed','true');
});
test('map layers, saved months, selection and zoom',async({page})=>{
 await ready(page);await expect(page.locator('.municipality-path')).toHaveCount(1903);
 await page.locator('#map-month').fill('0');await expect(page.locator('#map-month-label')).toContainText('январь 2023');
 await page.locator('[data-map-layer="stability"]').click();await expect(page.locator('#map-month')).toBeDisabled();
 await expect(page.locator('#map-legend')).toContainText('Сходство устойчиво');
 await page.locator('[data-map-layer="profile"]').click();await page.locator('#map-play').click();await expect(page.locator('#map-play')).toHaveAttribute('aria-pressed','true');await page.locator('#map-play').click();
 await page.locator('#map-zoom-in').click();await expect(page.locator('.map-geography')).not.toHaveAttribute('transform','translate(0,0) scale(1)');
 await page.locator('.municipality-path').first().dispatchEvent('click');await expect(page.locator('#municipality-detail h3')).not.toBeEmpty();
 await page.locator('.flow-link').first().focus();await expect(page.locator('#flow-detail')).toContainText('территорий');
});
test('GSAP smooth scroll, chapter navigation, reduced-motion cleanup',async({page})=>{
 await page.emulateMedia({reducedMotion:'no-preference'});await page.setViewportSize({width:1440,height:1000});const errors=[];page.on('pageerror',e=>errors.push(e.message));await ready(page);
 expect(await page.evaluate(()=>ScrollSmoother.get().smooth())).toBeGreaterThan(1);
 await page.locator('nav a[href="#changes"]').click();await expect.poll(()=>page.locator('#changes').evaluate(el=>Math.abs(el.getBoundingClientRect().top-36)),{timeout:7000}).toBeLessThan(8);
 await expect(page.locator('#changes h2')).toBeInViewport();
 await page.evaluate(()=>window.atlasNavigate(document.querySelector('[data-scene="1"]')));
 await expect.poll(()=>page.locator('#change-canvas').getAttribute('data-scene'),{timeout:7000}).toBe('1');
 await expect(page.locator('#change-canvas')).toBeInViewport();
 await page.emulateMedia({reducedMotion:'reduce'});await expect.poll(()=>page.evaluate(()=>!!ScrollSmoother.get())).toBe(false);
 await page.evaluate(()=>window.atlasNavigate(document.querySelector('#atlas')));await expect(page.locator('#atlas h2')).toBeInViewport();expect(errors).toEqual([]);
});
test('failed geometry preserves search and retry recovers map',async({page})=>{
 await page.route('**/data/municipalities.geojson',r=>r.abort());await page.goto('/');await page.waitForFunction(()=>window.researchReady);await expect(page.locator('#map-status')).toContainText('Карта недоступна');
 await page.locator('#municipality-search').fill('Казань');await page.locator('#search-results button').first().click();await expect(page.locator('#municipality-detail h3')).toContainText('Казань');
 await page.unroute('**/data/municipalities.geojson');await page.locator('#map-status button').click();await page.waitForFunction(()=>window.researchMapReady);
});
test('data failure leaves reading and keyboard navigation available',async({page})=>{
 await page.route('**/data/research.json',r=>r.abort());await page.goto('/');await expect(page.locator('#load-status')).toContainText('Не удалось загрузить');await expect(page.locator('#changes h2')).toBeVisible();await page.keyboard.press('Tab');await expect(page.locator('.skip')).toBeFocused();
});
test('methodology, aliases, downloads and print include complete scope',async({page,request})=>{
 await ready(page);await page.evaluate(()=>window.prepareResearchPrint());await expect(page.locator('.profile-print-list article')).toHaveCount(7);await expect(page.locator('#print-appendix')).toContainText('k = 20');
 for(const url of ['/methodology.html','/site/methodology.html','/assets/research-brief.pdf','/atlas/index.html','/site/index.html','/data/manifest.json'])expect((await request.get(url)).ok(),url).toBeTruthy();
 await page.goto('/methodology.html');await page.waitForFunction(()=>window.researchReady);await expect(page.locator('h1')).toContainText('Как устроен');
});

test('hero stays in place through grouping, then releases naturally',async({page})=>{
 await page.emulateMedia({reducedMotion:'no-preference'});await page.setViewportSize({width:1280,height:720});await ready(page);
 await expect.poll(()=>page.locator('#hero-canvas').getAttribute('data-progress')).not.toBeNull();
 const before=await page.locator('.hero-figure').boundingBox();const end=await page.evaluate(()=>ScrollTrigger.getById('hero-transformation').end);
 await page.mouse.wheel(0,Math.round(end*.87));
 await expect.poll(()=>page.locator('#hero-canvas').getAttribute('data-progress'),{timeout:5000}).toBe('1.000');
 const grouped=await page.locator('.hero-figure').boundingBox();expect(Math.abs(grouped.y-before.y)).toBeLessThan(3);expect(grouped.y+grouped.height).toBeLessThan(720);
 await expect(page.locator('#hero-scroll-state')).toContainText('Группы видны');
 await page.mouse.wheel(0,Math.round(end*.5));await expect.poll(()=>page.locator('.hero-figure').evaluate(el=>el.getBoundingClientRect().top),{timeout:5000}).toBeLessThan(before.y-100);
});
test('external comparisons and region-held-out scores keep their meaning',async({page})=>{
 await ready(page);await expect(page.locator('.external-row')).toHaveCount(7);
 await expect(page.locator('[data-external-profile="D"] strong')).toContainText('75');
 await page.locator('[data-indicator="population"]').click();await expect(page.locator('#external-chart-title')).toContainText('населения');
 await expect(page.locator('[data-external-profile="D"] strong')).toHaveText(/130\s?039/);
 await page.locator('[data-indicator="employment_total"]').click();await expect(page.locator('#external-chart-title')).toContainText('занятых');
 await expect(page.locator('#prediction-bars strong')).toHaveText(['0,551','0,096']);await page.locator('[data-validation="random"]').click();await expect(page.locator('#prediction-bars strong')).toHaveText(['0,647','0,091']);
 await expect(page.locator('#prediction-explanation')).toContainText('перестановке');
 await page.locator('[data-external-profile="F"]').click();await expect(page.locator('#profile-count')).toHaveText('327');
 await expect(page.locator('.place-proximity > div')).toHaveCount(3);await expect(page.locator('.place-proximity')).toContainText('не вероятности');
});


const chapterPosition=async(page,id,fraction)=>{
 await page.evaluate(({id,fraction})=>{
  const t=ScrollTrigger.getById('chapter-'+id);
  const y=t.start+(t.end-t.start)*fraction;
  const smoother=ScrollSmoother.get();if(smoother)smoother.scrollTop(y);else window.scrollTo(0,y);
 },{id,fraction});
 await page.waitForFunction(({id,fraction})=>{
  const trigger=ScrollTrigger.getById('chapter-'+id);
  return Math.abs(trigger.progress-fraction)<.015;
 },{id,fraction});
};
test('every evidence-rich profile card is selectable and keeps its explicit status',async({page})=>{
 await page.setViewportSize({width:1280,height:900});await ready(page);
 expect(await page.locator('[data-tour="profiles"]').count()).toBe(0);
 for(const profile of [...'ABCDEFG']){
  await page.locator(`[data-profile="${profile}"]`).click();
  await expect(page.locator(`[data-profile="${profile}"]`)).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('#profile-code')).toHaveText(`Профиль ${profile}`);
  await expect(page.locator('#profile-status')).not.toBeEmpty();
  await expect(page.locator('#profile-territories')).toContainText('выборки');
  await expect(page.locator('#profile-representatives li')).toHaveCount(3);
  await expect(page.locator('.profile-block')).toHaveCount(6);
  await expect(page.locator('#profile-demand')).not.toContainText('Total');
  await expect(page.locator('#profile-representatives')).not.toContainText('reference');
  await expect(page.locator('#profile-robustness')).not.toContainText('retention');
 }
 await page.locator('[data-profile="A"]').click();
 await expect(page.locator('#profile-name')).toHaveText('Северный ресурсный');
 await expect(page.locator('#profile-status')).toHaveText('Статус: поддержан');
 await expect(page.locator('#profile-representatives li').first()).toContainText('золотодобывающая специализация');
 await expect(page.locator('#profile-external')).toContainText('северные и дальневосточные территории');
 await expect(page.locator('#profile-robustness')).toContainText('Ядро устойчиво');
 await expect(page.locator('#profile-counterexample')).toContainText('Лаишевский район');
 await page.locator('#profile-technical').click();
 await expect(page.locator('#profile-technical-content')).toContainText('точность границы 27,5%');
 await page.locator('[data-profile="B"]').click();
 await expect(page.locator('#profile-name')).toHaveText('Деловые районы мегаполисов');
 await page.locator('[data-profile="C"]').click();
 await expect(page.locator('#profile-representatives-title')).toHaveText('Иллюстративные случаи');
 await expect(page.locator('#profile-robustness')).toContainText('нет собственной устойчивой границы');
 await page.locator('[data-profile="E"]').click();
 await expect(page.locator('#profile-name')).toHaveText('Спальные районы мегаполисов');
 await page.locator('[data-profile="F"]').click();
 await expect(page.locator('#profile-representatives')).toContainText('Сторона D');
 await expect(page.locator('#profile-representatives')).toContainText('Сторона G');
 await expect(page.locator('#profile-representatives')).toContainText('Предельный случай');
 await page.locator('[data-profile="D"]').click();
 await expect(page.locator('#profile-name')).toHaveText('Промышленные города');
 await expect(page.locator('#profile-external')).toContainText('Оренбург, Магнитогорск, Тамбов');
 await expect(page.locator('#profile-counterexample')).toContainText('Уссурийск');
 await expect(page.locator('#profile-robustness')).toContainText('98,7%');
 await page.locator('[data-profile="G"]').click();
 await expect(page.locator('#profile-name')).toHaveText('Сельская бюджетная Россия');
});
test('salary population and employment follow scroll in a readable pinned chart',async({page})=>{
 await page.emulateMedia({reducedMotion:'no-preference'});await page.setViewportSize({width:1280,height:720});await ready(page);
 await expect(page.locator('[data-tour="indicators"]')).toHaveAttribute('data-pinned','true');
 for(const [i,key] of ['wage','population','employment_total'].entries()){
  await chapterPosition(page,'indicators',(i+.4)/3);
  await expect(page.locator(`[data-indicator="${key}"]`)).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('#external-chart-title')).toBeInViewport();
  await expect(page.locator('.external-row').last()).toBeInViewport();
 }
 await chapterPosition(page,'indicators',.1);await expect(page.locator('[data-indicator="wage"]')).toHaveAttribute('aria-pressed','true');
});
test('map layers follow scrolling and keep manual exploration available',async({page})=>{
 await page.emulateMedia({reducedMotion:'no-preference'});await page.setViewportSize({width:1280,height:720});await ready(page);
 for(const [i,key] of ['profile','switches','stability'].entries()){
  await chapterPosition(page,'map',(i+.4)/3);
  await expect(page.locator(`[data-map-layer="${key}"]`)).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('#map-legend')).toBeInViewport();
 }
 await expect(page.locator('#map-legend')).toContainText('Сходство устойчиво');
 await page.locator('[data-map-layer="profile"]').click();await expect(page.locator('#map-month')).toBeEnabled();
 await expect(page.locator('#possibilities')).toContainText('не гарантирует рост');await expect(page.locator('#wage-effect')).toHaveText('0,633');
});
test('captions controls and evidence remain readable on a phone and laptop',async({page})=>{
 for(const width of [390,1280]){
  await page.setViewportSize({width,height:900});await ready(page);
  for(const selector of ['#profile-status','.profile-dot-caption','.map-legend','.external-row-name','.external-row-name small','.contract-note','.trajectory-years span']){
   expect(await page.locator(selector).first().evaluate(e=>parseFloat(getComputedStyle(e).fontSize)),selector).toBeGreaterThanOrEqual(14);
  }
  await expect(page.locator('#profile-tabs')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 }
});

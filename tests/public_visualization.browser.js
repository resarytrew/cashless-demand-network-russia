// Run in the loaded page using agent-browser eval --stdin. No network required.
(() => {
  const app = window.landscapeApp;
  const get = id => document.getElementById(id);
  const assert = (condition, message) => { if (!condition) throw Error(message); };
  get('reset').click();
  const original = JSON.stringify(app.rows);
  assert(app.rows.length === 1904, '1904 records');
  assert(document.querySelectorAll('.point').length === 1904, '1904 SVG marks');
  assert(get('story-controls').offsetHeight === 0, 'story controls initially hidden');
  const visible = () => [...document.querySelectorAll('.point')].filter(p => p.style.display !== 'none').length;
  for (const mode of ['consensus','stability','uncertainty','DFG','BE']) {
    get('mode').value = mode; get('mode').dispatchEvent(new Event('input'));
    assert(visible() === app.rows.filter(app.accepts).length, `filter ${mode}`);
    assert(visible() > 0, `nonempty ${mode}`);
  }
  get('reset').click();
  for (const [id,value,field] of [['reference','F','reference_profile'],['consensus','G','consensus_class'],['stability','transition','stability_class']]) {
    get(id).value=value;get(id).dispatchEvent(new Event('input'));
    assert(visible()===app.rows.filter(r=>r[field]===value).length,id);
    get('reset').click();
  }
  get('margin').value='.5';get('margin').dispatchEvent(new Event('input'));
  assert(visible()===app.rows.filter(r=>r.affinity_margin>=.5).length,'margin filter');
  get('reset').click();
  const r = app.rows[14];
  get('search').value = r.municipality;get('search').dispatchEvent(new Event('input'));
  document.querySelector('#matches button').click();
  assert(app.selected === r.panel_index,'selection id');
  assert(get('details').textContent.includes(r.municipality),'selected municipality');
  assert(document.querySelectorAll('.dna-row').length===7,'seven original affinity bars');
  const point = [...document.querySelectorAll('.point')].find(p=>Number(p.dataset.id)===r.panel_index);
  point.dispatchEvent(new PointerEvent('pointerenter',{clientX:200,clientY:300}));
  assert(!get('tooltip').hidden && get('tooltip').textContent.includes(r.municipality),'hover identity');
  point.dispatchEvent(new PointerEvent('pointerleave'));
  get('reset').click();get('hard').click();assert(app.layout==='hard','hard layout');
  get('soft').click();assert(app.layout==='soft','soft layout');
  get('story').click();get('pause').click();
  assert(app.layout==='hard' && app.storyIndex===0,'scene 1');
  for(let i=1;i<5;i++){get('next').click();assert(app.storyIndex===i,`scene ${i+1}`);if(i===3)assert(visible()===327,'all F including A side');}
  get('stop').click();
  assert(original === JSON.stringify(app.rows),'filters/story do not mutate input data');
  assert(document.documentElement.scrollWidth<=innerWidth,'no horizontal page overflow');
  return {status:'PASS',municipalities:1904,checks:'five modes, filters, search, hover, DNA, hard/soft, five scenes, input immutability, viewport'};
})()

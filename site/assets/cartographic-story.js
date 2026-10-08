'use strict';

// All lines come from saved graph neighbors. Scroll changes presentation only.
window.initCartographicStory = async function () {
  const host = document.getElementById('network-story');
  if (!host) return;
  const status = document.getElementById('network-status');
  try {
    const response = await fetch('data/network.json');
    if (!response.ok) throw Error('Network data unavailable');
    const saved = await response.json();
    const geo = await loadGeometry();
    const places = new Map(data.municipalities.map(m => [m.id, m]));
    const selected = saved.presentation.examples.map(query => data.municipalities.find(m => m.name.includes(query))).filter(Boolean);
    const svg = d3.select('#network-map');
    const projection = d3.geoConicEqualArea().rotate([-100, 0]).center([0, 63]).parallels([50, 70]).fitExtent([[30, 45], [1070, 550]], geo);
    const path = d3.geoPath(projection);
    svg.append('g').attr('class', 'network-land').selectAll('path').data(geo.features).join('path').attr('d', path);
    const curve = edge => {
      const a = projection(edge.from), b = projection(edge.to);
      const lift = Math.min(140, Math.hypot(b[0] - a[0], b[1] - a[1]) * .32);
      return `M${a} Q${(a[0] + b[0]) / 2},${(a[1] + b[1]) / 2 - lift} ${b}`;
    };
    svg.append('g').attr('class', 'network-context').selectAll('path')
      .data(saved.edges.filter((_, i) => i % saved.presentation.overview_stride === 0))
      .join('path').attr('d', curve);
    const links = svg.append('g').attr('class', 'network-links');
    const nodes = svg.append('g').attr('class', 'network-nodes');
    const chapters = document.getElementById('network-chapters');
    const narratives = [
      ['Сначала найдём знакомую точку.', 'У каждой территории есть географические соседи. Но похожий спрос может связывать её с совсем другими местами.'],
      ['Теперь посмотрим за пределы региона.', 'Линии ведут к трём ближайшим соседям по структуре и уровню расходов. Расстояние между ними не участвовало в построении сети.'],
      ['Дальняя связь тоже имеет значение.', 'Сравнение не ограничено административными границами. Оно помогает увидеть сходство, которое обычная карта оставляет незаметным.'],
      ['Сходство становится вопросом.', 'Почему эти территории оказались рядом по спросу? Карта подсказывает, что сравнить. Объяснение требует отдельного исследования.']
    ];
    chapters.innerHTML = selected.map((m, i) => `<article class="network-chapter" data-network-step="${i}"><span class="network-place">${escapeHTML(shortName(m.name))}</span><h3>${narratives[i][0]}</h3><p>${narratives[i][1]}</p><ol>${saved.edges.filter(e => e.source === m.id).map(e => `<li><span>${escapeHTML(shortName(places.get(e.target).name))}</span><b>${nf.format(e.km)} км</b></li>`).join('')}</ol><p class="network-small">Три ближайших соседа по спросу. Рядом указано географическое расстояние.</p></article>`).join('');
    let active = -1;
    function show(index) {
      if (active === index) return;
      active = index;
      const m = selected[index], edges = saved.edges.filter(e => e.source === m.id);
      links.selectAll('path').data(edges).join('path').attr('d', curve);
      const points = edges.map(e => ({id: e.target, xy: projection(e.to)}));
      if (edges.length) points.push({id: m.id, xy: projection(edges[0].from)});
      nodes.selectAll('circle').data(points).join('circle').attr('cx', n => n.xy[0]).attr('cy', n => n.xy[1]).attr('r', n => n.id === m.id ? 7 : 4);
      document.getElementById('network-current').textContent = shortName(m.name);
      document.getElementById('network-progress').textContent = `${index + 1} / ${selected.length}`;
      host.dataset.active = String(index);
      chapters.querySelectorAll('article').forEach((el, i) => el.classList.toggle('is-current', i === index));
    }
    selected.forEach((_, index) => {
      show(index);
      const mobileMap = svg.node().cloneNode(true);
      mobileMap.removeAttribute('id');
      mobileMap.setAttribute('class', 'network-mobile-map');
      mobileMap.setAttribute('aria-label', 'Сохранённые связи: ' + shortName(selected[index].name));
      chapters.children[index].querySelector('h3').after(mobileMap);
      const caption=document.createElement('p');caption.className='network-mobile-caption';caption.textContent='Линии показывают сходство расходов, а не денежные потоки. Декабрь 2024 года.';mobileMap.after(caption);
    });
    show(0);
    status.hidden = true;
    const media = gsap.matchMedia();
    media.add('all', () => {
      const triggers = selected.map((_, index) => ScrollTrigger.create({
        trigger: chapters.children[index], start: 'top 65%', end: 'bottom 65%',
        onEnter: () => show(index), onEnterBack: () => show(index)
      }));
      // GSAP pin works inside the existing transformed smooth-scroll container.
      return () => {triggers.forEach(t => t.kill());};
    });
    media.add('(min-width: 641px)', () => {
      const pin = ScrollTrigger.create({trigger: '.network-journey', start: 'top 30px', end: 'bottom bottom', pin: '.network-map-panel', pinSpacing: false, invalidateOnRefresh: true});
      return () => pin.kill();
    });
    window.researchNetworkReady = true;
    ScrollTrigger.refresh();
  } catch (error) {
    status.textContent = 'Не удалось загрузить карту связей. Основной атлас и описание исследования доступны ниже.';
    const retry = document.createElement('button');
    retry.textContent = 'Повторить загрузку';
    retry.onclick = () => { document.getElementById('network-map').replaceChildren();window.initCartographicStory(); };
    status.append(retry);
  }
};

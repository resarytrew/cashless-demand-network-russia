'use strict';

// Motion is a presentation layer. It never changes a saved observation or label.
window.initAtlasMotion = async function () {
  if (!window.gsap || !window.ScrollTrigger || !window.ScrollSmoother) return;
  gsap.registerPlugin(ScrollTrigger, ScrollSmoother, ScrollToPlugin);
  const media = gsap.matchMedia();
  let smoother, navigation;
  const chapterLinks = [...document.querySelectorAll('.masthead nav a[href^="#"]')];

  window.atlasNavigate = (target, updateHistory = false) => {
    if (!target) return;
    navigation?.kill();
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const scrollTarget = ['explore','top'].includes(target.id) ? document.getElementById('opening-frame') : target;
    const top = Math.max(0, scrollTarget.getBoundingClientRect().top + scrollY - 36);
    if (smoother) smoother.scrollTo(scrollTarget, !reduce, 'top 36px');
    else if (reduce) window.scrollTo({top, behavior:'instant'});
    else navigation = gsap.to(window, {
      scrollTo: {y:top, autoKill:true}, duration:1.55, ease:'power3.inOut', overwrite:'auto'
    });
    if (updateHistory && target.id) history.pushState(null, '', '#' + target.id);
  };
  document.addEventListener('click', event => {
    const anchor = event.target.closest('a[href^="#"]');
    if (!anchor || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const target = document.getElementById(anchor.hash.slice(1));
    if (!target) return;
    event.preventDefault();
    window.atlasNavigate(target, true);
    // Transfer keyboard focus without fighting the animated scroll.
    if (event.detail === 0) {
      target.setAttribute('tabindex', '-1');
      target.focus({preventScroll:true});
    }
  });
  const cancelNavigation = () => { navigation?.kill(); navigation = null; };
  window.addEventListener('wheel', cancelNavigation, {passive:true});
  window.addEventListener('touchstart', cancelNavigation, {passive:true});
  window.addEventListener('keydown', event => {
    if (['ArrowDown','ArrowUp','PageDown','PageUp','Home','End',' '].includes(event.key)) cancelNavigation();
  });

  media.add({motion:'(prefers-reduced-motion: no-preference)', desktop:'(min-width: 900px)'}, context => {
    if (!context.conditions.motion) return;
    document.documentElement.classList.add('gsap-motion');
    smoother = context.conditions.desktop ? ScrollSmoother.create({
      wrapper:'#smooth-wrapper', content:'#smooth-content', smooth:1.35,
      ease:'power3', smoothTouch:0, effects:false, normalizeScroll:false
    }) : null;
    // Continuous background colour moves across the whole canvas, never a section edge.
    const atmosphere = gsap.timeline({scrollTrigger:{trigger:'#profiles',start:'top bottom',end:'bottom top',scrub:1.5}});
    atmosphere.to('body', {backgroundColor:'#f0f2f5',duration:1,ease:'none'})
      .to('body', {backgroundColor:'#f7f4ee',duration:1,ease:'none'});

    gsap.from('.hero-copy > *', {y:32, opacity:0, duration:1.3, stagger:.13, ease:'power3.out',clearProps:'transform,opacity'});
    gsap.from('.hero-figure', {opacity:0, duration:1.8, ease:'power2.out'});
    const geography = {progress:0};
    const opening = gsap.timeline({scrollTrigger:{
      id:'hero-transformation',
      trigger:context.conditions.desktop ? '#opening-frame' : '.hero-figure',
      start:context.conditions.desktop ? 'top top' : 'top 28px',
      end:()=>'+='+Math.max(innerHeight*1.25,760),
      pin:context.conditions.desktop ? '#opening-frame' : '.hero-figure',
      pinSpacing:true, scrub:.65, anticipatePin:1, invalidateOnRefresh:true
    }});
    opening.to(geography,{progress:1,duration:1,ease:'power1.inOut',onUpdate:()=>{
      window.setHeroProgress?.(geography.progress);
      const caption=document.getElementById('hero-scroll-state');
      if(caption)caption.textContent=geography.progress>.98 ? 'Группы видны. Продолжайте исследование ↓' : geography.progress>.1 ? 'Расстояния уступают место сходству' : 'Прокрутите, чтобы увидеть связи ↓';
    }}).to({}, {duration:.3}); // Hold the completed grouping before releasing the screen.

    // A thin editorial progress line and the four-act rail keep the long read legible.
    ScrollTrigger.create({id:'reading-progress',start:0,end:'max',onUpdate:self=>{
      gsap.set('.reading-progress i',{scaleX:self.progress});
    }});
    const storySections=[
      {id:'question',marker:'question'},
      {id:'crack',marker:'question'},
      {id:'answer',marker:'answer'},
      {id:'profiles',marker:'answer'},
      {id:'discoveries',marker:'discoveries'},
      {id:'limits',marker:'limits'}
    ];
    storySections.forEach(({id,marker})=>ScrollTrigger.create({trigger:'#'+id,start:'top 56%',end:'bottom 44%',onToggle:self=>{
      if(!self.isActive)return;
      document.querySelectorAll('[data-story-marker]').forEach(link=>{
        if(link.dataset.storyMarker===marker)link.setAttribute('aria-current','location');else link.removeAttribute('aria-current');
      });
    }}));

    // The full-width map follows the reader's choice; scrolling never resets it.
    gsap.from('.hypothesis-screen .story-copy > *',{y:65,opacity:0,stagger:.12,ease:'power3.out',scrollTrigger:{trigger:'.hypothesis-screen',start:'top 88%',end:'top 48%',scrub:.8}});
    gsap.from('.hypothesis-figure',{y:35,opacity:.7,ease:'power3.out',scrollTrigger:{trigger:'.hypothesis-figure',start:'top 95%',end:'top 70%',scrub:.5}});

    // The shared comparison scale enters once and remains available for inspection.
    gsap.from('.comparison-desk',{y:30,opacity:.4,duration:.7,ease:'power2.out',scrollTrigger:{trigger:'.comparison-desk',start:'top 92%',toggleActions:'play none none none'}});

    // The measured spectrum reveals one row at a time without pinning the page.
    gsap.from('.spectrum-row',{y:18,opacity:.45,stagger:.075,duration:.55,ease:'power2.out',scrollTrigger:{trigger:'#demand-spectrum',start:'top 90%',toggleActions:'play none none none'}});

    // The hand-off into the atlas is a continuous dark editorial canvas.
    gsap.from('.status-legend',{y:35,opacity:0,ease:'power3.out',scrollTrigger:{trigger:'.status-legend',start:'top 92%',end:'top 68%',scrub:.7}});
    gsap.from('.weight-key > div',{y:45,opacity:0,stagger:.14,ease:'power3.out',scrollTrigger:{trigger:'.weight-key',start:'top 90%',end:'bottom 66%',scrub:.8}});

    // Three findings: line first, then exceptions; bars and people follow as separate beats.
    const engelLine=document.querySelector('#engel-chart .engel-line');
    if(engelLine){
      const length=engelLine.getTotalLength();gsap.set(engelLine,{strokeDasharray:length,strokeDashoffset:length});
      const engel=gsap.timeline({scrollTrigger:{trigger:'.finding-engel',start:'top 78%',end:'bottom 42%',scrub:.9}});
      engel.from('.finding-engel .finding-copy > *',{y:55,opacity:0,stagger:.1,duration:.8,ease:'power3.out'})
        .to(engelLine,{strokeDashoffset:0,duration:1.3,ease:'power2.inOut'},.25)
        .from('#engel-chart .engel-point:not([data-engel-profile="A"]):not([data-engel-profile="C"])',{scale:0,opacity:0,stagger:.09,duration:.75,ease:'back.out(1.8)'},.45)
        .from('#engel-chart .engel-point[data-engel-profile="A"],#engel-chart .engel-point[data-engel-profile="C"]',{y:-120,opacity:0,duration:1,ease:'bounce.out'},1.35);
    }
    gsap.from('.market-row i',{scaleX:0,stagger:.09,ease:'power3.out',scrollTrigger:{trigger:'.finding-market',start:'top 78%',end:'bottom 46%',scrub:.85}});
    gsap.from('.finding-market .finding-copy > *',{y:50,opacity:0,stagger:.1,ease:'power3.out',scrollTrigger:{trigger:'.finding-market',start:'top 82%',end:'center 55%',scrub:.8}});
    gsap.from('.people-card',{y:65,rotate:(_,element)=>element.matches(':first-child')?-1.5:1.5,opacity:0,stagger:.18,ease:'power3.out',scrollTrigger:{trigger:'.finding-city',start:'top 80%',end:'center 55%',scrub:.85}});
    gsap.from('.people-grid i.active',{scale:0,opacity:.15,stagger:{each:.012,from:'random'},duration:.7,ease:'back.out(2)',scrollTrigger:{trigger:'.city-function',start:'top 80%',toggleActions:'play none none reverse'}});

    // Act III deliberately changes register: cards arrive like evidence sheets, not feature tiles.
    gsap.from('.limits-heading > *',{y:75,opacity:0,stagger:.13,ease:'power3.out',scrollTrigger:{trigger:'.limits-heading',start:'top 88%',end:'bottom 62%',scrub:.85}});
    gsap.from('.limits-grid article',{y:110,rotate:(_,element)=>[ -1.2,.6,1.1 ][[...element.parentNode.children].indexOf(element)]||0,opacity:0,stagger:.18,ease:'power3.out',scrollTrigger:{trigger:'.limits-grid',start:'top 90%',end:'center 55%',scrub:.95}});
    gsap.from('.limits-total > *',{y:50,opacity:0,stagger:.16,ease:'power3.out',scrollTrigger:{trigger:'.limits-total',start:'top 90%',end:'bottom 66%',scrub:.8}});
    gsap.from('.proof-pillars article',{y:55,opacity:0,stagger:.12,ease:'power3.out',scrollTrigger:{trigger:'.proof-pillars',start:'top 90%',end:'bottom 68%',scrub:.8}});
    gsap.from('.proof-terminal',{clipPath:'inset(0 0 100% 0)',y:35,ease:'power2.inOut',scrollTrigger:{trigger:'.proof-terminal',start:'top 90%',end:'bottom 68%',scrub:.85}});
    gsap.from('.conclusion-section h2',{y:90,opacity:0,filter:'blur(8px)',ease:'power3.out',scrollTrigger:{trigger:'.conclusion-section',start:'top 82%',end:'center 58%',scrub:.9}});

    for (const heading of document.querySelectorAll('.section-heading,.flow-heading,.about-section > div:first-child')) {
      gsap.from(heading.children, {y:48,stagger:.09,ease:'power2.out',
        scrollTrigger:{trigger:heading,start:'top 96%',end:'top 54%',scrub:.85}});
    }
    gsap.from('.profile-stage', {y:65,ease:'none',scrollTrigger:{trigger:'.profiles-workspace',start:'top bottom',end:'top 32%',scrub:1}});
    gsap.from('.profile-tabs button', {x:-15,opacity:.8,stagger:.08,ease:'power2.out',scrollTrigger:{trigger:'.profiles-workspace',start:'top 92%',end:'center 64%',scrub:.8}});
    gsap.from('.reading-mechanics', {y:45,opacity:.2,ease:'power2.out',scrollTrigger:{trigger:'.reading-key',start:'top 88%',end:'center 65%',scrub:.8}});
    gsap.from('.external-coverage p', {y:30,opacity:.2,stagger:.12,ease:'power2.out',scrollTrigger:{trigger:'.external-coverage',start:'top 90%',end:'bottom 65%',scrub:.8}});

    if (context.conditions.desktop) {
      gsap.set('.story-visual', {position:'relative',top:0});
      ScrollTrigger.create({trigger:'.story-layout',start:'top 6%',end:'bottom 94%',pin:'.story-visual',pinSpacing:false,invalidateOnRefresh:true});
    }
    for (const step of document.querySelectorAll('.story-step')) {
      gsap.from(step.children, {y:45,opacity:.12,stagger:.08,ease:'power2.out',
        scrollTrigger:{trigger:step,start:'top 90%',end:'center 63%',scrub:.9}});
    }
    gsap.from('#flow-chart', {clipPath:'inset(0% 100% 0% 0%)',ease:'none',scrollTrigger:{trigger:'.flows-section',start:'top 85%',end:'center 53%',scrub:1.15}});
    gsap.from('.discovery-stat', {y:50,opacity:.15,stagger:.18,ease:'power2.out',scrollTrigger:{trigger:'.discovery-grid',start:'top 90%',end:'center 58%',scrub:1}});
    gsap.fromTo('.boundary-orbit', {scale:.62,x:0},{scale:1.1,x:10,ease:'none',scrollTrigger:{trigger:'.discovery-grid',start:'top 80%',end:'bottom 40%',scrub:1.4}});
    for (const section of document.querySelectorAll('#question,#profiles,#discoveries,#limits,#changes,#atlas')) {
      ScrollTrigger.create({trigger:section,start:'top 45%',end:'bottom 45%',onToggle:({isActive})=>{
        if (isActive) chapterLinks.forEach(a=>{if(a.hash==='#'+section.id)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');});
      }});
    }
    window.atlasMotion = {engine:'GSAP',version:gsap.version,smoother:!!smoother};
    return () => { navigation?.kill(); smoother?.kill(); smoother=null; document.documentElement.classList.remove('gsap-motion');window.atlasMotion.smoother=false; };
  });

  const refresh = () => ScrollTrigger.refresh();
  document.addEventListener('toggle', refresh, true);
  await window.loadResearchMap?.();
  ScrollTrigger.refresh();
  window.stopAtlasMotion = () => { media.revert(); document.removeEventListener('toggle',refresh,true); };
  window.addEventListener('beforeprint', window.stopAtlasMotion);
  // Legacy links still land on the interactive map.
  const initial = location.hash === '#research' ? document.getElementById('atlas') : ['#explore','#top'].includes(location.hash) ? document.getElementById('opening-frame') : document.getElementById(location.hash.slice(1));
  if (initial) { if(smoother)smoother.scrollTo(initial,false,'top 36px');else initial.scrollIntoView(); }
};

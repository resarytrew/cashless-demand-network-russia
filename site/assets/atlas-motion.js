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
    const top = Math.max(0, smoother ? smoother.offset(scrollTarget, 'top 36px') : scrollTarget.getBoundingClientRect().top + scrollY - 36);
    if (reduce) window.scrollTo({top, behavior:'instant'});
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

    for (const heading of document.querySelectorAll('.section-heading,.flow-heading,.about-section > div:first-child')) {
      gsap.from(heading.children, {y:48,opacity:.12,stagger:.09,ease:'power2.out',
        scrollTrigger:{trigger:heading,start:'top 94%',end:'bottom 65%',scrub:.85}});
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
    for (const section of document.querySelectorAll('#explore,#profiles,#changes,#atlas')) {
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
